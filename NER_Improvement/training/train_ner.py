#!/usr/bin/env python3
"""
Phase 3 — Train EVA NER models with correct BIO subword alignment + entity F1 eval.

Usage:
    python train_ner.py --model scheduling
    python train_ner.py --model learning
    python train_ner.py --model scheduling --epochs 3 --batch-size 16

Outputs:
    training/output/{scheduling|learning}/          — checkpoint + tokenizer
    evaluation/baseline_f1_{scheduling|learning}.json — per-entity F1 report
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import torch
from sklearn.model_selection import train_test_split
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    DataCollatorForTokenClassification,
    EarlyStoppingCallback,
    Trainer,
    TrainingArguments,
)

try:
    from seqeval.metrics import classification_report, f1_score, precision_score, recall_score
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Install seqeval: pip install seqeval") from exc

ROOT = Path(__file__).resolve().parents[1]
CONFIG_LABELS = ROOT / "config" / "labels.json"

DEFAULT_BASE_MODEL = "bert-base-uncased"
DEFAULT_MAX_LEN = 128
DEFAULT_EPOCHS = 5
DEFAULT_BATCH_SIZE = 16
DEFAULT_LR = 2e-5
DEFAULT_SEED = 42
DEFAULT_DROPOUT = 0.2
DEFAULT_EARLY_STOPPING_PATIENCE = 2
VAL_RATIO = 0.1

MODEL_CONFIG = {
    "scheduling": {
        "dataset": ROOT / "datasets" / "scheduling" / "final" / "scheduling_ner.json",
        "label_key": "scheduling_ner",
        "output_dir": ROOT / "training" / "output" / "scheduling",
        "report_path": ROOT / "evaluation" / "baseline_f1_scheduling.json",
        "deploy_dir": ROOT.parent / "Eva_AI_Server" / "models" / "ner_model",
    },
    "learning": {
        "dataset": ROOT / "datasets" / "learning" / "final" / "learning_ner.json",
        "label_key": "learning_ner",
        "output_dir": ROOT / "training" / "output" / "learning",
        "report_path": ROOT / "evaluation" / "baseline_f1_learning.json",
        "deploy_dir": ROOT.parent / "Eva_AI_Server" / "models" / "learning_ner",
    },
}


@dataclass
class LabelMaps:
    labels: List[str]
    label2id: Dict[str, int]
    id2label: Dict[int, str]


def load_label_maps(label_key: str) -> LabelMaps:
    with CONFIG_LABELS.open(encoding="utf-8") as fh:
        cfg = json.load(fh)
    block = cfg[label_key]
    labels = list(block["labels"])
    label2id = {k: int(v) for k, v in block["label2id"].items()}
    id2label = {int(k): v for k, v in block["id2label"].items()}
    return LabelMaps(labels=labels, label2id=label2id, id2label=id2label)


def load_dataset(path: Path) -> List[Dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    cleaned: List[Dict[str, Any]] = []
    for ex in data:
        tokens = ex.get("tokens") or []
        labels = ex.get("labels") or []
        if not tokens or len(tokens) != len(labels):
            continue
        cleaned.append(
            {
                "tokens": tokens,
                "labels": labels,
                "intent": ex.get("intent", ""),
                "text": ex.get("text", " ".join(tokens)),
            }
        )
    return cleaned


def align_labels_with_tokens(
    word_labels: Sequence[str],
    word_ids: Sequence[Optional[int]],
    label2id: Dict[str, int],
) -> List[int]:
    """
    Map word-level BIO labels to subword tokens.

    Phase 3 fix: continuation subwords of an entity receive I- tags (not -100).
    Continuation subwords of O-labeled words stay -100 (ignored in loss).
    """
    aligned: List[int] = []
    previous_word_idx: Optional[int] = None

    for word_idx in word_ids:
        if word_idx is None:
            aligned.append(-100)
            continue

        word_label = word_labels[word_idx]

        if word_idx != previous_word_idx:
            aligned.append(label2id.get(word_label, label2id["O"]))
        else:
            if word_label == "O":
                aligned.append(-100)
            elif word_label.startswith("B-"):
                i_label = "I-" + word_label[2:]
                aligned.append(label2id.get(i_label, -100))
            else:
                aligned.append(label2id.get(word_label, -100))

        previous_word_idx = word_idx

    return aligned


def build_tokenized_dataset(
    examples: List[Dict[str, Any]],
    tokenizer: AutoTokenizer,
    label_maps: LabelMaps,
    max_length: int,
) -> Dict[str, List[Any]]:
    tokenized_inputs: Dict[str, List[Any]] = {
        "input_ids": [],
        "attention_mask": [],
        "labels": [],
    }

    for ex in examples:
        encoding = tokenizer(
            ex["tokens"],
            is_split_into_words=True,
            truncation=True,
            max_length=max_length,
        )
        labels = align_labels_with_tokens(
            ex["labels"],
            encoding.word_ids(),
            label_maps.label2id,
        )
        tokenized_inputs["input_ids"].append(encoding["input_ids"])
        tokenized_inputs["attention_mask"].append(encoding["attention_mask"])
        tokenized_inputs["labels"].append(labels)

    return tokenized_inputs


class NERDataset(torch.utils.data.Dataset):
    def __init__(self, encodings: Dict[str, List[Any]]):
        self.encodings = encodings

    def __len__(self) -> int:
        return len(self.encodings["input_ids"])

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        return {
            "input_ids": torch.tensor(self.encodings["input_ids"][idx], dtype=torch.long),
            "attention_mask": torch.tensor(self.encodings["attention_mask"][idx], dtype=torch.long),
            "labels": torch.tensor(self.encodings["labels"][idx], dtype=torch.long),
        }


def make_compute_metrics(id2label: Dict[int, str]):
    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=2)

        true_labels: List[List[str]] = []
        true_predictions: List[List[str]] = []

        for pred_row, label_row in zip(predictions, labels):
            pred_tags: List[str] = []
            gold_tags: List[str] = []
            for pred_id, label_id in zip(pred_row, label_row):
                if label_id == -100:
                    continue
                gold_tags.append(id2label[int(label_id)])
                pred_tags.append(id2label[int(pred_id)])
            true_labels.append(gold_tags)
            true_predictions.append(pred_tags)

        return {
            "precision": precision_score(true_labels, true_predictions),
            "recall": recall_score(true_labels, true_predictions),
            "f1": f1_score(true_labels, true_predictions),
        }

    return compute_metrics


def pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def evaluate_and_save_report(
    trainer: Trainer,
    eval_dataset: NERDataset,
    id2label: Dict[int, str],
    report_path: Path,
    model_name: str,
) -> Dict[str, Any]:
    predictions = trainer.predict(eval_dataset)
    pred_ids = np.argmax(predictions.predictions, axis=2)
    label_ids = predictions.label_ids

    true_labels: List[List[str]] = []
    true_predictions: List[List[str]] = []

    for pred_row, label_row in zip(pred_ids, label_ids):
        pred_tags: List[str] = []
        gold_tags: List[str] = []
        for pred_id, label_id in zip(pred_row, label_row):
            if label_id == -100:
                continue
            gold_tags.append(id2label[int(label_id)])
            pred_tags.append(id2label[int(pred_id)])
        true_labels.append(gold_tags)
        true_predictions.append(pred_tags)

    report_text = classification_report(true_labels, true_predictions, digits=4)
    overall = {
        "precision": float(precision_score(true_labels, true_predictions)),
        "recall": float(recall_score(true_labels, true_predictions)),
        "f1": float(f1_score(true_labels, true_predictions)),
    }

    payload = {
        "model": model_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall": overall,
        "classification_report": report_text,
        "eval_examples": len(true_labels),
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print("\n=== Entity-level F1 (validation) ===")
    print(report_text)
    print(f"Overall F1: {overall['f1']:.4f}")
    print(f"Report saved: {report_path}")

    return payload


def train_model(args: argparse.Namespace) -> None:
    cfg = MODEL_CONFIG[args.model]
    label_maps = load_label_maps(cfg["label_key"])

    print(f"Loading dataset: {cfg['dataset']}")
    raw = load_dataset(cfg["dataset"])
    if args.max_samples:
        raw = raw[: args.max_samples]
    print(f"  examples: {len(raw)}")

    stratify = [ex["intent"] for ex in raw] if len(set(ex["intent"] for ex in raw)) > 1 else None
    train_raw, val_raw = train_test_split(
        raw,
        test_size=VAL_RATIO,
        random_state=args.seed,
        stratify=stratify,
    )
    print(f"  train: {len(train_raw)}, val: {len(val_raw)}")

    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    train_enc = build_tokenized_dataset(train_raw, tokenizer, label_maps, args.max_length)
    val_enc = build_tokenized_dataset(val_raw, tokenizer, label_maps, args.max_length)

    train_dataset = NERDataset(train_enc)
    val_dataset = NERDataset(val_enc)

    model = AutoModelForTokenClassification.from_pretrained(
        args.base_model,
        num_labels=len(label_maps.labels),
        id2label=label_maps.id2label,
        label2id=label_maps.label2id,
        hidden_dropout_prob=args.dropout,
        attention_probs_dropout_prob=max(0.1, args.dropout / 2),
        classifier_dropout=args.dropout,
    )

    device = pick_device()
    print(f"Device: {device}")

    output_dir = Path(args.output_dir or cfg["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(output_dir / "checkpoints"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.lr,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        save_total_limit=2,
        seed=args.seed,
        report_to="none",
        use_mps_device=(device == "mps"),
    )

    data_collator = DataCollatorForTokenClassification(tokenizer=tokenizer)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=make_compute_metrics(label_maps.id2label),
        callbacks=[
            EarlyStoppingCallback(early_stopping_patience=args.early_stopping_patience),
        ],
    )

    print("\nStarting training...")
    trainer.train()

    final_dir = output_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))
    print(f"\nModel saved: {final_dir}")

    report = evaluate_and_save_report(
        trainer,
        val_dataset,
        label_maps.id2label,
        Path(args.report_path or cfg["report_path"]),
        args.model,
    )

    if args.deploy:
        deploy_dir = Path(cfg["deploy_dir"])
        deploy_dir.mkdir(parents=True, exist_ok=True)
        trainer.save_model(str(deploy_dir))
        tokenizer.save_pretrained(str(deploy_dir))
        print(f"Deployed to: {deploy_dir}")

    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train EVA NER model (Phase 3)")
    parser.add_argument(
        "--model",
        required=True,
        choices=["scheduling", "learning"],
        help="Which NER model to train",
    )
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--max-length", type=int, default=DEFAULT_MAX_LEN)
    parser.add_argument("--lr", type=float, default=DEFAULT_LR)
    parser.add_argument("--dropout", type=float, default=DEFAULT_DROPOUT)
    parser.add_argument(
        "--early-stopping-patience",
        type=int,
        default=DEFAULT_EARLY_STOPPING_PATIENCE,
        help="Stop training if val F1 does not improve for N epochs",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--max-samples", type=int, default=0, help="Limit dataset size (0 = all)")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--report-path", default="")
    parser.add_argument(
        "--deploy",
        action="store_true",
        help="Copy final model to Eva_AI_Server/models/",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    train_model(args)


if __name__ == "__main__":
    main()

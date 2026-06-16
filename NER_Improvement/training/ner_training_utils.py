"""
Shared NER training utilities for local scripts and Google Colab.

Phase 3 fix: continuation BERT subwords get I- tags (not -100).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import torch
from sklearn.model_selection import train_test_split
from transformers import AutoTokenizer

try:
    from seqeval.metrics import classification_report, f1_score, precision_score, recall_score
except ImportError:
    classification_report = f1_score = precision_score = recall_score = None  # type: ignore


@dataclass
class LabelMaps:
    labels: List[str]
    label2id: Dict[str, int]
    id2label: Dict[int, str]


def load_label_maps(labels_json: Path | str, label_key: str) -> LabelMaps:
    with Path(labels_json).open(encoding="utf-8") as fh:
        cfg = json.load(fh)
    block = cfg[label_key]
    labels = list(block["labels"])
    label2id = {k: int(v) for k, v in block["label2id"].items()}
    id2label = {int(k): v for k, v in block["id2label"].items()}
    return LabelMaps(labels=labels, label2id=label2id, id2label=id2label)


def load_ner_dataset(path: Path | str) -> List[Dict[str, Any]]:
    with Path(path).open(encoding="utf-8") as fh:
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
    Map word-level BIO labels to BERT subword tokens.

    FIX (Phase 3): entity continuation subwords → I- tag, not -100.
    O-word continuation subwords → still -100 (ignored in loss).
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
    max_length: int = 128,
) -> Dict[str, List[Any]]:
    tokenized: Dict[str, List[Any]] = {
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
        tokenized["input_ids"].append(encoding["input_ids"])
        tokenized["attention_mask"].append(encoding["attention_mask"])
        tokenized["labels"].append(labels)

    return tokenized


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


def split_train_val(
    examples: List[Dict[str, Any]],
    val_ratio: float = 0.1,
    seed: int = 42,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    intents = [ex["intent"] for ex in examples]
    stratify = intents if len(set(intents)) > 1 else None
    return train_test_split(examples, test_size=val_ratio, random_state=seed, stratify=stratify)


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


def print_entity_report(trainer, eval_dataset, id2label: Dict[int, str]) -> str:
    """Run predict and print seqeval classification report."""
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

    report = classification_report(true_labels, true_predictions, digits=4)
    overall_f1 = f1_score(true_labels, true_predictions)
    print("\n=== Entity-level F1 (validation) ===")
    print(report)
    print(f"Overall F1: {overall_f1:.4f}")
    return report


def demo_alignment_fix():
    """Quick sanity check — run in Colab before training."""
    label2id = {"O": 0, "B-task_name": 1, "I-task_name": 2}
    word_labels = ["O", "B-task_name", "I-task_name", "O"]
    word_ids = [None, 0, 1, 1, 2, 3, None]  # add | physic ##s | exam | on
    aligned = align_labels_with_tokens(word_labels, word_ids, label2id)
    print("word_ids:", word_ids)
    print("aligned:", aligned)
    assert aligned[3] == 2, "continuation subword must get I-task_name (not -100)"
    print("Alignment fix OK ✓")

"""
Local trainer for CLF1/CLF2 (optional). Colab notebooks are preferred.

Usage:
  cd CLF_Improvement/training
  python train_clf.py --task clf1
  python train_clf.py --task clf2
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import numpy as np
from datasets import Dataset
from sklearn.metrics import accuracy_score, f1_score
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)


ROOT = Path(__file__).resolve().parents[1]


def load_jsonl(path: Path) -> List[Dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, preds),
        "macro_f1": f1_score(labels, preds, average="macro"),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", choices=["clf1", "clf2"], required=True)
    ap.add_argument("--base_model", default="distilbert-base-uncased")
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--batch", type=int, default=16)
    args = ap.parse_args()

    data_path = ROOT / "datasets" / args.task / "final" / f"{args.task}.jsonl"
    out_dir = ROOT / "training" / f"{args.task}_output"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = load_jsonl(data_path)
    labels = sorted({r["label"] for r in rows})
    label2id = {l: i for i, l in enumerate(labels)}
    id2label = {i: l for l, i in label2id.items()}

    ds = Dataset.from_list(
        [{"text": r["text"], "label": label2id[r["label"]]} for r in rows]
    ).train_test_split(test_size=0.1, seed=1337)

    tok = AutoTokenizer.from_pretrained(args.base_model)

    def tokenize(batch):
        return tok(batch["text"], truncation=True, max_length=64)

    ds = ds.map(tokenize, batched=True)
    collator = DataCollatorWithPadding(tok)

    model = AutoModelForSequenceClassification.from_pretrained(
        args.base_model,
        num_labels=len(labels),
        id2label=id2label,
        label2id=label2id,
    )

    training_args = TrainingArguments(
        output_dir=str(out_dir / "runs"),
        learning_rate=3e-5,
        per_device_train_batch_size=args.batch,
        per_device_eval_batch_size=args.batch,
        num_train_epochs=args.epochs,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        greater_is_better=True,
        logging_steps=50,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=ds["train"],
        eval_dataset=ds["test"],
        tokenizer=tok,
        data_collator=collator,
        compute_metrics=compute_metrics,
    )

    trainer.train()
    metrics = trainer.evaluate()
    print("Eval:", metrics)

    final_dir = out_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(final_dir))
    tok.save_pretrained(str(final_dir))

    with (final_dir / "label_map.json").open("w", encoding="utf-8") as f:
        json.dump({"id2label": {str(k): v for k, v in id2label.items()}}, f, indent=2)

    print("Saved:", final_dir)


if __name__ == "__main__":
    main()


"""
CLF1 Training — Input Type Classification
==========================================
Classes: command, confirmation, general, help, multiple_command, out_of_scope

Usage:
    python clf1_train.py
    python clf1_train.py --epochs 5 --lr 3e-5 --batch 32

Outputs:
    clf1_model/          — best model checkpoint
    clf1_label_map.json  — {label: id} mapping (not pickle)
    clf1_results.json    — per-class F1 on held-out test set
"""

import argparse
import json
import os
import random
import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset
from transformers import (
    DistilBertTokenizerFast,
    DistilBertForSequenceClassification,
    get_linear_schedule_with_warmup,
)
from sklearn.metrics import classification_report

# ── Constants ─────────────────────────────────────────────────────────────────
# Explicit label list — never auto-detected from data
LABELS = [
    'command',
    'confirmation',
    'general',
    'help',
    'multiple_command',
    'out_of_scope',
]
LABEL2ID = {l: i for i, l in enumerate(LABELS)}
ID2LABEL = {i: l for l, i in LABEL2ID.items()}

MODEL_NAME  = 'distilbert-base-uncased'  # uncased — lowercase input in pipeline
DATA_DIR    = os.path.join(os.path.dirname(__file__), '..', 'Datasets')
OUTPUT_DIR  = os.path.join(os.path.dirname(__file__), 'clf1_model')
LABEL_MAP_PATH = os.path.join(os.path.dirname(__file__), 'clf1_label_map.json')
RESULTS_PATH   = os.path.join(os.path.dirname(__file__), 'clf1_results.json')

F1_WARN_THRESHOLD = 0.80   # warn if any class falls below this


# ── Dataset ───────────────────────────────────────────────────────────────────
class CLF1Dataset(Dataset):
    def __init__(self, examples, tokenizer, max_len=64):
        self.examples  = examples
        self.tokenizer = tokenizer
        self.max_len   = max_len

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        ex   = self.examples[idx]
        text = ex['text']
        label_id = LABEL2ID[ex['intent']]

        enc = self.tokenizer(
            text.lower(),
            max_length     = self.max_len,
            padding        = 'max_length',
            truncation     = True,
            return_tensors = 'pt',
        )
        return {
            'input_ids'      : enc['input_ids'].squeeze(0),
            'attention_mask' : enc['attention_mask'].squeeze(0),
            'labels'         : torch.tensor(label_id, dtype=torch.long),
        }


# ── Helpers ───────────────────────────────────────────────────────────────────
def seed_everything(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def evaluate(model, loader, device):
    model.eval()
    all_preds, all_labels = [], []
    with torch.no_grad():
        for batch in loader:
            input_ids = batch['input_ids'].to(device)
            attn_mask = batch['attention_mask'].to(device)
            labels    = batch['labels'].to(device)
            outputs   = model(input_ids=input_ids, attention_mask=attn_mask)
            preds     = outputs.logits.argmax(dim=-1)
            all_preds.extend(preds.cpu().tolist())
            all_labels.extend(labels.cpu().tolist())
    return all_preds, all_labels


# ── Training ──────────────────────────────────────────────────────────────────
def train(args):
    seed_everything(args.seed)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"[clf1] Device: {device}")

    tokenizer = DistilBertTokenizerFast.from_pretrained(MODEL_NAME)

    train_data = load_json(os.path.join(DATA_DIR, 'clf1_train.json'))
    test_data  = load_json(os.path.join(DATA_DIR, 'clf1_test.json'))

    # Validation split from train (10%)
    random.shuffle(train_data)
    val_cut   = int(len(train_data) * 0.9)
    val_data  = train_data[val_cut:]
    train_data = train_data[:val_cut]

    print(f"[clf1] Train={len(train_data)}  Val={len(val_data)}  Test={len(test_data)}")

    g = torch.Generator()
    g.manual_seed(args.seed)

    train_loader = DataLoader(
        CLF1Dataset(train_data, tokenizer, args.max_len),
        batch_size=args.batch, shuffle=True,
        num_workers=0, generator=g,
    )
    val_loader = DataLoader(
        CLF1Dataset(val_data, tokenizer, args.max_len),
        batch_size=args.batch, shuffle=False, num_workers=0,
    )
    test_loader = DataLoader(
        CLF1Dataset(test_data, tokenizer, args.max_len),
        batch_size=args.batch, shuffle=False, num_workers=0,
    )

    model = DistilBertForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels = len(LABELS),
        id2label   = ID2LABEL,
        label2id   = LABEL2ID,
    ).to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    total_steps = len(train_loader) * args.epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps   = total_steps // 10,
        num_training_steps = total_steps,
    )

    best_val_loss = float('inf')
    patience_counter = 0

    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0

        for batch in train_loader:
            input_ids = batch['input_ids'].to(device)
            attn_mask = batch['attention_mask'].to(device)
            labels    = batch['labels'].to(device)

            optimizer.zero_grad()
            outputs = model(input_ids=input_ids, attention_mask=attn_mask, labels=labels)
            loss    = outputs.loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            total_loss += loss.item()

        avg_train_loss = total_loss / len(train_loader)

        # Validation
        val_preds, val_labels = evaluate(model, val_loader, device)
        val_loss = sum(
            torch.nn.CrossEntropyLoss()(
                torch.zeros(len(LABELS)).scatter_(0, torch.tensor(p), 1.0).unsqueeze(0),
                torch.tensor([l])
            ).item()
            for p, l in zip(val_preds, val_labels)
        ) / len(val_preds)

        val_acc = sum(p == l for p, l in zip(val_preds, val_labels)) / len(val_preds)
        print(f"  Epoch {epoch}/{args.epochs}  train_loss={avg_train_loss:.4f}  "
              f"val_acc={val_acc:.4f}")

        # Early stopping on val loss
        if avg_train_loss < best_val_loss:
            best_val_loss = avg_train_loss
            patience_counter = 0
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            model.save_pretrained(OUTPUT_DIR)
            tokenizer.save_pretrained(OUTPUT_DIR)
        else:
            patience_counter += 1
            if patience_counter >= args.patience:
                print(f"  Early stopping at epoch {epoch} (patience={args.patience})")
                break

    # ── Final evaluation on held-out test set ────────────────────────────────
    print("\n[clf1] Loading best checkpoint for test evaluation ...")
    best_model = DistilBertForSequenceClassification.from_pretrained(OUTPUT_DIR).to(device)
    test_preds, test_labels = evaluate(best_model, test_loader, device)

    label_names = [ID2LABEL[i] for i in range(len(LABELS))]
    report = classification_report(
        test_labels, test_preds,
        target_names = label_names,
        output_dict  = True,
    )
    print("\n[clf1] Per-class F1 on test set:")
    for cls in label_names:
        f1 = report[cls]['f1-score']
        flag = '  <<< WARNING: F1 < 0.80' if f1 < F1_WARN_THRESHOLD else ''
        print(f"  {cls:20s}: F1={f1:.4f}{flag}")
    print(f"\n  macro avg F1: {report['macro avg']['f1-score']:.4f}")

    with open(RESULTS_PATH, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    print(f"\n[clf1] Results saved -> {RESULTS_PATH}")

    # Save label map as JSON
    with open(LABEL_MAP_PATH, 'w', encoding='utf-8') as f:
        json.dump(LABEL2ID, f, indent=2)
    print(f"[clf1] Label map saved -> {LABEL_MAP_PATH}")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--epochs',   type=int,   default=5)
    parser.add_argument('--batch',    type=int,   default=32)
    parser.add_argument('--lr',       type=float, default=3e-5)
    parser.add_argument('--max_len',  type=int,   default=64)
    parser.add_argument('--patience', type=int,   default=3)
    parser.add_argument('--seed',     type=int,   default=42)
    args = parser.parse_args()
    train(args)

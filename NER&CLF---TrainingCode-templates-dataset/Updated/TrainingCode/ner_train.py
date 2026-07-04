"""
NER Training — Unified (Scheduling + Learning)
================================================
Uses entity-level seqeval F1 as primary metric (not token accuracy).
Class-weighted loss handles sparse entities (duration, new_taskname, etc.).
One script for both NER models — select mode via --mode flag.

Usage:
    python ner_train.py --mode scheduling
    python ner_train.py --mode learning
    python ner_train.py --mode scheduling --epochs 8 --lr 3e-5 --batch 16

Outputs (per mode):
    scheduling_ner_model/           — best checkpoint
    scheduling_ner_label_map.json   — {label: id} JSON
    scheduling_ner_results.json     — per-entity F1 on test set

    learning_ner_model/
    learning_ner_label_map.json
    learning_ner_results.json
"""

import argparse
import json
import os
import random
from collections import Counter

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset
from transformers import (
    DistilBertTokenizerFast,
    DistilBertForTokenClassification,
    get_linear_schedule_with_warmup,
)

try:
    from seqeval.metrics import classification_report as seq_report
    from seqeval.metrics import f1_score as seq_f1
    SEQEVAL_AVAILABLE = True
except ImportError:
    SEQEVAL_AVAILABLE = False
    print("WARNING: seqeval not installed. Run: pip install seqeval")
    print("         Falling back to token-level accuracy (not recommended).")

# ── Label sets ────────────────────────────────────────────────────────────────
# Fixed explicit lists — never derived from data at runtime.

SCHEDULING_LABELS = [
    'O',
    'B-task_name',   'I-task_name',
    'B-date',        'I-date',
    'B-time',        'I-time',
    'B-priority',    'I-priority',
    'B-status',      'I-status',
    'B-person',      'I-person',
    'B-duration',    'I-duration',
    'B-day',         'I-day',
    'B-new_taskname','I-new_taskname',
    'B-new_date',    'I-new_date',
    'B-new_time',    'I-new_time',
    'B-new_duration','I-new_duration',
    'B-new_priority','I-new_priority',
    'B-new_status',  'I-new_status',
]

LEARNING_LABELS = [
    'O',
    'B-topic',      'I-topic',
    'B-subtopic',   'I-subtopic',
    'B-duration',   'I-duration',
    'B-start_date', 'I-start_date',
    'B-person',     'I-person',
    'B-date',       'I-date',
]

MODE_CONFIG = {
    'scheduling': {
        'labels'     : SCHEDULING_LABELS,
        'train_file' : 'scheduling_ner_train.json',
        'test_file'  : 'scheduling_ner_test.json',
        'output_dir' : 'scheduling_ner_model',
        'label_map'  : 'scheduling_ner_label_map.json',
        'results'    : 'scheduling_ner_results.json',
    },
    'learning': {
        'labels'     : LEARNING_LABELS,
        'train_file' : 'learning_ner_train.json',
        'test_file'  : 'learning_ner_test.json',
        'output_dir' : 'learning_ner_model',
        'label_map'  : 'learning_ner_label_map.json',
        'results'    : 'learning_ner_results.json',
    },
}

MODEL_NAME = 'distilbert-base-uncased'  # uncased — lowercase input in pipeline
DATA_DIR   = os.path.join(os.path.dirname(__file__), '..', 'Datasets')
TRAIN_DIR  = os.path.dirname(__file__)


# ── BIO alignment ─────────────────────────────────────────────────────────────
def align_labels_with_tokens(word_ids, bio_labels, label2id):
    """
    Map word-level BIO labels to subword token positions.
    Only the first subword of each word gets the real label.
    All other subwords and special tokens get -100 (ignored in loss).
    """
    aligned = []
    prev_word_id = None
    for word_id in word_ids:
        if word_id is None:
            aligned.append(-100)
        elif word_id != prev_word_id:
            aligned.append(label2id.get(bio_labels[word_id], label2id['O']))
        else:
            aligned.append(-100)
        prev_word_id = word_id
    return aligned


def example_to_bio(example, labels_set):
    """
    Convert dataset example dict to word-level BIO label sequence.
    Returns (words, bio_labels).
    """
    text     = example['text']
    entities = sorted(example['entities'], key=lambda e: e['start'])
    words    = text.split()

    # Map each character position to its word index
    char_to_word = {}
    pos = 0
    for wi, w in enumerate(words):
        for ci in range(len(w)):
            char_to_word[pos + ci] = wi
        pos += len(w) + 1   # +1 for space

    bio = ['O'] * len(words)
    for ent in entities:
        entity_type = ent['entity']
        start, end  = ent['start'], ent['end']
        value       = ent['value']
        if not value.strip():
            continue

        start_word = char_to_word.get(start)
        # end is exclusive; find last word
        end_word = char_to_word.get(end - 1)
        if start_word is None or end_word is None:
            continue

        # Only tag if B- and I- labels exist for this entity type
        if f'B-{entity_type}' not in labels_set:
            continue

        bio[start_word] = f'B-{entity_type}'
        for wi in range(start_word + 1, end_word + 1):
            bio[wi] = f'I-{entity_type}'

    return words, bio


# ── Dataset ───────────────────────────────────────────────────────────────────
class NERDataset(Dataset):
    def __init__(self, examples, tokenizer, label2id, labels_set, max_len=128):
        self.examples   = examples
        self.tokenizer  = tokenizer
        self.label2id   = label2id
        self.labels_set = labels_set
        self.max_len    = max_len

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        ex = self.examples[idx]
        words, bio_labels = example_to_bio(ex, self.labels_set)
        words = [w.lower() for w in words]

        enc = self.tokenizer(
            words,
            is_split_into_words = True,
            max_length          = self.max_len,
            padding             = 'max_length',
            truncation          = True,
            return_tensors      = 'pt',
        )
        word_ids       = enc.word_ids(batch_index=0)
        aligned_labels = align_labels_with_tokens(word_ids, bio_labels, self.label2id)

        return {
            'input_ids'      : enc['input_ids'].squeeze(0),
            'attention_mask' : enc['attention_mask'].squeeze(0),
            'labels'         : torch.tensor(aligned_labels, dtype=torch.long),
        }


# ── Class weights ─────────────────────────────────────────────────────────────
def compute_class_weights(train_data, labels, label2id, tokenizer, max_len=128):
    """
    Count token-level label occurrences in training data to build
    inverse-frequency weights. O label gets weight 0.1 (dominant, downsample).
    """
    counts = Counter()
    labels_set = set(labels)

    for ex in train_data:
        words, bio = example_to_bio(ex, labels_set)
        words      = [w.lower() for w in words]
        enc        = tokenizer(words, is_split_into_words=True,
                               max_length=max_len, truncation=True)
        word_ids   = enc.word_ids(batch_index=0)
        aligned    = align_labels_with_tokens(word_ids, bio, label2id)
        for lid in aligned:
            if lid != -100:
                counts[lid] += 1

    total = sum(counts.values())
    weights = []
    for i, lbl in enumerate(labels):
        cnt = counts.get(i, 1)
        w   = total / (len(labels) * cnt)
        if lbl == 'O':
            w = min(w, 0.1)   # cap O weight — it's always dominant
        weights.append(w)

    return torch.tensor(weights, dtype=torch.float)


# ── Evaluation ────────────────────────────────────────────────────────────────
def evaluate_ner(model, loader, id2label, device):
    model.eval()
    all_preds_seq  = []
    all_labels_seq = []

    with torch.no_grad():
        for batch in loader:
            input_ids = batch['input_ids'].to(device)
            attn_mask = batch['attention_mask'].to(device)
            labels    = batch['labels'].to(device)
            logits    = model(input_ids=input_ids, attention_mask=attn_mask).logits
            preds     = logits.argmax(dim=-1)

            for pred_row, label_row in zip(preds, labels):
                pred_seq  = []
                label_seq = []
                for p, l in zip(pred_row.tolist(), label_row.tolist()):
                    if l == -100:
                        continue
                    pred_seq.append(id2label[p])
                    label_seq.append(id2label[l])
                all_preds_seq.append(pred_seq)
                all_labels_seq.append(label_seq)

    return all_preds_seq, all_labels_seq


def compute_f1(preds_seq, labels_seq, id2label):
    if SEQEVAL_AVAILABLE:
        return seq_f1(labels_seq, preds_seq)
    # Fallback: token accuracy (weak but better than nothing)
    correct = total = 0
    for ps, ls in zip(preds_seq, labels_seq):
        for p, l in zip(ps, ls):
            total   += 1
            correct += (p == l)
    return correct / total if total else 0.0


# ── Training ──────────────────────────────────────────────────────────────────
def seed_everything(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def train(args):
    cfg    = MODE_CONFIG[args.mode]
    labels = cfg['labels']
    label2id = {l: i for i, l in enumerate(labels)}
    id2label = {i: l for l, i in label2id.items()}
    labels_set = set(labels)

    output_dir    = os.path.join(TRAIN_DIR, cfg['output_dir'])
    label_map_path = os.path.join(TRAIN_DIR, cfg['label_map'])
    results_path   = os.path.join(TRAIN_DIR, cfg['results'])

    seed_everything(args.seed)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"[ner/{args.mode}] Device: {device}  Labels: {len(labels)}")

    tokenizer  = DistilBertTokenizerFast.from_pretrained(MODEL_NAME)
    train_data = load_json(os.path.join(DATA_DIR, cfg['train_file']))
    test_data  = load_json(os.path.join(DATA_DIR, cfg['test_file']))

    random.shuffle(train_data)
    val_cut    = int(len(train_data) * 0.9)
    val_data   = train_data[val_cut:]
    train_data = train_data[:val_cut]

    print(f"[ner/{args.mode}] Train={len(train_data)}  Val={len(val_data)}  Test={len(test_data)}")

    g = torch.Generator()
    g.manual_seed(args.seed)

    train_loader = DataLoader(
        NERDataset(train_data, tokenizer, label2id, labels_set, args.max_len),
        batch_size=args.batch, shuffle=True, num_workers=0, generator=g,
    )
    val_loader = DataLoader(
        NERDataset(val_data, tokenizer, label2id, labels_set, args.max_len),
        batch_size=args.batch, shuffle=False, num_workers=0,
    )
    test_loader = DataLoader(
        NERDataset(test_data, tokenizer, label2id, labels_set, args.max_len),
        batch_size=args.batch, shuffle=False, num_workers=0,
    )

    print(f"[ner/{args.mode}] Computing class weights ...")
    class_weights = compute_class_weights(
        train_data, labels, label2id, tokenizer, args.max_len
    ).to(device)
    loss_fn = torch.nn.CrossEntropyLoss(weight=class_weights, ignore_index=-100)

    model = DistilBertForTokenClassification.from_pretrained(
        MODEL_NAME,
        num_labels = len(labels),
        id2label   = id2label,
        label2id   = label2id,
    ).to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    total_steps = len(train_loader) * args.epochs
    scheduler   = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps   = total_steps // 10,
        num_training_steps = total_steps,
    )

    best_val_f1      = 0.0
    patience_counter = 0

    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0

        for batch in train_loader:
            input_ids = batch['input_ids'].to(device)
            attn_mask = batch['attention_mask'].to(device)
            labels_t  = batch['labels'].to(device)

            optimizer.zero_grad()
            logits = model(input_ids=input_ids, attention_mask=attn_mask).logits

            # Flatten for weighted loss
            logits_flat = logits.view(-1, len(labels))
            labels_flat = labels_t.view(-1)
            loss        = loss_fn(logits_flat, labels_flat)

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            total_loss += loss.item()

        avg_loss = total_loss / len(train_loader)

        val_preds, val_labels = evaluate_ner(model, val_loader, id2label, device)
        val_f1 = compute_f1(val_preds, val_labels, id2label)
        print(f"  Epoch {epoch}/{args.epochs}  loss={avg_loss:.4f}  "
              f"val_entity_F1={val_f1:.4f}")

        if val_f1 > best_val_f1:
            best_val_f1      = val_f1
            patience_counter = 0
            os.makedirs(output_dir, exist_ok=True)
            model.save_pretrained(output_dir)
            tokenizer.save_pretrained(output_dir)
        else:
            patience_counter += 1
            if patience_counter >= args.patience:
                print(f"  Early stopping at epoch {epoch}")
                break

    # ── Test evaluation ───────────────────────────────────────────────────────
    print(f"\n[ner/{args.mode}] Loading best checkpoint ...")
    best_model = DistilBertForTokenClassification.from_pretrained(output_dir).to(device)
    test_preds, test_labels_seq = evaluate_ner(best_model, test_loader, id2label, device)

    test_f1 = compute_f1(test_preds, test_labels_seq, id2label)
    print(f"\n[ner/{args.mode}] Test entity F1: {test_f1:.4f}")

    results = {'overall_entity_f1': test_f1}

    if SEQEVAL_AVAILABLE:
        report_str = seq_report(test_labels_seq, test_preds, output_dict=False)
        report_dict = seq_report(test_labels_seq, test_preds, output_dict=True)
        print("\n[ner] Per-entity F1:")
        print(report_str)
        results['per_entity'] = report_dict

        # Warn on weak entities
        for ent_type, metrics in report_dict.items():
            if isinstance(metrics, dict) and 'f1-score' in metrics:
                f1 = metrics['f1-score']
                if f1 < 0.85 and ent_type not in ('macro avg', 'weighted avg', 'micro avg'):
                    print(f"  WARNING: {ent_type} F1={f1:.4f} < 0.85")

    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    with open(label_map_path, 'w', encoding='utf-8') as f:
        json.dump(label2id, f, indent=2)

    print(f"\n[ner/{args.mode}] Results   -> {results_path}")
    print(f"[ner/{args.mode}] Label map -> {label_map_path}")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode',     choices=['scheduling', 'learning'], required=True)
    parser.add_argument('--epochs',   type=int,   default=8)
    parser.add_argument('--batch',    type=int,   default=16)
    parser.add_argument('--lr',       type=float, default=3e-5)
    parser.add_argument('--max_len',  type=int,   default=128)
    parser.add_argument('--patience', type=int,   default=3)
    parser.add_argument('--seed',     type=int,   default=42)
    args = parser.parse_args()
    train(args)

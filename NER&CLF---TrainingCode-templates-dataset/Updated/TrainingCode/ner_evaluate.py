"""
NER Evaluator — Interactive + Batch + Position-Swap Tests
===========================================================
Loads a trained NER model and evaluates it on custom inputs or test files.

Usage:
    # Interactive mode — type sentences, see entity extraction
    python ner_evaluate.py --mode scheduling --interactive

    # Batch mode — run on held-out test file, print per-entity F1
    python ner_evaluate.py --mode scheduling --batch

    # Position-swap test — run built-in overfitting probe
    python ner_evaluate.py --mode scheduling --swap_test

    # All at once
    python ner_evaluate.py --mode scheduling --batch --swap_test --interactive
"""

import argparse
import json
import os
import torch
from transformers import (
    DistilBertTokenizerFast,
    DistilBertForTokenClassification,
)

try:
    from seqeval.metrics import classification_report as seq_report
    from seqeval.metrics import f1_score as seq_f1
    SEQEVAL_AVAILABLE = True
except ImportError:
    SEQEVAL_AVAILABLE = False
    print("WARNING: seqeval not installed — batch F1 unavailable. pip install seqeval")

# ── Config ────────────────────────────────────────────────────────────────────
TRAIN_DIR = os.path.dirname(__file__)
DATA_DIR  = os.path.join(TRAIN_DIR, '..', 'Datasets')

MODE_CONFIG = {
    'scheduling': {
        'model_dir'  : os.path.join(TRAIN_DIR, 'scheduling_ner_model'),
        'label_map'  : os.path.join(TRAIN_DIR, 'scheduling_ner_label_map.json'),
        'test_file'  : os.path.join(DATA_DIR,  'scheduling_ner_test.json'),
    },
    'learning': {
        'model_dir'  : os.path.join(TRAIN_DIR, 'learning_ner_model'),
        'label_map'  : os.path.join(TRAIN_DIR, 'learning_ner_label_map.json'),
        'test_file'  : os.path.join(DATA_DIR,  'learning_ner_test.json'),
    },
}

# ── Position-swap test cases ──────────────────────────────────────────────────
# Each group contains the same semantic intent in different word orders.
# A well-generalised model should extract the same entities regardless of order.

POSITION_SWAP_TESTS = {
    'scheduling': [
        {
            'description': 'task_name + date — canonical, date-first, bare',
            'cases': [
                {
                    'text'    : 'add urdu exam on monday',
                    'expected': [('urdu exam', 'task_name'), ('monday', 'date')],
                },
                {
                    'text'    : 'monday urdu exam add it',
                    'expected': [('urdu exam', 'task_name'), ('monday', 'date')],
                },
                {
                    'text'    : 'urdu exam monday',
                    'expected': [('urdu exam', 'task_name'), ('monday', 'date')],
                },
            ],
        },
        {
            'description': 'task_name + date + time — 3 positions',
            'cases': [
                {
                    'text'    : 'schedule physics exam on friday at 3pm',
                    'expected': [('physics exam', 'task_name'), ('friday', 'date'), ('3pm', 'time')],
                },
                {
                    'text'    : 'friday 3pm physics exam',
                    'expected': [('physics exam', 'task_name'), ('friday', 'date'), ('3pm', 'time')],
                },
                {
                    'text'    : 'physics exam friday 3pm',
                    'expected': [('physics exam', 'task_name'), ('friday', 'date'), ('3pm', 'time')],
                },
            ],
        },
        {
            'description': 'person must NOT bleed into task_name',
            'cases': [
                {
                    'text'    : 'add Ali project on tuesday',
                    'expected': [('Ali project', 'task_name'), ('tuesday', 'date')],
                },
                {
                    'text'    : 'add cs lab with Ali on tuesday',
                    'expected': [('cs lab', 'task_name'), ('Ali', 'person'), ('tuesday', 'date')],
                },
                {
                    'text'    : 'add lab report collaborator is Hassan',
                    'expected': [('lab report', 'task_name'), ('Hassan', 'person')],
                },
            ],
        },
        {
            'description': 'priority position variants',
            'cases': [
                {
                    'text'    : 'add math exam on monday high priority',
                    'expected': [('math exam', 'task_name'), ('monday', 'date'), ('high', 'priority')],
                },
                {
                    'text'    : 'high priority math exam on monday',
                    'expected': [('math exam', 'task_name'), ('monday', 'date'), ('high', 'priority')],
                },
            ],
        },
    ],
    'learning': [
        {
            'description': 'topic + duration — canonical vs bare',
            'cases': [
                {
                    'text'    : 'create a python roadmap for 2 weeks',
                    'expected': [('python', 'topic'), ('2 weeks', 'duration')],
                },
                {
                    'text'    : 'python 2 weeks roadmap',
                    'expected': [('python', 'topic'), ('2 weeks', 'duration')],
                },
            ],
        },
        {
            'description': 'topic + subtopic + start_date',
            'cases': [
                {
                    'text'    : 'learn python oop starting next monday',
                    'expected': [('python', 'topic'), ('oop', 'subtopic'), ('next monday', 'start_date')],
                },
                {
                    'text'    : 'next monday start python oop',
                    'expected': [('python', 'topic'), ('oop', 'subtopic'), ('next monday', 'start_date')],
                },
            ],
        },
    ],
}


# ── Model loading ─────────────────────────────────────────────────────────────
def load_model(mode):
    cfg       = MODE_CONFIG[mode]
    model_dir = cfg['model_dir']

    if not os.path.exists(model_dir):
        raise FileNotFoundError(
            f"No trained model at '{model_dir}'. "
            f"Run: python ner_train.py --mode {mode}"
        )

    with open(cfg['label_map'], encoding='utf-8') as f:
        label2id = json.load(f)
    id2label = {int(i): l for l, i in label2id.items()}

    tokenizer = DistilBertTokenizerFast.from_pretrained(model_dir)
    model     = DistilBertForTokenClassification.from_pretrained(model_dir)
    model.eval()

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model  = model.to(device)

    return model, tokenizer, id2label, device


# ── Prediction ────────────────────────────────────────────────────────────────
def predict(text, model, tokenizer, id2label, device):
    """Extract entities from a single text string. Returns list of (value, entity) tuples."""
    words = text.lower().split()
    enc   = tokenizer(
        words,
        is_split_into_words = True,
        return_tensors      = 'pt',
        truncation          = True,
        max_length          = 128,
    ).to(device)

    with torch.no_grad():
        logits = model(**enc).logits
    pred_ids = logits.argmax(dim=-1).squeeze(0).tolist()
    word_ids = enc.word_ids(batch_index=0)

    # Collapse subword predictions — take first subword's label per word
    word_labels = {}
    for tok_idx, word_id in enumerate(word_ids):
        if word_id is None or word_id in word_labels:
            continue
        word_labels[word_id] = id2label.get(pred_ids[tok_idx], 'O')

    # Build entity spans from BIO labels
    entities = []
    current_entity = None
    current_words  = []

    for wi in range(len(words)):
        label = word_labels.get(wi, 'O')
        if label.startswith('B-'):
            if current_entity:
                entities.append((' '.join(current_words), current_entity))
            current_entity = label[2:]
            current_words  = [words[wi]]
        elif label.startswith('I-') and current_entity == label[2:]:
            current_words.append(words[wi])
        else:
            if current_entity:
                entities.append((' '.join(current_words), current_entity))
            current_entity = None
            current_words  = []

    if current_entity:
        entities.append((' '.join(current_words), current_entity))

    return entities


# ── Test file BIO conversion (for batch eval) ─────────────────────────────────
def example_to_bio(example, label2id):
    text     = example['text']
    entities = sorted(example['entities'], key=lambda e: e['start'])
    words    = text.split()

    char_to_word = {}
    pos = 0
    for wi, w in enumerate(words):
        for ci in range(len(w)):
            char_to_word[pos + ci] = wi
        pos += len(w) + 1

    bio = ['O'] * len(words)
    for ent in entities:
        if f"B-{ent['entity']}" not in label2id:
            continue
        s = char_to_word.get(ent['start'])
        e = char_to_word.get(ent['end'] - 1)
        if s is None or e is None:
            continue
        bio[s] = f"B-{ent['entity']}"
        for wi in range(s + 1, e + 1):
            bio[wi] = f"I-{ent['entity']}"

    return words, bio


# ── Modes ─────────────────────────────────────────────────────────────────────
def run_batch(mode, model, tokenizer, id2label, device, label2id):
    test_file = MODE_CONFIG[mode]['test_file']
    print(f"\n[batch] Loading {test_file} ...")
    with open(test_file, encoding='utf-8') as f:
        test_data = json.load(f)

    all_pred_seqs  = []
    all_label_seqs = []

    for ex in test_data:
        words, bio = example_to_bio(ex, label2id)
        words = [w.lower() for w in words]
        enc = tokenizer(
            words,
            is_split_into_words = True,
            return_tensors      = 'pt',
            truncation          = True,
            max_length          = 128,
        ).to(device)

        with torch.no_grad():
            logits = model(**enc).logits
        pred_ids = logits.argmax(dim=-1).squeeze(0).tolist()
        word_ids = enc.word_ids(batch_index=0)

        pred_bio  = []
        label_bio = []
        for tok_idx, word_id in enumerate(word_ids):
            if word_id is None:
                continue
            # first subword only
            if tok_idx > 0 and word_ids[tok_idx - 1] == word_id:
                continue
            pred_bio.append(id2label.get(pred_ids[tok_idx], 'O'))
            label_bio.append(bio[word_id])

        all_pred_seqs.append(pred_bio)
        all_label_seqs.append(label_bio)

    if SEQEVAL_AVAILABLE:
        print("\n[batch] Per-entity F1:")
        print(seq_report(all_label_seqs, all_pred_seqs))
        overall = seq_f1(all_label_seqs, all_pred_seqs)
        print(f"[batch] Overall entity F1: {overall:.4f}")
    else:
        correct = total = 0
        for ps, ls in zip(all_pred_seqs, all_label_seqs):
            for p, l in zip(ps, ls):
                total   += 1
                correct += (p == l)
        print(f"[batch] Token accuracy: {correct/total:.4f}  (install seqeval for F1)")


def run_swap_test(mode, model, tokenizer, id2label, device):
    cases = POSITION_SWAP_TESTS.get(mode, [])
    if not cases:
        print(f"[swap] No test cases for mode '{mode}'")
        return

    print(f"\n[swap] Position-swap tests for mode='{mode}'")
    label2id = {v: k for k, v in id2label.items()}
    total_cases = passed = 0

    for group in cases:
        print(f"\n  Group: {group['description']}")
        for case in group['cases']:
            text     = case['text']
            expected = case['expected']   # list of (value, entity)
            predicted = predict(text, model, tokenizer, id2label, device)

            # Match by entity type (value matching is fuzzy — lowercase strip)
            pred_set     = {(v.lower().strip(), e) for v, e in predicted}
            expected_set = {(v.lower().strip(), e) for v, e in expected}
            ok = expected_set.issubset(pred_set)

            status = 'PASS' if ok else 'FAIL'
            total_cases += 1
            passed      += ok
            print(f"    [{status}] \"{text}\"")
            if not ok:
                missing = expected_set - pred_set
                extra   = pred_set - expected_set
                if missing:
                    print(f"           MISSING : {missing}")
                if extra:
                    print(f"           EXTRA   : {extra}")

    print(f"\n[swap] Result: {passed}/{total_cases} passed")
    if passed < total_cases:
        print("[swap] FAIL — model still shows positional bias. "
              "Consider more training epochs or more word-order variants.")
    else:
        print("[swap] PASS — model generalises across word orders.")


def run_interactive(mode, model, tokenizer, id2label, device):
    print(f"\n[interactive] NER mode='{mode}'. Type text to extract entities. 'quit' to exit.\n")
    while True:
        try:
            text = input("Input: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text.lower() in ('quit', 'exit', 'q'):
            break
        if not text:
            continue
        entities = predict(text, model, tokenizer, id2label, device)
        if entities:
            for value, entity in entities:
                print(f"  {entity:20s}: {value!r}")
        else:
            print("  (no entities found)")


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode',        choices=['scheduling', 'learning'], required=True)
    parser.add_argument('--batch',       action='store_true', help='Run batch F1 on test file')
    parser.add_argument('--swap_test',   action='store_true', help='Run position-swap tests')
    parser.add_argument('--interactive', action='store_true', help='Interactive entity extraction')
    args = parser.parse_args()

    if not any([args.batch, args.swap_test, args.interactive]):
        print("Specify at least one of: --batch  --swap_test  --interactive")
        parser.print_help()
        return

    print(f"[ner_evaluate] Loading model for mode='{args.mode}' ...")
    model, tokenizer, id2label, device = load_model(args.mode)
    label2id = {v: k for k, v in id2label.items()}
    print(f"[ner_evaluate] Model loaded. Device: {device}")

    if args.batch:
        run_batch(args.mode, model, tokenizer, id2label, device, label2id)
    if args.swap_test:
        run_swap_test(args.mode, model, tokenizer, id2label, device)
    if args.interactive:
        run_interactive(args.mode, model, tokenizer, id2label, device)


if __name__ == '__main__':
    main()

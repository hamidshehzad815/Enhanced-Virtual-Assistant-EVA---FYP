"""
Phase 4 — NER dataset augmentation with BIO label preservation.

Augmentations work on (token, label) pairs or entity/O chunks so entity
boundaries stay aligned after capitalization, typos, fillers, abbreviations,
punctuation noise, and controlled word-order shuffling.
"""

from __future__ import annotations

import copy
import random
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

Chunk = Tuple[str, List[str], List[str]]  # ("O"|"E", tokens, labels)


def split_into_chunks(tokens: Sequence[str], labels: Sequence[str]) -> List[Chunk]:
    """Split into O-runs and entity spans (B- + I-* chains)."""
    chunks: List[Chunk] = []
    i = 0
    n = len(tokens)

    while i < n:
        label = labels[i]
        if label == "O":
            start = i
            while i < n and labels[i] == "O":
                i += 1
            chunks.append(("O", list(tokens[start:i]), list(labels[start:i])))
        elif label.startswith("B-"):
            etype = label[2:]
            start = i
            i += 1
            while i < n and labels[i] == f"I-{etype}":
                i += 1
            chunks.append(("E", list(tokens[start:i]), list(labels[start:i])))
        else:
            chunks.append(("E", [tokens[i]], [labels[i]]))
            i += 1

    return chunks


def chunks_to_example(chunks: Sequence[Chunk], intent: str) -> Dict[str, Any]:
    tokens: List[str] = []
    labels: List[str] = []
    for _, toks, lbls in chunks:
        tokens.extend(toks)
        labels.extend(lbls)
    return {
        "text": " ".join(tokens),
        "tokens": tokens,
        "labels": labels,
        "intent": intent,
    }


def _random_case(token: str, rng: random.Random) -> str:
    # Favour lower/mixed case — full UPPER breaks cased BERT at inference; uncased still prefers natural casing.
    mode = rng.randint(0, 9)
    if mode == 0:
        return token.upper()
    if mode <= 5:
        return token.lower()
    if mode == 7:
        return token.capitalize()
    if len(token) <= 1:
        return token
    return token[0].upper() + token[1:].lower()


def _apply_typo_char(token: str, rng: random.Random) -> str:
    if len(token) < 2:
        return token
    op = rng.choice(["swap", "delete", "insert", "substitute"])
    chars = list(token)
    idx = rng.randrange(len(chars))

    if op == "swap" and len(chars) >= 2:
        j = min(idx + 1, len(chars) - 1)
        chars[idx], chars[j] = chars[j], chars[idx]
    elif op == "delete":
        del chars[idx]
    elif op == "insert":
        chars.insert(idx, rng.choice("aeiou"))
    else:
        chars[idx] = rng.choice("abcdefghijklmnopqrstuvwxyz")

    return "".join(chars) if chars else token


def _replace_token(token: str, mapping: Dict[str, str]) -> str:
    lower = token.lower()
    if lower in mapping:
        repl = mapping[lower]
        if token.isupper():
            return repl.upper()
        if token[0].isupper():
            return repl.capitalize()
        return repl
    return token


def augment_capitalization(
    tokens: List[str],
    labels: List[str],
    rng: random.Random,
) -> Tuple[List[str], List[str]]:
    out_toks = [_random_case(t, rng) for t in tokens]
    return out_toks, labels[:]


def augment_typo(
    tokens: List[str],
    labels: List[str],
    rng: random.Random,
    entity_typos: Dict[str, str],
    o_typos: Dict[str, str],
    protected: Sequence[str],
) -> Tuple[List[str], List[str]]:
    indices = list(range(len(tokens)))
    rng.shuffle(indices)

    for idx in indices:
        tok = tokens[idx]
        low = tok.lower()
        if low in protected:
            continue

        if labels[idx] == "O" and low in o_typos:
            tokens = tokens[:]
            labels = labels[:]
            tokens[idx] = _replace_token(tok, o_typos)
            return tokens, labels

        if labels[idx] != "O" and low in entity_typos:
            tokens = tokens[:]
            labels = labels[:]
            tokens[idx] = _replace_token(tok, entity_typos)
            return tokens, labels

        if rng.random() < 0.4 and len(tok) >= 4 and low not in protected:
            tokens = tokens[:]
            labels = labels[:]
            tokens[idx] = _apply_typo_char(tok, rng)
            return tokens, labels

    return tokens, labels


def augment_filler_prefix(
    tokens: List[str],
    labels: List[str],
    filler: str,
) -> Tuple[List[str], List[str]]:
    filler_tokens = filler.split()
    return filler_tokens + tokens, ["O"] * len(filler_tokens) + labels


def augment_filler_suffix(
    tokens: List[str],
    labels: List[str],
    filler: str,
) -> Tuple[List[str], List[str]]:
    filler_tokens = filler.split()
    return tokens + filler_tokens, labels + ["O"] * len(filler_tokens)


def augment_punctuation(
    tokens: List[str],
    labels: List[str],
    rng: random.Random,
) -> Tuple[List[str], List[str]]:
    o_indices = [i for i, lbl in enumerate(labels) if lbl == "O"]
    if not o_indices:
        return tokens, labels
    idx = rng.choice(o_indices)
    tokens = tokens[:]
    labels = labels[:]
    punct = rng.choice([",", "!", "..."])
    tokens[idx] = tokens[idx] + punct
    return tokens, labels


def augment_abbreviation(
    tokens: List[str],
    labels: List[str],
    rng: random.Random,
    day_abbrevs: Dict[str, str],
    time_abbrevs: Dict[str, str],
    duration_abbrevs: Dict[str, str],
) -> Tuple[List[str], List[str]]:
    combined = {**day_abbrevs, **time_abbrevs, **duration_abbrevs}
    candidates = [i for i, t in enumerate(tokens) if t.lower() in combined]
    if not candidates:
        return tokens, labels
    idx = rng.choice(candidates)
    tokens = tokens[:]
    labels = labels[:]
    tokens[idx] = _replace_token(tokens[idx], combined)
    return tokens, labels


def augment_extra_spaces(text: str) -> str:
    """Double space after first O-word (text only; tokens rebuilt on merge)."""
    return re.sub(r"(\w+) ", r"\1  ", text, count=1)


def augment_word_order_shuffle(
    tokens: List[str],
    labels: List[str],
    rng: random.Random,
) -> Tuple[List[str], List[str]]:
    chunks = split_into_chunks(tokens, labels)
    if len(chunks) < 3:
        return tokens, labels
    entity_count = sum(1 for kind, _, _ in chunks if kind == "E")
    if entity_count < 1:
        return tokens, labels

    order = list(range(len(chunks)))
    rng.shuffle(order)
    if order == list(range(len(chunks))):
        rng.shuffle(order)

    shuffled = [chunks[i] for i in order]
    out = chunks_to_example(shuffled, "")
    return out["tokens"], out["labels"]


def augment_example(
    example: Dict[str, Any],
    cfg: Dict[str, Any],
    rng: random.Random,
) -> Optional[Dict[str, Any]]:
    """Return one augmented copy, or None if no change applied."""
    tokens = list(example["tokens"])
    labels = list(example["labels"])
    intent = example.get("intent", "")
    original_text = " ".join(tokens)

    probs = cfg.get("probabilities", {})
    applied = False

    if rng.random() < probs.get("capitalization", 0):
        tokens, labels = augment_capitalization(tokens, labels, rng)
        applied = True

    if rng.random() < probs.get("typo", 0):
        new_toks, new_lbls = augment_typo(
            tokens,
            labels,
            rng,
            cfg.get("entity_typos", {}),
            cfg.get("o_token_typos", {}),
            cfg.get("protected_from_typo", []),
        )
        if new_toks != tokens:
            tokens, labels = new_toks, new_lbls
            applied = True

    if rng.random() < probs.get("filler_prefix", 0):
        filler = rng.choice(cfg.get("fillers_prefix", ["please"]))
        tokens, labels = augment_filler_prefix(tokens, labels, filler)
        applied = True

    if rng.random() < probs.get("filler_suffix", 0):
        filler = rng.choice(cfg.get("fillers_suffix", ["please"]))
        tokens, labels = augment_filler_suffix(tokens, labels, filler)
        applied = True

    if rng.random() < probs.get("punctuation", 0):
        new_toks, new_lbls = augment_punctuation(tokens, labels, rng)
        if new_toks != tokens:
            tokens, labels = new_toks, new_lbls
            applied = True

    if rng.random() < probs.get("abbreviation", 0):
        new_toks, new_lbls = augment_abbreviation(
            tokens,
            labels,
            rng,
            cfg.get("day_abbreviations", {}),
            cfg.get("time_abbreviations", {}),
            cfg.get("duration_abbreviations", {}),
        )
        if new_toks != tokens:
            tokens, labels = new_toks, new_lbls
            applied = True

    if rng.random() < probs.get("word_order_shuffle", 0):
        new_toks, new_lbls = augment_word_order_shuffle(tokens, labels, rng)
        if " ".join(new_toks) != " ".join(tokens):
            tokens, labels = new_toks, new_lbls
            applied = True

    text = " ".join(tokens)

    if not applied or text == original_text:
        return None

    return {
        "text": text,
        "tokens": tokens,
        "labels": labels,
        "intent": intent,
        "augmented": True,
        "source_text": original_text,
    }


def augment_dataset(
    examples: List[Dict[str, Any]],
    cfg: Dict[str, Any],
    variants_per_example: int = 1,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    augmented: List[Dict[str, Any]] = []
    seen_text: set = set()

    for ex in examples:
        for _ in range(variants_per_example):
            aug = augment_example(ex, cfg, rng)
            if aug is None:
                continue
            key = aug["text"]
            if key in seen_text:
                continue
            seen_text.add(key)
            augmented.append(aug)

    return augmented


def load_hard_negatives(path: str, key: str) -> List[Dict[str, Any]]:
    import json
    from pathlib import Path

    with Path(path).open(encoding="utf-8") as fh:
        data = json.load(fh)
    items = data.get(key, [])
    for item in items:
        item["hard_negative"] = True
    return items


def merge_datasets(
    raw: List[Dict[str, Any]],
    augmented: List[Dict[str, Any]],
    hard_negatives: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen: set = set()

    for batch in (raw, augmented, hard_negatives):
        for ex in batch:
            text = ex.get("text", "")
            if not text or text in seen:
                continue
            seen.add(text)
            merged.append(copy.deepcopy(ex))

    return merged

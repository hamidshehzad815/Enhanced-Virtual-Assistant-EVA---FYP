"""
Instantiate NER templates with slot values and assign BIO labels per token.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")
_TOKEN_RE = re.compile(r"\S+")


def extract_placeholders(template: str) -> List[str]:
    """Return placeholder slot names in left-to-right order."""
    return _PLACEHOLDER_RE.findall(template)


def fill_template(
    template: str,
    slot_values: Dict[str, str],
) -> Tuple[str, Dict[str, Tuple[int, int]]]:
    """
    Replace {slot} placeholders left-to-right.
    Returns filled text and character spans per slot name (first occurrence only).
    """
    spans: Dict[str, Tuple[int, int]] = {}
    parts: List[str] = []
    cursor = 0

    for match in _PLACEHOLDER_RE.finditer(template):
        parts.append(template[cursor : match.start()])
        slot = match.group(1)
        if slot not in slot_values:
            raise KeyError(f"Missing slot value for {{{slot}}} in template: {template!r}")
        value = slot_values[slot]
        start = sum(len(p) for p in parts)
        parts.append(value)
        end = start + len(value)
        if slot not in spans:
            spans[slot] = (start, end)
        cursor = match.end()

    parts.append(template[cursor:])
    return "".join(parts), spans


def tokenize_with_offsets(text: str) -> List[Tuple[str, int, int]]:
    return [(m.group(), m.start(), m.end()) for m in _TOKEN_RE.finditer(text)]


def spans_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


def assign_bio_labels(
    token_spans: List[Tuple[str, int, int]],
    entity_spans: Dict[str, Tuple[int, int]],
) -> List[str]:
    """Assign BIO labels to whitespace tokens from character entity spans."""
    labels = ["O"] * len(token_spans)

    for entity_type, (estart, eend) in entity_spans.items():
        first = True
        for i, (_tok, ts, te) in enumerate(token_spans):
            if not spans_overlap(ts, te, estart, eend):
                continue
            labels[i] = ("B-" if first else "I-") + entity_type
            first = False

    return labels


def build_example(
    template_text: str,
    entity_slots: List[str],
    slot_values: Dict[str, str],
) -> Dict[str, object]:
    """Build one training example dict with text, tokens, and BIO labels."""
    placeholders = extract_placeholders(template_text)
    if set(placeholders) != set(entity_slots):
        raise ValueError(
            f"Template entity mismatch. text={template_text!r} "
            f"entities={entity_slots} placeholders={placeholders}"
        )

    text, char_spans = fill_template(template_text, slot_values)
    token_spans = tokenize_with_offsets(text)
    tokens = [t for t, _, _ in token_spans]
    labels = assign_bio_labels(token_spans, char_spans)

    return {
        "text": text,
        "tokens": tokens,
        "labels": labels,
    }


def merge_bio_tokens(tokens: List[str], labels: List[str]) -> Dict[str, List[str]]:
    """Reconstruct entity strings from BIO tags (for validation)."""
    entities: Dict[str, List[str]] = {}
    current_type = ""
    current_tokens: List[str] = []

    for tok, label in zip(tokens, labels):
        if label == "O" or "-" not in label:
            if current_type:
                entities.setdefault(current_type, []).append(" ".join(current_tokens))
            current_type = ""
            current_tokens = []
            continue

        prefix, etype = label.split("-", 1)
        if prefix == "B" or etype != current_type:
            if current_type:
                entities.setdefault(current_type, []).append(" ".join(current_tokens))
            current_type = etype
            current_tokens = [tok]
        else:
            current_tokens.append(tok)

    if current_type:
        entities.setdefault(current_type, []).append(" ".join(current_tokens))

    return entities

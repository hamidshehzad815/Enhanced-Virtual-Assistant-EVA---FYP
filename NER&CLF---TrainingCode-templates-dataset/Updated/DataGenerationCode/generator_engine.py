"""
Generator Engine
================
Rewrite of Current(old) _Cycler + _find_span + generate() + save_dataset().

Key fixes vs old version:
  - _Cycler: shuffle=True mode — shuffles each full cycle pass so model
    cannot learn (template_index, value_index) positional correlations
  - _find_span: strips trailing punctuation before search to fix "5pm," misses
  - generate(): shuffles final output list before returning
  - inject_noise(): randomly drops/swaps chars in non-entity tokens (typo sim)
  - flag_rate_by_template: logs which templates flag most so you can fix them
  - Zero-entity templates filtered out for NER automatically when ner_only=True

Usage
-----
    from generator_engine import generate, save_dataset, inject_noise

    clean, flagged = generate(
        templates     = ADD_TEMPLATES,
        entity_values = {"task_name": TASK_NAMES, "date": DATES},
        intent        = "scheduling_add",
        count         = 3000,
        shuffle       = True,   # default True for NER
        ner_only      = True,   # skip zero-entity templates for NER
        noise_rate    = 0.05,   # 0.0 to disable
    )
    save_dataset(clean, flagged, "Datasets/scheduling_ner.json")
"""

import json
import os
import re
import random
from collections import defaultdict


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

class _Cycler:
    """
    Sequential cycling over a list with optional shuffle-per-pass.

    shuffle=False (old behaviour): items returned in fixed order indefinitely.
    shuffle=True  (new default):   each full pass through the list is shuffled
                                   independently, breaking positional correlations.
    """

    def __init__(self, items: list, shuffle: bool = True, seed: int = None):
        if not items:
            raise ValueError("Value list must not be empty.")
        self._original = list(items)
        self._shuffle  = shuffle
        self._rng      = random.Random(seed)
        self._queue    = []
        self._refill()

    def _refill(self):
        self._queue = list(self._original)
        if self._shuffle:
            self._rng.shuffle(self._queue)

    def next(self):
        if not self._queue:
            self._refill()
        return self._queue.pop()


def _strip_punct(value: str) -> str:
    """Strip trailing punctuation that may attach to a slot value in text."""
    return value.rstrip(".,;:!?\"'")


def _find_span(text: str, value: str):
    """
    Return (start, end) of *value* inside *text* (case-insensitive).
    Strips trailing punctuation from value before searching.
    Returns None when value is not found or appears more than once (ambiguous).
    """
    clean_value  = _strip_punct(value)
    lower_text   = text.lower()
    lower_value  = clean_value.lower()

    if not lower_value:
        return None

    matches = [m.start() for m in re.finditer(re.escape(lower_value), lower_text)]
    if len(matches) != 1:
        return None

    start = matches[0]
    return start, start + len(clean_value)


def _build_example(template: str, entity_labels: list,
                   cyclers: dict, intent: str):
    """
    Fill one template, resolve positions, return a dataset example dict.
    Returns None if any entity span cannot be located unambiguously.
    """
    # Pick one value per unique label
    slot_values: dict = {}
    for label in entity_labels:
        if label not in cyclers:
            raise KeyError(
                f"No value array for entity '{label}'. "
                f"Add it to the entity_values dict."
            )
        if label not in slot_values:
            slot_values[label] = cyclers[label].next()

    # Fill template
    text = template
    for label, value in slot_values.items():
        text = text.replace("{" + label + "}", value, 1)

    # Resolve character spans
    entities    = []
    seen_labels = []
    for label in entity_labels:
        if label in seen_labels:
            continue
        seen_labels.append(label)

        value = slot_values[label]
        span  = _find_span(text, value)
        if span is None:
            return None   # flag

        entities.append({
            "value" : value,
            "entity": label,
            "start" : span[0],
            "end"   : span[1],
        })

    entities.sort(key=lambda e: e["start"])
    # `_template` is carried so callers can build a template-disjoint split.
    # It is metadata only and must be stripped before writing a dataset.
    return {"text": text, "intent": intent, "entities": entities, "_template": template}


# ──────────────────────────────────────────────────────────────────────────────
# Noise injection
# ──────────────────────────────────────────────────────────────────────────────

def inject_noise(text: str, entities: list, rate: float = 0.05,
                 rng: random.Random = None) -> tuple:
    """
    Randomly corrupt characters in NON-ENTITY tokens to simulate student typos.
    Entity spans are never touched. Returns (noisy_text, updated_entities).

    Operations (chosen randomly per eligible character):
      - drop character
      - swap character with its right neighbour
      - duplicate character

    rate: probability each non-entity character is mutated (default 5%).
    """
    if rate <= 0 or not text:
        return text, entities

    if rng is None:
        rng = random.Random()

    # Build a boolean mask: True = inside an entity span (protected)
    protected = [False] * len(text)
    for ent in entities:
        for i in range(ent["start"], ent["end"]):
            protected[i] = True

    chars   = list(text)
    offset  = 0   # tracks cumulative shift from insertions/deletions

    # We operate on original indices; collect mutations first
    mutations = []   # (original_index, operation)
    for i, ch in enumerate(text):
        if not protected[i] and ch != " " and rng.random() < rate:
            op = rng.choice(["drop", "swap", "dup"])
            # don't swap the last char (no right neighbour)
            if op == "swap" and i >= len(text) - 1:
                op = "drop"
            mutations.append((i, op))

    # Apply mutations right-to-left so indices stay valid
    for orig_idx, op in reversed(mutations):
        adj = orig_idx + offset
        if op == "drop":
            chars.pop(adj)
            offset -= 1
            # shift entity spans that start after this point
            for ent in entities:
                if ent["start"] > orig_idx:
                    ent["start"] -= 1
                    ent["end"]   -= 1
        elif op == "swap" and adj + 1 < len(chars):
            chars[adj], chars[adj + 1] = chars[adj + 1], chars[adj]
            # spans unchanged (swap doesn't change length)
        elif op == "dup":
            chars.insert(adj, chars[adj])
            offset += 1
            for ent in entities:
                if ent["start"] > orig_idx:
                    ent["start"] += 1
                    ent["end"]   += 1

    return "".join(chars), entities


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def generate(
    templates:      list,
    entity_values:  dict,
    intent:         str,
    count:          int,
    shuffle:        bool  = True,
    ner_only:       bool  = True,
    noise_rate:     float = 0.0,
    seed:           int   = None,
) -> tuple:
    """
    Generate `count` NER training examples.

    Parameters
    ----------
    templates : list of (template_str, [entity_labels])
    entity_values : dict {label: [value, ...]}
    intent : str   — written into every example
    count : int    — number of examples to generate
    shuffle : bool — shuffle each cycler pass (True breaks positional bias)
    ner_only : bool — skip templates with empty entity list (True for NER)
    noise_rate : float — per-char mutation rate in non-entity tokens (0 = off)
    seed : int | None — RNG seed for reproducibility

    Returns
    -------
    clean   : list of valid examples
    flagged : list of examples where a span could not be resolved
    """
    if not templates:
        raise ValueError("`templates` must not be empty.")
    if count <= 0:
        raise ValueError("`count` must be a positive integer.")

    rng = random.Random(seed)

    # Filter out zero-entity templates when generating NER data
    active_templates = [t for t in templates if t[1]] if ner_only else templates
    if not active_templates:
        raise ValueError(
            "No templates with entities found. "
            "Set ner_only=False if you intended to include zero-entity templates."
        )

    cyclers = {
        label: _Cycler(values, shuffle=shuffle, seed=rng.randint(0, 2**31))
        for label, values in entity_values.items()
    }
    template_cycler = _Cycler(active_templates, shuffle=shuffle,
                               seed=rng.randint(0, 2**31))

    clean            = []
    flagged          = []
    flag_by_template = defaultdict(int)   # template_str → flag count

    for _ in range(count):
        template_str, entity_labels = template_cycler.next()
        example = _build_example(template_str, entity_labels, cyclers, intent)

        if example is None:
            flag_by_template[template_str] += 1
            # Re-build without positions so caller can inspect
            slot_values = {}
            for lbl in entity_labels:
                if lbl not in slot_values:
                    # peek last returned value without advancing
                    c = cyclers[lbl]
                    slot_values[lbl] = c._original[
                        (len(c._original) - len(c._queue) - 1) % len(c._original)
                    ]
            text = template_str
            for lbl, val in slot_values.items():
                text = text.replace("{" + lbl + "}", val, 1)
            flagged.append({
                "text"        : text,
                "intent"      : intent,
                "entities"    : [{"value": slot_values.get(lbl, ""), "entity": lbl}
                                  for lbl in entity_labels],
                "_template"   : template_str,
                "_flag_reason": "value not found or ambiguous in text",
            })
        else:
            if noise_rate > 0:
                noisy_text, noisy_ents = inject_noise(
                    example["text"],
                    [dict(e) for e in example["entities"]],
                    rate=noise_rate,
                    rng=rng,
                )
                example["text"]     = noisy_text
                example["entities"] = noisy_ents
            clean.append(example)

    # Shuffle final output so intent ordering isn't positional
    rng.shuffle(clean)

    # Print flag rate by template (helps identify broken patterns)
    _report_flag_rate(flag_by_template, count)

    return clean, flagged


def template_disjoint_split(
    examples:   list,
    test_ratio: float = 0.10,
    seed:       int   = 7,
    strip_meta: bool  = True,
) -> tuple:
    """
    Split so that no template appears in BOTH train and test.

    Why this exists
    ---------------
    The generators previously did `rng.shuffle(all)` then sliced 90/10. Because
    one template produces many rows (same sentence, different slot fills), that
    puts the *same pattern* on both sides of the split. The model memorises the
    pattern in training and is then "tested" on it, which is why reported F1 sat
    at ~100% while real, unseen phrasings failed. Measured before this change:
    81% (CLF1) / 91% (CLF2) of test rows shared a structure seen in train.

    Holding out whole templates means the test set contains only phrasings the
    model has never seen — which is the thing we actually care about. Expect the
    reported score to drop a lot. That drop is the point: it is the first number
    that responds to real changes.

    Stratified per intent, so every intent keeps test coverage even when its
    template pool is small (e.g. behavioral has 26).

    Returns (train, test) with `_template` removed unless strip_meta=False.
    """
    rng = random.Random(seed)

    by_intent = defaultdict(lambda: defaultdict(list))
    for ex in examples:
        by_intent[ex.get("intent", "")][ex.get("_template", ex["text"])].append(ex)

    train, test = [], []
    print("\n[split] template-disjoint (no template in both sides)")
    for intent in sorted(by_intent):
        groups = list(by_intent[intent].items())
        rng.shuffle(groups)

        total = sum(len(rows) for _, rows in groups)
        target = total * test_ratio

        test_rows, train_rows, held = [], [], 0
        for tpl, rows in groups:
            # Keep at least one template in train, and stop once the test
            # target is met, so a class is never emptied into the test side.
            if len(test_rows) < target and held < len(groups) - 1:
                test_rows.extend(rows)
                held += 1
            else:
                train_rows.extend(rows)

        train.extend(train_rows)
        test.extend(test_rows)
        print(
            f"  {intent:20s} templates={len(groups):4d} "
            f"(train={len(groups)-held:4d} test={held:3d})  "
            f"rows train={len(train_rows):5d} test={len(test_rows):5d}"
        )

    rng.shuffle(train)
    rng.shuffle(test)

    if strip_meta:
        train = [{k: v for k, v in ex.items() if k != "_template"} for ex in train]
        test = [{k: v for k, v in ex.items() if k != "_template"} for ex in test]

    return train, test


def _report_flag_rate(flag_by_template: dict, total: int):
    """Print templates with high flag rates so they can be fixed."""
    if not flag_by_template:
        return
    total_flagged = sum(flag_by_template.values())
    rate = total_flagged / total * 100
    print(f"\n[generator] Flagged: {total_flagged}/{total} ({rate:.1f}%)")
    if total_flagged:
        print("[generator] Top flagging templates:")
        sorted_flags = sorted(flag_by_template.items(),
                               key=lambda x: x[1], reverse=True)
        for tmpl, cnt in sorted_flags[:10]:
            print(f"  {cnt:4d}x  {tmpl!r}")


def save_dataset(
    clean:        list,
    flagged:      list,
    clean_path:   str,
    flagged_path: str  = None,
    append:       bool = True,
):
    """
    Save clean examples to JSON. Optionally save flagged separately.

    append=True  → merges with existing file at clean_path.
    append=False → overwrites.
    """
    os.makedirs(os.path.dirname(os.path.abspath(clean_path)), exist_ok=True)

    existing = []
    if append and os.path.exists(clean_path):
        with open(clean_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        print(f"[save] Loaded {len(existing)} existing examples from '{clean_path}'")

    combined = existing + clean
    with open(clean_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    print(f"[save] Wrote {len(combined)} examples ({len(existing)} old + "
          f"{len(clean)} new) → '{clean_path}'")

    if flagged_path and flagged:
        os.makedirs(os.path.dirname(os.path.abspath(flagged_path)), exist_ok=True)
        with open(flagged_path, "w", encoding="utf-8") as f:
            json.dump(flagged, f, indent=2, ensure_ascii=False)
        print(f"[save] Wrote {len(flagged)} flagged → '{flagged_path}'")
    elif flagged:
        print(f"[save] Warning: {len(flagged)} flagged examples not saved "
              f"(no flagged_path given).")

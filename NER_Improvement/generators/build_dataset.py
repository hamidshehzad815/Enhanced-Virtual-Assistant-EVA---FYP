#!/usr/bin/env python3
"""
Phase 2 — Build base NER datasets from templates + vocab slot fillers.

Reads template JSON from templates/scheduling/ and templates/learning/,
fills slots from config/vocab.json, assigns BIO labels, writes raw datasets.

Usage:
    python build_dataset.py
    python build_dataset.py --samples-per-template 20
    python build_dataset.py --scheduling-only
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from itertools import product
from pathlib import Path
from typing import Any, Dict, Iterator, List, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generators"))

from label_utils import build_example, extract_placeholders  # noqa: E402
from slot_fillers import SLOT_POOLS  # noqa: E402

SCHEDULING_TEMPLATE_DIR = ROOT / "templates" / "scheduling"
LEARNING_TEMPLATE_DIR = ROOT / "templates" / "learning"

SCHEDULING_FILES = [
    "scheduling_add.json",
    "scheduling_delete.json",
    "scheduling_update.json",
    "scheduling_show.json",
    "behavioral.json",
]

LEARNING_FILES = [
    "learning_create.json",
    "learning_update.json",
    "learning_delete.json",
]

DEFAULT_SAMPLES_PER_TEMPLATE = 12
MAX_CARTesian_CAP = 24


def load_template_file(path: Path) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def iter_templates(template_dir: Path, filenames: List[str]) -> Iterator[Tuple[str, Dict[str, Any]]]:
    for name in filenames:
        data = load_template_file(template_dir / name)
        intent = data["intent"]
        for group in data.get("groups", []):
            for tpl in group.get("templates", []):
                yield intent, tpl


def sample_slot_values(
    slots: List[str],
    rng: random.Random,
    cap: int,
) -> List[Dict[str, str]]:
    """Generate up to `cap` unique slot-fill combinations."""
    pools = [SLOT_POOLS.get(s, [s]) for s in slots]
    sizes = [len(p) for p in pools]

    # Small enough → full cartesian product (capped)
    total = 1
    for n in sizes:
        total *= max(n, 1)
        if total > MAX_CARTesian_CAP * 4:
            break

    combos: List[Dict[str, str]] = []

    if total <= MAX_CARTesian_CAP:
        for values in product(*pools):
            combos.append(dict(zip(slots, values)))
    else:
        seen: Set[Tuple[str, ...]] = set()
        attempts = 0
        while len(combos) < cap and attempts < cap * 30:
            attempts += 1
            values = tuple(rng.choice(pool) for pool in pools)
            if values in seen:
                continue
            seen.add(values)
            combos.append(dict(zip(slots, values)))

        # Always include deterministic first values
        if slots:
            first = {s: pools[i][0] for i, s in enumerate(slots)}
            key = tuple(first[s] for s in slots)
            if key not in seen:
                combos.insert(0, first)

    return combos[:cap]


def generate_for_templates(
    template_dir: Path,
    filenames: List[str],
    samples_per_template: int,
    seed: int,
) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    examples: List[Dict[str, Any]] = []
    seen_text: Set[str] = set()
    skipped = 0

    for intent, tpl in iter_templates(template_dir, filenames):
        text = tpl["text"]
        entities: List[str] = tpl.get("entities", [])
        placeholders = extract_placeholders(text)

        if set(placeholders) != set(entities):
            skipped += 1
            continue

        if not entities:
            if text not in seen_text:
                seen_text.add(text)
                examples.append(
                    {
                        "text": text,
                        "intent": intent,
                        "tokens": text.split(),
                        "labels": ["O"] * len(text.split()),
                    }
                )
            continue

        combos = sample_slot_values(entities, rng, samples_per_template)

        for slot_values in combos:
            try:
                ex = build_example(text, entities, slot_values)
            except (KeyError, ValueError):
                skipped += 1
                continue

            if ex["text"] in seen_text:
                continue
            seen_text.add(ex["text"])
            ex["intent"] = intent
            examples.append(ex)

    if skipped:
        print(f"  Warning: skipped {skipped} template fills due to mismatch/errors")

    return examples


def write_dataset(examples: List[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(examples, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def summarize(examples: List[Dict[str, Any]], name: str) -> None:
    intents: Dict[str, int] = {}
    for ex in examples:
        intents[ex["intent"]] = intents.get(ex["intent"], 0) + 1
    print(f"\n{name}: {len(examples)} examples")
    for intent, count in sorted(intents.items()):
        print(f"  {intent}: {count}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build NER datasets from templates")
    parser.add_argument(
        "--samples-per-template",
        type=int,
        default=DEFAULT_SAMPLES_PER_TEMPLATE,
        help=f"Max slot-fill variants per template (default {DEFAULT_SAMPLES_PER_TEMPLATE})",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--scheduling-only", action="store_true")
    parser.add_argument("--learning-only", action="store_true")
    args = parser.parse_args()

    print("Building NER datasets from templates...")
    print(f"  samples_per_template={args.samples_per_template}, seed={args.seed}")

    if not args.learning_only:
        scheduling = generate_for_templates(
            SCHEDULING_TEMPLATE_DIR,
            SCHEDULING_FILES,
            args.samples_per_template,
            args.seed,
        )
        out = ROOT / "datasets" / "scheduling" / "raw" / "scheduling_ner.json"
        write_dataset(scheduling, out)
        summarize(scheduling, "Scheduling NER")
        print(f"  -> {out}")

    if not args.scheduling_only:
        learning = generate_for_templates(
            LEARNING_TEMPLATE_DIR,
            LEARNING_FILES,
            args.samples_per_template,
            args.seed + 1,
        )
        out = ROOT / "datasets" / "learning" / "raw" / "learning_ner.json"
        write_dataset(learning, out)
        summarize(learning, "Learning NER")
        print(f"  -> {out}")

    print("\nDone. Run: python validate_dataset.py")


if __name__ == "__main__":
    main()

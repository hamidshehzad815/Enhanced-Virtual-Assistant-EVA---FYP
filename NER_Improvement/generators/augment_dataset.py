#!/usr/bin/env python3
"""
Phase 4 — Augment raw NER datasets and merge into final training sets.

Reads datasets/*/raw/*.json, applies noise augmentations, adds hard negatives,
writes:
  datasets/{scheduling,learning}/augmented/*_augmented.json
  datasets/{scheduling,learning}/final/*_ner.json  (raw + augmented + hard negatives)

Usage:
    cd NER_Improvement/generators
    python3 augment_dataset.py
    python3 augment_dataset.py --learning-only --variants 2
    python3 validate_dataset.py --path ../datasets/learning/final/learning_ner.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generators"))

from augment_utils import (  # noqa: E402
    augment_dataset,
    load_hard_negatives,
    merge_datasets,
)

CONFIG_PATH = ROOT / "config" / "augmentation.json"
HARD_NEGATIVES_PATH = ROOT / "generators" / "hard_negatives.json"

DATASETS = {
    "scheduling": {
        "raw": ROOT / "datasets" / "scheduling" / "raw" / "scheduling_ner.json",
        "augmented": ROOT / "datasets" / "scheduling" / "augmented" / "scheduling_ner_augmented.json",
        "final": ROOT / "datasets" / "scheduling" / "final" / "scheduling_ner.json",
        "hard_neg_key": "scheduling",
    },
    "learning": {
        "raw": ROOT / "datasets" / "learning" / "raw" / "learning_ner.json",
        "augmented": ROOT / "datasets" / "learning" / "augmented" / "learning_ner_augmented.json",
        "final": ROOT / "datasets" / "learning" / "final" / "learning_ner.json",
        "hard_neg_key": "learning",
    },
}


def load_json(path: Path) -> List[Dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, data: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def process_split(name: str, meta: Dict[str, Path], cfg: Dict[str, Any], variants: int) -> None:
    raw_path = meta["raw"]
    if not raw_path.exists():
        print(f"SKIP {name}: raw not found at {raw_path}")
        return

    raw = load_json(raw_path)
    seed = int(cfg.get("seed", 42)) + (1 if name == "learning" else 0)

    augmented = augment_dataset(
        raw,
        cfg,
        variants_per_example=variants,
        seed=seed,
    )

    hard_neg = load_hard_negatives(str(HARD_NEGATIVES_PATH), meta["hard_neg_key"])
    final = merge_datasets(raw, augmented, hard_neg)

    write_json(meta["augmented"], augmented)
    write_json(meta["final"], final)

    print(f"\n{name}:")
    print(f"  raw:        {len(raw):>6}  {raw_path.name}")
    print(f"  augmented:  {len(augmented):>6}  -> {meta['augmented'].relative_to(ROOT)}")
    print(f"  hard_neg:   {len(hard_neg):>6}")
    print(f"  final:      {len(final):>6}  -> {meta['final'].relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Augment NER datasets (Phase 4)")
    parser.add_argument(
        "--variants",
        type=int,
        default=None,
        help="Augmented variants per raw example (default from config)",
    )
    parser.add_argument("--scheduling-only", action="store_true")
    parser.add_argument("--learning-only", action="store_true")
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    args = parser.parse_args()

    with args.config.open(encoding="utf-8") as fh:
        cfg = json.load(fh)

    variants = args.variants if args.variants is not None else int(cfg.get("variants_per_example", 1))

    print("Phase 4 — augmenting NER datasets")
    print(f"  config:   {args.config.relative_to(ROOT)}")
    print(f"  variants: {variants} per example")

    splits = list(DATASETS.items())
    if args.scheduling_only:
        splits = [(k, v) for k, v in splits if k == "scheduling"]
    if args.learning_only:
        splits = [(k, v) for k, v in splits if k == "learning"]

    for name, meta in splits:
        process_split(name, meta, cfg, variants)

    print("\nDone. Validate with:")
    print("  python3 validate_dataset.py --path ../datasets/scheduling/final/scheduling_ner.json")
    print("  python3 validate_dataset.py --path ../datasets/learning/final/learning_ner.json")


if __name__ == "__main__":
    main()

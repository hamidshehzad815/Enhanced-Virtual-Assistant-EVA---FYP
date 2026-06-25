#!/usr/bin/env python3
"""
Phase 5 — Balance NER final datasets: hard negatives, targeted examples, oversampling.

Reads Phase 4 output (datasets/*/final/), adds targeted + hard-negative examples,
oversamples rare entity types, writes updated final + balance report.

Run after augment_dataset.py:

    cd NER_Improvement/generators
    python3 augment_dataset.py
    python3 balance_dataset.py
    python3 validate_dataset.py --path ../datasets/scheduling/final/scheduling_ner.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generators"))

from augment_utils import load_hard_negatives  # noqa: E402
from balance_utils import (  # noqa: E402
    count_examples_per_entity,
    is_zero_entity_example,
    merge_unique_examples,
    oversample_entities,
    oversample_zero_entity,
)

CONFIG_PATH = ROOT / "config" / "balance.json"
HARD_NEGATIVES_PATH = ROOT / "generators" / "hard_negatives.json"
TARGETED_PATH = ROOT / "generators" / "targeted_examples.json"

DATASETS = {
    "scheduling": {
        "input": ROOT / "datasets" / "scheduling" / "final" / "scheduling_ner.json",
        "output": ROOT / "datasets" / "scheduling" / "final" / "scheduling_ner.json",
        "hard_neg_key": "scheduling",
        "targeted_key": "scheduling",
        "priority_key": "scheduling_priority_entities",
    },
    "learning": {
        "input": ROOT / "datasets" / "learning" / "final" / "learning_ner.json",
        "output": ROOT / "datasets" / "learning" / "final" / "learning_ner.json",
        "hard_neg_key": "learning",
        "targeted_key": "learning",
        "priority_key": "learning_priority_entities",
    },
}


def load_json_list(path: Path) -> List[Dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def load_targeted(path: Path, key: str) -> List[Dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    items = data.get(key, [])
    for item in items:
        item["targeted"] = True
    return items


def write_json(path: Path, data: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def process_split(name: str, meta: Dict[str, Any], cfg: Dict[str, Any], seed: int) -> Dict[str, Any]:
    input_path = meta["input"]
    if not input_path.exists():
        print(f"SKIP {name}: input not found at {input_path}")
        return {}

    base = load_json_list(input_path)
    hard_neg = load_hard_negatives(str(HARD_NEGATIVES_PATH), meta["hard_neg_key"])
    targeted = load_targeted(TARGETED_PATH, meta["targeted_key"])

    merged = merge_unique_examples([base, hard_neg, targeted])
    before_counts = count_examples_per_entity(merged)

    balanced, plan = oversample_entities(
        merged,
        cfg.get(meta["priority_key"], []),
        target_pct=float(cfg.get("target_example_pct", 0.12)),
        max_oversample=int(cfg.get("max_oversample_per_entity", 600)),
        seed=seed,
    )

    zero_pct = float(cfg.get("zero_entity_target_pct", 0.12))
    balanced, zero_plan = oversample_zero_entity(
        balanced,
        target_pct=zero_pct,
        max_oversample=int(cfg.get("max_zero_entity_oversample", 2500)),
        seed=seed + 17,
    )

    after_counts = count_examples_per_entity(balanced)
    zero_count = sum(1 for ex in balanced if is_zero_entity_example(ex))
    write_json(meta["output"], balanced)

    report = {
        "dataset": name,
        "input_examples": len(base),
        "hard_negatives_added": len(hard_neg),
        "targeted_added": len(targeted),
        "after_merge": len(merged),
        "final_examples": len(balanced),
        "oversample_plan": plan,
        "zero_entity_plan": zero_plan,
        "zero_entity_count": zero_count,
        "zero_entity_pct": round(zero_count / max(len(balanced), 1), 4),
        "entity_counts_before": dict(before_counts),
        "entity_counts_after": dict(after_counts),
    }

    print(f"\n{name}:")
    print(f"  input:     {len(base):>6}")
    print(f"  +hard_neg: {len(hard_neg):>6}")
    print(f"  +targeted: {len(targeted):>6}")
    print(f"  merged:    {len(merged):>6}")
    print(f"  final:     {len(balanced):>6}  (+{len(balanced) - len(merged)} oversampled)")
    if plan:
        print("  oversampled entities:")
        for et, info in sorted(plan.items()):
            print(f"    {et}: {info.get('current')} -> +{info.get('added', 0)} (target {info.get('target')})")
    if zero_plan.get("added"):
        print(f"  zero-entity: {zero_plan.get('current')} -> +{zero_plan.get('added')} ({zero_count}/{len(balanced)} = {100*zero_count/len(balanced):.1f}%)")

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 5 balance NER datasets")
    parser.add_argument("--scheduling-only", action="store_true")
    parser.add_argument("--learning-only", action="store_true")
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    args = parser.parse_args()

    with args.config.open(encoding="utf-8") as fh:
        cfg = json.load(fh)

    print("Phase 5 — balancing NER datasets")
    print(f"  config: {args.config.relative_to(ROOT)}")

    splits = list(DATASETS.items())
    if args.scheduling_only:
        splits = [(k, v) for k, v in splits if k == "scheduling"]
    if args.learning_only:
        splits = [(k, v) for k, v in splits if k == "learning"]

    reports = []
    for i, (name, meta) in enumerate(splits):
        reports.append(process_split(name, meta, cfg, seed=42 + i))

    report_path = ROOT / "evaluation" / "balance_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as fh:
        json.dump({"datasets": [r for r in reports if r]}, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print(f"\nReport: {report_path.relative_to(ROOT)}")
    print("Validate with:")
    print("  python3 validate_dataset.py --path ../datasets/scheduling/final/scheduling_ner.json")
    print("  python3 validate_dataset.py --path ../datasets/learning/final/learning_ner.json")


if __name__ == "__main__":
    main()

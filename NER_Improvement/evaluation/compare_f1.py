#!/usr/bin/env python3
"""
Compare entity F1 reports (baseline vs after retrain).

Usage:
    python3 compare_f1.py \\
        ../evaluation/baseline_f1_learning.json \\
        ../evaluation/augmented_f1_learning.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def parse_report(path: Path) -> dict[str, float]:
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    text = data.get("classification_report", "")
    scores: dict[str, float] = {}
    for line in text.splitlines():
        m = re.match(r"^\s{2,}(\S+)\s+[\d.]+\s+[\d.]+\s+([\d.]+)", line)
        if m and m.group(1) not in ("micro", "macro", "weighted", "avg"):
            scores[m.group(1)] = float(m.group(2))
    scores["_overall"] = float(data.get("overall_f1", 0))
    return scores


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two F1 JSON reports")
    parser.add_argument("baseline", type=Path)
    parser.add_argument("current", type=Path)
    args = parser.parse_args()

    base = parse_report(args.baseline)
    cur = parse_report(args.current)

    print(f"{'entity':<20} {'baseline':>10} {'current':>10} {'delta':>10}")
    print("-" * 52)
    entities = sorted(set(base) | set(cur))
    for et in entities:
        b = base.get(et, 0.0)
        c = cur.get(et, 0.0)
        print(f"{et:<20} {b:>10.4f} {c:>10.4f} {c - b:>+10.4f}")


if __name__ == "__main__":
    main()

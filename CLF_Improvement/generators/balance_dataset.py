"""
Balance classifier datasets by downsampling to the smallest class size.

Input:
  datasets/clf1/final/clf1.jsonl
  datasets/clf2/final/clf2.jsonl

Output (overwrites in-place by default):
  datasets/*/final/*.jsonl
"""

from __future__ import annotations

import json
import os
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, DefaultDict, Dict, List


ROOT = Path(__file__).resolve().parents[1]


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _balance(path: Path) -> Dict[str, int]:
    rows = _read_jsonl(path)
    buckets: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        buckets[str(r.get("label") or "")].append(r)

    counts = {k: len(v) for k, v in buckets.items() if k}
    if not counts:
        return {}
    target = min(counts.values())

    balanced: List[Dict[str, Any]] = []
    seed = int(os.getenv("SEED", "1337"))
    rng = random.Random(seed)
    for label, items in buckets.items():
        if not label:
            continue
        rng.shuffle(items)
        balanced.extend(items[:target])

    _write_jsonl(path, balanced)
    out_counts = {k: target for k in counts.keys()}
    return out_counts


def main() -> None:
    paths = [
        ROOT / "datasets" / "clf1" / "final" / "clf1.jsonl",
        ROOT / "datasets" / "clf2" / "final" / "clf2.jsonl",
    ]
    for p in paths:
        if not p.exists():
            print("[balance_dataset] Missing:", p)
            continue
        counts = _balance(p)
        print("[balance_dataset] Balanced:", p)
        for k in sorted(counts.keys()):
            print(f"  - {k}: {counts[k]}")


if __name__ == "__main__":
    main()


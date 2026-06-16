"""
Validate classifier datasets:
- file exists
- JSONL parse
- non-empty text
- label present
- basic duplicate detection
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception as e:
                raise ValueError(f"{path}: line {i}: invalid JSON: {e}")
    return rows


def _norm_text(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def validate(path: Path) -> Tuple[bool, str]:
    if not path.exists():
        return False, f"missing file: {path}"

    rows = _read_jsonl(path)
    if not rows:
        return False, f"empty dataset: {path}"

    label_counts: Counter[str] = Counter()
    seen: Dict[Tuple[str, str], int] = {}
    dupes = 0

    for idx, r in enumerate(rows):
        text = str(r.get("text") or "").strip()
        label = str(r.get("label") or "").strip()
        if not text:
            return False, f"{path}: row {idx}: empty text"
        if not label:
            return False, f"{path}: row {idx}: missing label"
        label_counts[label] += 1
        key = (_norm_text(text), label)
        if key in seen:
            dupes += 1
        else:
            seen[key] = idx

    msg_lines = [
        f"ok: {path}",
        f"  rows: {len(rows)}",
        f"  labels: {len(label_counts)}",
        f"  dupes(same text+label): {dupes}",
    ]
    for label in sorted(label_counts.keys()):
        msg_lines.append(f"  - {label}: {label_counts[label]}")

    return True, "\n".join(msg_lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", action="append", required=True, help="JSONL dataset path")
    args = ap.parse_args()

    all_ok = True
    for raw in args.path:
        ok, msg = validate(Path(raw))
        print(msg)
        if not ok:
            all_ok = False

    raise SystemExit(0 if all_ok else 1)


if __name__ == "__main__":
    main()


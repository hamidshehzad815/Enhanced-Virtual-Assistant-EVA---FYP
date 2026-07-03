#!/usr/bin/env python3
"""Merge the two intent source files into clf2completeDataset.json.

This script reads:
- LearningNER.json
- !LearningNER.json

It keeps only the `text` and `intent` fields from every item and writes the
merged output to `clf2completeDataset.json` in the same folder.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def load_records(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array in {path}")

    records: List[Dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue

        text = item.get("text")
        intent = item.get("intent")

        if isinstance(text, str) and isinstance(intent, str) and text.strip() and intent.strip():
            records.append({"text": text.strip(), "intent": intent.strip()})

    return records


def main() -> None:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--folder", default=".", help="folder containing LearningNER.json files")
    args, _unknown = parser.parse_known_args()

    folder = Path(args.folder).resolve()
    file1 = folder / "LearningNER.json"
    file2 = folder / "!LearningNER.json"

    print(f"Reading {file1}")
    records1 = load_records(file1)
    print(f"  -> {len(records1)} rows")

    print(f"Reading {file2}")
    records2 = load_records(file2)
    print(f"  -> {len(records2)} rows")

    merged = records1 + records2

    out_path = folder / "clf2completeDataset.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(merged)} rows to {out_path}")


if __name__ == "__main__":
    main()

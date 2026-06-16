#!/usr/bin/env python3
"""
Phase 2 — Validate generated NER datasets (tokens, BIO labels, entity spans).

Usage:
    python validate_dataset.py
    python validate_dataset.py --path ../datasets/scheduling/raw/scheduling_ner.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generators"))

from label_utils import merge_bio_tokens  # noqa: E402

DEFAULT_PATHS = [
    ROOT / "datasets" / "scheduling" / "raw" / "scheduling_ner.json",
    ROOT / "datasets" / "learning" / "raw" / "learning_ner.json",
]

VALID_PREFIXES = ("B-", "I-")


def load_labels_config() -> Tuple[set, set]:
    with (ROOT / "config" / "labels.json").open(encoding="utf-8") as fh:
        cfg = json.load(fh)
    scheduling = set(cfg["scheduling_ner"]["labels"])
    learning = set(cfg["learning_ner"]["labels"])
    return scheduling, learning


def validate_example(
    ex: Dict[str, Any],
    allowed_labels: set,
    index: int,
) -> List[str]:
    errors: List[str] = []
    prefix = f"example[{index}]"

    tokens: List[str] = ex.get("tokens", [])
    labels: List[str] = ex.get("labels", [])
    text: str = ex.get("text", "")

    if not tokens:
        errors.append(f"{prefix}: empty tokens")
        return errors

    if len(tokens) != len(labels):
        errors.append(
            f"{prefix}: token/label length mismatch "
            f"({len(tokens)} tokens vs {len(labels)} labels) text={text!r}"
        )
        return errors

    for i, label in enumerate(labels):
        if label not in allowed_labels:
            errors.append(f"{prefix}: invalid label {label!r} at token {i}")
        if label != "O" and not label.startswith(VALID_PREFIXES):
            errors.append(f"{prefix}: malformed label {label!r} at token {i}")

    # BIO sequence rules
    prev_type = ""
    for i, label in enumerate(labels):
        if label == "O":
            prev_type = ""
            continue
        prefix_tag, etype = label.split("-", 1)
        if prefix_tag == "I" and prev_type and etype != prev_type:
            errors.append(
                f"{prefix}: invalid I-{etype} after different entity at token {i} text={text!r}"
            )
        if prefix_tag == "I" and not prev_type:
            errors.append(
                f"{prefix}: I-{etype} without preceding B- at token {i} text={text!r}"
            )
        prev_type = etype if prefix_tag in ("B", "I") else ""

    # Reconstructed text from tokens should match (whitespace-normalized)
    if " ".join(tokens) != " ".join(text.split()):
        errors.append(f"{prefix}: tokens do not reconstruct text: tokens={tokens!r} text={text!r}")

    # Entity values must appear in text
    merged = merge_bio_tokens(tokens, labels)
    for etype, values in merged.items():
        for val in values:
            if val.lower() not in text.lower():
                errors.append(
                    f"{prefix}: entity {etype}={val!r} not found in text={text!r}"
                )

    return errors


def validate_file(path: Path, allowed_labels: set) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)

    all_errors: List[str] = []
    intent_counts = Counter(ex.get("intent", "?") for ex in data)
    label_counts = Counter()

    for i, ex in enumerate(data):
        for lbl in ex.get("labels", []):
            label_counts[lbl] += 1
        all_errors.extend(validate_example(ex, allowed_labels, i))

    return {
        "path": str(path),
        "examples": len(data),
        "intents": dict(intent_counts),
        "label_distribution": dict(label_counts.most_common(20)),
        "errors": all_errors,
        "valid": len(all_errors) == 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate NER datasets")
    parser.add_argument("--path", type=Path, action="append", help="Dataset JSON path (repeatable)")
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "evaluation" / "validation_report.json",
    )
    args = parser.parse_args()

    scheduling_labels, learning_labels = load_labels_config()
    paths = args.path or DEFAULT_PATHS

    reports = []
    total_errors = 0

    for path in paths:
        if not path.exists():
            print(f"SKIP (not found): {path}")
            continue

        allowed = scheduling_labels if "scheduling" in path.name else learning_labels
        report = validate_file(path, allowed)
        reports.append(report)
        total_errors += len(report["errors"])

        status = "PASS" if report["valid"] else "FAIL"
        print(f"\n{status}: {path.name}")
        print(f"  examples: {report['examples']}")
        print(f"  intents: {report['intents']}")
        if report["errors"]:
            print(f"  errors: {len(report['errors'])}")
            for err in report["errors"][:15]:
                print(f"    - {err}")
            if len(report["errors"]) > 15:
                print(f"    ... and {len(report['errors']) - 15} more")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "total_errors": total_errors,
                "all_valid": total_errors == 0,
                "datasets": reports,
            },
            fh,
            indent=2,
            ensure_ascii=False,
        )
        fh.write("\n")

    print(f"\nReport written to {args.report}")
    if total_errors:
        sys.exit(1)


if __name__ == "__main__":
    main()

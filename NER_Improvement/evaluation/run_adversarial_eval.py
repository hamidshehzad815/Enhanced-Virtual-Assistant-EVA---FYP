#!/usr/bin/env python3
"""
Phase 8 — Run adversarial NER evaluation against deployed EVA models.

Uses Eva_AI_Server pipeline (spell correction, fallbacks, postprocess).

Usage:
    cd NER_Improvement/evaluation
    python3 run_adversarial_eval.py

    # custom paths
    python3 run_adversarial_eval.py --tests adversarial/adversarial_tests.json

Outputs:
    evaluation/adversarial_report.json
    evaluation/errors/adversarial_failures.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVA_SERVER = ROOT.parent / "Eva_AI_Server"
EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL_DIR))
sys.path.insert(0, str(EVA_SERVER))

from adversarial_eval import (  # noqa: E402
    evaluate_case,
    group_failures_for_feedback,
    load_adversarial_cases,
    summarize_results,
)
from pipeline.ner import get_ner_extractor_for_intent  # noqa: E402

DEFAULT_TESTS = Path(__file__).resolve().parent / "adversarial" / "adversarial_tests.json"
DEFAULT_REPORT = Path(__file__).resolve().parent / "adversarial_report.json"
DEFAULT_FAILURES = Path(__file__).resolve().parent / "errors" / "adversarial_failures.json"


def run_eval(cases: list, verbose: bool = True) -> list:
    results = []
    loaded_groups: dict = {}

    for case in cases:
        intent = case.get("intent", "")
        group = case.get("model_group", "")
        extractor = get_ner_extractor_for_intent(intent)
        if group not in loaded_groups:
            if not extractor.loaded and not extractor.load():
                raise RuntimeError(f"Failed to load NER model for group={group}")
            loaded_groups[group] = str(extractor.loaded_from)

        actual = extractor.extract(case["text"], intent_hint=intent)
        result = evaluate_case(case, actual)
        result["model_dir"] = loaded_groups.get(group, "")
        results.append(result)

        if verbose:
            status = "PASS" if result["passed"] else "FAIL"
            print(f"[{status}] {result.get('id') or result['text'][:50]}")
            if not result["passed"]:
                for err in result.get("errors") or []:
                    print(f"       - {err}")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Adversarial NER evaluation (Phase 8)")
    parser.add_argument("--tests", type=Path, default=DEFAULT_TESTS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--failures", type=Path, default=DEFAULT_FAILURES)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if not args.tests.exists():
        raise SystemExit(f"Tests not found: {args.tests}")

    cases = load_adversarial_cases(args.tests)
    print(f"Running {len(cases)} adversarial cases...")
    results = run_eval(cases, verbose=not args.quiet)

    summary = summarize_results(results)
    failures = [r for r in results if not r["passed"]]
    feedback = group_failures_for_feedback(results)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tests_file": str(args.tests),
        "summary": summary,
        "results": results,
    }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    args.failures.parent.mkdir(parents=True, exist_ok=True)
    with args.failures.open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "generated_at": report["generated_at"],
                "failure_count": len(failures),
                "failures": failures,
                "feedback_by_tag": feedback,
            },
            fh,
            indent=2,
            ensure_ascii=False,
        )
        fh.write("\n")

    print("\nSummary:")
    print(f"  passed: {summary['passed']}/{summary['total']} ({summary['pass_rate']:.0%})")
    if summary.get("failures_by_tag"):
        print("  failure tags:", summary["failures_by_tag"])
    print(f"  report:   {args.report}")
    print(f"  failures: {args.failures}")

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

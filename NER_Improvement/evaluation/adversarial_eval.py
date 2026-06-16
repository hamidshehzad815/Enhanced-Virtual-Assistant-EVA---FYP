"""
Phase 8 — Adversarial NER evaluation helpers (no model loading).
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Mirror pipeline spell corrections for expected-value comparison.
_TYPO_NORMALIZE = {
    "beginer": "beginner",
    "beginers": "beginners",
    "begginer": "beginner",
    "physcis": "physics",
    "munday": "monday",
    "tuseday": "tuesday",
    "pyton": "python",
}


def _norm_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = " ".join(text.split())
    tokens = [_TYPO_NORMALIZE.get(t, t) for t in text.split()]
    return " ".join(tokens)


def flatten_entity_values(entities: Dict[str, Any]) -> Dict[str, str]:
    flat: Dict[str, str] = {}
    for key, value in (entities or {}).items():
        if value is None or value == "" or value == []:
            continue
        if isinstance(value, list):
            flat[key] = " ".join(str(v) for v in value if v)
        else:
            flat[key] = str(value)
    return flat


def all_extracted_tokens(entities: Dict[str, Any]) -> List[str]:
    tokens: List[str] = []
    for value in flatten_entity_values(entities).values():
        tokens.extend(value.split())
    return tokens


def forbidden_present(entities: Dict[str, Any], forbidden: List[str]) -> List[str]:
    if not forbidden:
        return []
    found: List[str] = []
    flat = flatten_entity_values(entities)
    for ban in forbidden:
        b = ban.lower()
        for val in flat.values():
            val_norm = _norm_text(val)
            if val_norm == b or re.search(rf"(?<![a-z0-9]){re.escape(b)}(?![a-z0-9])", val_norm):
                found.append(ban)
                break
    return found


def compare_entities(
    expected: Dict[str, str],
    actual: Dict[str, Any],
) -> Tuple[bool, List[str]]:
    """Return (passed, mismatch_messages)."""
    errors: List[str] = []
    actual_flat = flatten_entity_values(actual)

    for key, exp_val in (expected or {}).items():
        exp_norm = _norm_text(exp_val)
        act_val = actual_flat.get(key)
        if act_val is None:
            errors.append(f"missing {key}: expected {exp_val!r}")
            continue
        act_norm = _norm_text(act_val)
        if exp_norm != act_norm and exp_norm not in act_norm and act_norm not in exp_norm:
            errors.append(f"{key}: expected {exp_val!r}, got {act_val!r}")

    return (len(errors) == 0, errors)


def evaluate_case(case: Dict[str, Any], actual_entities: Dict[str, Any]) -> Dict[str, Any]:
    expected = case.get("expected") or {}
    must_not = list(case.get("must_not_extract") or [])

    entity_ok, entity_errors = compare_entities(expected, actual_entities)
    banned = forbidden_present(actual_entities, must_not)

    passed = entity_ok and not banned
    result = {
        "id": case.get("id", ""),
        "text": case.get("text", ""),
        "intent": case.get("intent", ""),
        "tags": case.get("tags", []),
        "passed": passed,
        "expected": expected,
        "actual": flatten_entity_values(actual_entities),
        "errors": entity_errors[:],
    }
    if banned:
        result["errors"].append(f"forbidden values extracted: {banned}")
    return result


def load_adversarial_cases(path: Path) -> List[Dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    cases: List[Dict[str, Any]] = []
    for group in ("scheduling", "learning"):
        for case in data.get(group, []):
            item = dict(case)
            item["model_group"] = group
            cases.append(item)
    return cases


def summarize_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    by_intent: Counter = Counter()
    fail_by_intent: Counter = Counter()
    fail_by_tag: Counter = Counter()
    weak_entities: Counter = Counter()

    for r in results:
        intent = r.get("intent", "?")
        by_intent[intent] += 1
        if r["passed"]:
            continue
        fail_by_intent[intent] += 1
        for tag in r.get("tags") or []:
            fail_by_tag[tag] += 1
        for err in r.get("errors") or []:
            if err.startswith("missing "):
                weak_entities[err.split(":", 1)[0].replace("missing ", "")] += 1
            elif ":" in err:
                weak_entities[err.split(":", 1)[0]] += 1

    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "by_intent_total": dict(by_intent),
        "failures_by_intent": dict(fail_by_intent),
        "failures_by_tag": dict(fail_by_tag.most_common()),
        "weak_entity_signals": dict(weak_entities.most_common()),
    }


def group_failures_for_feedback(results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in results:
        if r["passed"]:
            continue
        for tag in r.get("tags") or ["untagged"]:
            grouped[tag].append(
                {
                    "id": r.get("id"),
                    "text": r.get("text"),
                    "intent": r.get("intent"),
                    "errors": r.get("errors"),
                }
            )
    return dict(grouped)

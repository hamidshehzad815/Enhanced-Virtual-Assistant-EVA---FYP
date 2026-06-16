"""
Phase 5 — Entity balance utilities: count entities, oversample rare types.
"""

from __future__ import annotations

import copy
import random
from collections import Counter, defaultdict
from typing import Any, Dict, List, Sequence, Set, Tuple


def entity_types_in_example(labels: Sequence[str]) -> Set[str]:
    return {lbl[2:] for lbl in labels if lbl.startswith("B-")}


def count_examples_per_entity(examples: List[Dict[str, Any]]) -> Counter:
    counts: Counter = Counter()
    for ex in examples:
        for et in entity_types_in_example(ex.get("labels", [])):
            counts[et] += 1
    return counts


def index_examples_by_entity(examples: List[Dict[str, Any]]) -> Dict[str, List[int]]:
    index: Dict[str, List[int]] = defaultdict(list)
    for i, ex in enumerate(examples):
        for et in entity_types_in_example(ex.get("labels", [])):
            index[et].append(i)
    return index


def compute_balance_plan(
    examples: List[Dict[str, Any]],
    priority_entities: Sequence[str],
    target_pct: float,
    max_oversample: int,
) -> Dict[str, Dict[str, int]]:
    total = len(examples)
    if total == 0:
        return {}

    counts = count_examples_per_entity(examples)
    target = max(1, int(total * target_pct))
    plan: Dict[str, Dict[str, int]] = {}

    for et in priority_entities:
        current = counts.get(et, 0)
        needed = min(max_oversample, max(0, target - current))
        if needed > 0:
            plan[et] = {
                "current": current,
                "target": target,
                "oversample_add": needed,
            }

    return plan


def oversample_entities(
    examples: List[Dict[str, Any]],
    priority_entities: Sequence[str],
    target_pct: float,
    max_oversample: int,
    seed: int = 42,
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, int]]]:
    """Return examples + oversampled copies (exact duplicates allowed for rare entities)."""
    rng = random.Random(seed)
    plan = compute_balance_plan(examples, priority_entities, target_pct, max_oversample)
    index = index_examples_by_entity(examples)
    result = list(examples)
    added_count: Dict[str, int] = {et: 0 for et in plan}

    for et, info in plan.items():
        candidates = index.get(et, [])
        if not candidates:
            continue
        n = info["oversample_add"]
        for _ in range(n):
            src = copy.deepcopy(examples[rng.choice(candidates)])
            src["balanced"] = True
            src["balance_entity"] = et
            result.append(src)
            added_count[et] = added_count.get(et, 0) + 1

    for et in plan:
        plan[et]["added"] = added_count.get(et, 0)

    return result, plan


def merge_unique_examples(
    batches: Sequence[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for batch in batches:
        for ex in batch:
            text = ex.get("text", "")
            if not text or text in seen:
                continue
            seen.add(text)
            merged.append(copy.deepcopy(ex))
    return merged

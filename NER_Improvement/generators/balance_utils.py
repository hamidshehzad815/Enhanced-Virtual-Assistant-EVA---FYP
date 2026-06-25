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


def is_zero_entity_example(ex: Dict[str, Any]) -> bool:
    return all(lbl == "O" for lbl in ex.get("labels", []))


def oversample_zero_entity(
    examples: List[Dict[str, Any]],
    target_pct: float,
    max_oversample: int,
    seed: int = 42,
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Upsample all-O examples so they reach target_pct of the final dataset."""
    rng = random.Random(seed)
    zero_indices = [i for i, ex in enumerate(examples) if is_zero_entity_example(ex)]
    if not zero_indices:
        return examples, {"current": 0, "target": 0, "added": 0}

    current = len(zero_indices)
    total = len(examples)
    # target * (total + added) = current + added  =>  added = (target*total - current) / (1 - target)
    target = float(target_pct)
    needed = int((target * total - current) / max(1 - target, 0.01))
    needed = max(0, min(max_oversample, needed))

    result = list(examples)
    for _ in range(needed):
        src = copy.deepcopy(examples[rng.choice(zero_indices)])
        src["balanced"] = True
        src["balance_zero_entity"] = True
        result.append(src)

    return result, {"current": current, "target_pct": target_pct, "added": needed}


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

"""
Generate CLF2 (Intent Classification) Dataset
===============================================
Produces Updated/Datasets/clf2_train.json  (90%)
         Updated/Datasets/clf2_test.json   (10%)

Fixes vs old dataset:
  - Intent names aligned to server: scheduling_add / scheduling_delete /
    scheduling_update / scheduling_show  (was: add / delete / update / show)
  - Zero-entity (bare starter) templates INCLUDED here — CLF2 benefits from them
  - Uses shuffled cycler — breaks positional memorisation

Targets (plan Phase 5):
  scheduling_add    : 3000
  scheduling_delete : 3000
  scheduling_update : 3200
  scheduling_show   : 3000
  learning_create   : 5500
  learning_delete   : 2500
  learning_update   : 5500
  behavioral        : 2300
  TOTAL             : 28000
"""

import sys, os, json, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Templates'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'SlotArrays'))

from generator_engine import generate
from scheduling_templates import (
    ADD_TEMPLATES, DELETE_TEMPLATES, UPDATE_TEMPLATES,
    SHOW_TEMPLATES, BEHAVIORAL_TEMPLATES,
)
from learning_templates import (
    LEARNING_CREATE_TEMPLATES,
    LEARNING_DELETE_TEMPLATES,
    LEARNING_UPDATE_TEMPLATES,
)
from scheduling_slots import (
    TASK_NAMES, DATES, TIMES, DURATIONS, PRIORITIES,
    STATUSES, COLLABORATORS, DAYS,
)
from learning_slots import (
    TOPICS, SUBTOPICS,
    DURATIONS as LEARN_DURATIONS,
    START_DATES, COLLABORATORS as LEARN_COLLABORATORS,
)

SEED = 13

SCHED_ENTITIES = {
    "task_name"    : TASK_NAMES,
    "date"         : DATES,
    "time"         : TIMES,
    "duration"     : DURATIONS,
    "priority"     : PRIORITIES,
    "status"       : STATUSES,
    "person"       : COLLABORATORS,
    "day"          : DAYS,
    "new_taskname" : TASK_NAMES,
    "new_date"     : DATES,
    "new_time"     : TIMES,
    "new_duration" : DURATIONS,
    "new_priority" : PRIORITIES,
    "new_status"   : STATUSES,
}

LEARN_ENTITIES = {
    "topic"      : TOPICS,
    "subtopic"   : SUBTOPICS,
    "duration"   : LEARN_DURATIONS,
    "start_date" : START_DATES,
    "person"     : LEARN_COLLABORATORS,
    "date"       : START_DATES,
}

def _dedupe(examples):
    """
    Drop duplicate texts, keeping first occurrence.

    generator_engine.generate() is a blind `for _ in range(count)` with no
    dedup, so when a class's template x slot space is smaller than the requested
    count it simply repeats itself (e.g. BEHAVIORAL has 26 templates but is
    asked for 2300 -> each unique string ~22x). Those copies teach nothing,
    inflate confidence, and leak across the shuffle split. The post-dedupe count
    is the class's real coverage.
    """
    seen = {}
    unique = []
    conflicts = {}
    for ex in examples:
        key = " ".join(str(ex["text"]).lower().split())
        if key in seen:
            if seen[key] != ex["intent"]:
                conflicts.setdefault(key, {seen[key]}).add(ex["intent"])
            continue
        seen[key] = ex["intent"]
        unique.append(ex)

    if conflicts:
        print(f"[dedupe] WARNING: {len(conflicts)} text(s) labelled with multiple intents:")
        for text, intents in list(conflicts.items())[:10]:
            print(f"    {text!r}: {sorted(intents)}")
    return unique


def run():
    rng = random.Random(SEED)
    all_examples = []

    specs = [
        (ADD_TEMPLATES,              SCHED_ENTITIES,  "scheduling_add",    3000),
        (DELETE_TEMPLATES,           SCHED_ENTITIES,  "scheduling_delete", 3000),
        (UPDATE_TEMPLATES,           SCHED_ENTITIES,  "scheduling_update", 3200),
        (SHOW_TEMPLATES,             SCHED_ENTITIES,  "scheduling_show",   3000),
        (BEHAVIORAL_TEMPLATES,       SCHED_ENTITIES,  "behavioral",        2300),
        (LEARNING_CREATE_TEMPLATES,  LEARN_ENTITIES,  "learning_create",   5500),
        (LEARNING_DELETE_TEMPLATES,  LEARN_ENTITIES,  "learning_delete",   2500),
        (LEARNING_UPDATE_TEMPLATES,  LEARN_ENTITIES,  "learning_update",   5500),
    ]

    for templates, entities, intent, count in specs:
        print(f"\n[clf2] Generating {count} × {intent} ...")
        clean, flagged = generate(
            templates     = templates,
            entity_values = entities,
            intent        = intent,
            count         = count,
            shuffle       = True,
            ner_only      = False,   # CLF2 includes zero-entity templates
            noise_rate    = 0.0,     # No noise for CLF — clean intent signals
            seed          = rng.randint(0, 2**31),
        )
        # CLF2 only needs text + intent — drop entity spans
        clf2_clean = [{"text": ex["text"], "intent": ex["intent"]} for ex in clean]
        # The engine repeats itself once `count` exceeds the template x slot
        # space, so the requested number is aspirational. Report the real one.
        clf2_unique = _dedupe(clf2_clean)
        print(
            f"  requested={count}  generated={len(clf2_clean)}  "
            f"UNIQUE={len(clf2_unique)}  (templates={len(templates)})  flagged={len(flagged)}"
        )
        all_examples.extend(clf2_unique)

    before = len(all_examples)
    all_examples = _dedupe(all_examples)
    print(f"\n[clf2] cross-intent dedupe: {before} -> {len(all_examples)}")
    rng.shuffle(all_examples)

    split = int(len(all_examples) * 0.9)
    train = all_examples[:split]
    test  = all_examples[split:]

    out_dir = os.path.join(os.path.dirname(__file__), '..', 'Datasets')
    os.makedirs(out_dir, exist_ok=True)

    train_path = os.path.join(out_dir, 'clf2_train.json')
    test_path  = os.path.join(out_dir, 'clf2_test.json')

    with open(train_path, 'w', encoding='utf-8') as f:
        json.dump(train, f, indent=2, ensure_ascii=False)
    with open(test_path, 'w', encoding='utf-8') as f:
        json.dump(test, f, indent=2, ensure_ascii=False)

    print(f"\n[clf2] Done.")
    print(f"  Train : {len(train)} -> {train_path}")
    print(f"  Test  : {len(test)}  -> {test_path}")

    from collections import Counter
    dist = Counter(ex['intent'] for ex in train)
    print("\n[clf2] Class distribution in train split:")
    for intent, cnt in sorted(dist.items()):
        print(f"  {intent:25s}: {cnt}")

if __name__ == '__main__':
    run()

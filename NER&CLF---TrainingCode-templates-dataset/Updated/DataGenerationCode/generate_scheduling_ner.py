"""
Generate Scheduling NER Dataset
================================
Produces Updated/Datasets/scheduling_ner_train.json  (90%)
         Updated/Datasets/scheduling_ner_test.json   (10%)

Targets (plan Phase 5):
  scheduling_add    : 6000
  scheduling_delete : 4000
  scheduling_update : 5000
  scheduling_show   : 2000
  behavioral        : 1000
  TOTAL             : 18000
"""

import sys, os, json, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Templates'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'SlotArrays'))

from generator_engine import generate, template_disjoint_split
from scheduling_templates import (
    ADD_TEMPLATES, DELETE_TEMPLATES, UPDATE_TEMPLATES,
    SHOW_TEMPLATES, BEHAVIORAL_TEMPLATES,
)
from scheduling_slots import (
    TASK_NAMES, DATES, TIMES, DURATIONS, PRIORITIES,
    STATUSES, COLLABORATORS, DAYS,
)

SEED = 42

# Shared entity_values — covers every slot that appears across all template sets.
# new_* labels reuse the same value arrays with different entity names.
SCHEDULING_ENTITIES = {
    "task_name"    : TASK_NAMES,
    "date"         : DATES,
    "time"         : TIMES,
    "duration"     : DURATIONS,
    "priority"     : PRIORITIES,
    "status"       : STATUSES,
    "person"       : COLLABORATORS,
    "day"          : DAYS,
    # UPDATE new-value slots — same pools, separate entity names
    "new_taskname" : TASK_NAMES,
    "new_date"     : DATES,
    "new_time"     : TIMES,
    "new_duration" : DURATIONS,
    "new_priority" : PRIORITIES,
    "new_status"   : STATUSES,
}

def run():
    rng = random.Random(SEED)
    all_examples = []

    specs = [
        (ADD_TEMPLATES,        "scheduling_add",    6000),
        (DELETE_TEMPLATES,     "scheduling_delete", 4000),
        (UPDATE_TEMPLATES,     "scheduling_update", 5000),
        (SHOW_TEMPLATES,       "scheduling_show",   2000),
        (BEHAVIORAL_TEMPLATES, "behavioral",        1000),
    ]

    for templates, intent, count in specs:
        print(f"\n[scheduling_ner] Generating {count} × {intent} ...")
        clean, flagged = generate(
            templates     = templates,
            entity_values = SCHEDULING_ENTITIES,
            intent        = intent,
            count         = count,
            shuffle       = True,
            ner_only      = True,
            noise_rate    = 0.03,
            seed          = rng.randint(0, 2**31),
        )
        print(f"  clean={len(clean)}  flagged={len(flagged)}")
        all_examples.extend(clean)

    # Template-disjoint 90/10 split: no template in both train and test, so the
    # test set only contains phrasings the model has never seen.
    train, test = template_disjoint_split(all_examples, test_ratio=0.10, seed=SEED)

    out_dir = os.path.join(os.path.dirname(__file__), '..', 'Datasets')
    os.makedirs(out_dir, exist_ok=True)

    train_path = os.path.join(out_dir, 'scheduling_ner_train.json')
    test_path  = os.path.join(out_dir, 'scheduling_ner_test.json')

    with open(train_path, 'w', encoding='utf-8') as f:
        json.dump(train, f, indent=2, ensure_ascii=False)
    with open(test_path, 'w', encoding='utf-8') as f:
        json.dump(test, f, indent=2, ensure_ascii=False)

    print(f"\n[scheduling_ner] Done.")
    print(f"  Train : {len(train)} -> {train_path}")
    print(f"  Test  : {len(test)}  -> {test_path}")

    # Entity distribution report
    from collections import Counter
    ent_counter = Counter()
    for ex in train:
        for ent in ex['entities']:
            ent_counter[ent['entity']] += 1
    print("\n[scheduling_ner] Entity counts in train split:")
    for ent, cnt in sorted(ent_counter.items()):
        print(f"  {ent:20s}: {cnt}")

if __name__ == '__main__':
    run()

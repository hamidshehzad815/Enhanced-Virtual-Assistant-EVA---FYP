"""
Generate Learning NER Dataset
==============================
Produces Updated/Datasets/learning_ner_train.json  (90%)
         Updated/Datasets/learning_ner_test.json   (10%)

Targets (plan Phase 5):
  learning_create : 8000
  learning_delete : 4000
  learning_update : 4000
  TOTAL           : 16000

Notes:
  - Zero-entity templates filtered out via ner_only=True
  - 'date' label NOT used here — learning templates use 'start_date' only
  - Uses SUPPORTED_TOPICS + UNSUPPORTED_TOPICS via combined TOPICS array
"""

import sys, os, json, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Templates'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'SlotArrays'))

from generator_engine import generate, template_disjoint_split
from learning_templates import (
    LEARNING_CREATE_TEMPLATES,
    LEARNING_DELETE_TEMPLATES,
    LEARNING_UPDATE_TEMPLATES,
)
from learning_slots import (
    TOPICS, SUBTOPICS, DURATIONS, START_DATES, COLLABORATORS,
)

SEED = 7

LEARNING_ENTITIES = {
    "topic"      : TOPICS,
    "subtopic"   : SUBTOPICS,
    "duration"   : DURATIONS,
    "start_date" : START_DATES,
    "person"     : COLLABORATORS,
    # UPDATE reschedule slot
    "date"       : START_DATES,   # reschedule date reuses same date pool
}

def run():
    rng = random.Random(SEED)
    all_examples = []

    specs = [
        (LEARNING_CREATE_TEMPLATES, "learning_create", 8000),
        (LEARNING_DELETE_TEMPLATES, "learning_delete", 4000),
        (LEARNING_UPDATE_TEMPLATES, "learning_update", 4000),
    ]

    for templates, intent, count in specs:
        print(f"\n[learning_ner] Generating {count} × {intent} ...")
        clean, flagged = generate(
            templates     = templates,
            entity_values = LEARNING_ENTITIES,
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

    train_path = os.path.join(out_dir, 'learning_ner_train.json')
    test_path  = os.path.join(out_dir, 'learning_ner_test.json')

    with open(train_path, 'w', encoding='utf-8') as f:
        json.dump(train, f, indent=2, ensure_ascii=False)
    with open(test_path, 'w', encoding='utf-8') as f:
        json.dump(test, f, indent=2, ensure_ascii=False)

    print(f"\n[learning_ner] Done.")
    print(f"  Train : {len(train)} -> {train_path}")
    print(f"  Test  : {len(test)}  -> {test_path}")

    from collections import Counter
    ent_counter = Counter()
    for ex in train:
        for ent in ex['entities']:
            ent_counter[ent['entity']] += 1
    print("\n[learning_ner] Entity counts in train split:")
    for ent, cnt in sorted(ent_counter.items()):
        print(f"  {ent:20s}: {cnt}")

if __name__ == '__main__':
    run()

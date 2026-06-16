# NER Improvement Workspace

Dedicated workspace for rebuilding and improving EVA's two NER models from scratch.

## Models

| Model | Deploy path | Intents |
|-------|-------------|---------|
| Scheduling NER | `Eva_AI_Server/models/ner_model` | scheduling_*, behavioral |
| Learning NER | `Eva_AI_Server/models/learning_ner` | learning_* |

## Folder structure

```
NER_Improvement/
├── config/                 # Machine-readable reference (labels, entities, vocab)
├── templates/              # Sentence templates per intent
│   ├── scheduling/
│   └── learning/
├── datasets/               # Generated datasets
│   ├── scheduling/         # raw → augmented → final
│   └── learning/
├── generators/             # Scripts to build datasets from templates
├── training/               # Training notebooks/scripts
│   ├── scheduling/
│   └── learning/
└── evaluation/             # Test sets and error analysis
    ├── adversarial/
    └── errors/
```

## Key files

| File | Purpose |
|------|---------|
| `PHASES.md` | Step-by-step roadmap |
| `ENTITIES.md` | Human-readable entity reference |
| `config/labels.json` | BIO labels for both models |
| `config/entities.json` | Entity types, intent scope, aliases |
| `config/vocab.json` | Topics, days, priorities, statuses, sample values |

## Workflow

1. **Phase 1** — Setup (this folder + config) ✅
2. **Phase 2** — Templates + auto-generation → `datasets/*/raw` ✅
3. **Phase 3** — Fix training (BIO alignment, F1 eval) ✅
4. **Phase 4** — Augmentation ✅
5. **Phase 5** — Hard negatives + balance ✅
6. **Phase 6** — Pipeline fixes (`Eva_AI_Server`) ✅
7. **Phase 8** — Adversarial eval ✅
8. **Colab retrain** — when ready, on `datasets/*/final/`

### Regenerate datasets (Phase 2)

```bash
cd NER_Improvement/generators
python3 build_dataset.py --samples-per-template 12
python3 validate_dataset.py
```

### Build final training data (Phase 4 + 5)

```bash
cd NER_Improvement/generators
python3 augment_dataset.py
python3 balance_dataset.py
python3 validate_dataset.py --path ../datasets/scheduling/final/scheduling_ner.json
python3 validate_dataset.py --path ../datasets/learning/final/learning_ner.json
```

Final training files for Colab retrain:
- `datasets/scheduling/final/scheduling_ner.json` (~22k examples)
- `datasets/learning/final/learning_ner.json` (~9.5k examples)

### Evaluate (Phase 8)

```bash
cd NER_Improvement/evaluation
python3 run_adversarial_eval.py
```

See `evaluation/EVAL_GUIDE.md`.

See `PHASES.md` for the full plan.

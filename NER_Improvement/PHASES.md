# NER Improvement — Phased Roadmap

Follow each phase in order. Complete one phase before starting the next.

---

## Phase 1 — Project Setup ✅

- [x] Create folder structure (`templates/`, `datasets/`, `generators/`, `training/`, `evaluation/`)
- [x] Define entity types for **scheduling NER** and **learning NER** → `ENTITIES.md`, `config/entities.json`
- [x] Define BIO label list for both models → `config/labels.json`
- [x] Document supported entity vocabularies (topics, days, priorities, statuses) → `config/vocab.json`

---

## Phase 2 — Templates & Dataset Generation ✅

- [x] Write sentence templates for scheduling intents (add, delete, update, show, behavioral) → `templates/scheduling/`
- [x] Write sentence templates for learning intents (create, update, delete, show) → `templates/learning/`
- [x] Add word-order variations (entity-first, question-style, implicit action, confirmation) → in template groups
- [x] Add diverse entity values (academic, personal, informal task names; all topics) → `config/vocab.json` + `generators/slot_fillers.py`
- [x] Build auto-generation script from templates → token + BIO labels → `generators/build_dataset.py`
- [x] Generate base scheduling dataset → `datasets/scheduling/raw/scheduling_ner.json` (10,605 examples)
- [x] Generate base learning dataset → `datasets/learning/raw/learning_ner.json` (5,378 examples — create/update/delete only)
- [x] Validate generated labels → `generators/validate_dataset.py` + `evaluation/validation_report.json`

---

## Phase 3 — Fix Training (Root Cause)

- [x] Fix BIO subword alignment in trainer (label continuation subwords with `I-`, not `-100`) → `ner_training_utils.py` + Colab notebooks
- [x] Apply fix to **scheduling NER** → `colab/Train_Scheduling_NER.ipynb`
- [x] Apply fix to **learning NER** → `colab/Train_Learning_NER.ipynb`
- [x] Switch evaluation from accuracy to **entity-level F1** (`seqeval`, per entity type)
- [x] Train scheduling NER on Colab → save to `Eva_AI_Server/models/ner_model/`
- [x] Train learning NER on Colab → save to `Eva_AI_Server/models/learning_ner/`
- [x] Save baseline F1 scores per entity → `evaluation/baseline_f1_*.json`

---

## Phase 4 — Data Augmentation (in progress)

- [x] Build augmentation script for existing clean data → `generators/augment_dataset.py`, `augment_utils.py`
- [x] Spelling errors (swap, delete, insert, substitute, common typos) → `config/augmentation.json` `entity_typos` / `o_token_typos`
- [x] Capitalization variation (ALL CAPS, lowercase, mixed)
- [x] Punctuation noise (commas, exclamation on O tokens)
- [x] Controlled word-order shuffling (entity chunks stay intact)
- [x] Filler word insertion (`please`, `hey`, `yar`, etc.)
- [x] Abbreviations and shortcuts (`mon`, `hrs`, `wks`, etc.)
- [x] Recalculate entity spans after every augmentation (token-level BIO preserved)
- [x] Merge augmented data with base datasets → `datasets/*/final/*_ner.json`
- [x] Hard negatives for `my` / `roadmap` / OOP cases → `generators/hard_negatives.json`
- [x] Starter adversarial eval set → `evaluation/adversarial/adversarial_tests.json`
- [ ] Retrain both NER models on augmented data (Colab — use `datasets/*/final/` paths)

---

## Phase 5 — Hard Examples & Balance ✅

- [x] Add hard negative examples (similar words that must NOT be tagged) → `generators/hard_negatives.json`
- [x] Add targeted examples for weak entities → `generators/targeted_examples.json`
- [x] Balance rare entity types via oversampling → `generators/balance_dataset.py`, `config/balance.json`
- [x] Balance report → `evaluation/balance_report.json`
- [x] F1 comparison helper (post-retrain) → `evaluation/compare_f1.py`
- [ ] Retrain both NER models (Colab — after all prep phases)
- [ ] Compare F1 per entity vs Phase 3 baseline (after retrain)

---

## Phase 6 — Pipeline Runtime Fixes ✅

- [x] Add vocabulary / regex fallback after NER for **scheduling add** → `pipeline/add_entity_fallback.py`
- [x] Add vocabulary / regex fallback after NER for **learning** intents → `pipeline/learning_entity_fallback.py`
- [x] Extend existing delete/update fallbacks (wired via `entity_postprocess.apply_entity_fallbacks`)
- [x] Add smart spell correction before NER → `pipeline/spell_correction.py`
- [x] Add post-processing entity validation (strip fillers, subtopic noise) → `pipeline/entity_postprocess.py`
- [x] Wire pipeline changes in `Eva_AI_Server/pipeline/ner.py`
- [ ] Deploy updated models to `Eva_AI_Server/models/` (after Colab retrain on final datasets)

---

## Phase 7 — Advanced Training (Optional)

- [ ] Add class weights for imbalanced `O` vs entity labels
- [ ] Increase max sequence length if examples truncate (128 → 192)
- [ ] Train 15–20 epochs with early stopping on entity F1
- [ ] Add CRF layer on top of BERT (boundary enforcement)
- [ ] Retrain and compare F1 vs Phase 5

---

## Phase 8 — Evaluation & Monitoring ✅

- [x] Build adversarial test set → `evaluation/adversarial/adversarial_tests.json` (22 cases)
- [x] Build error analysis tool → `evaluation/adversarial_eval.py`, `errors/adversarial_failures.json`
- [x] Automated eval runner → `evaluation/run_adversarial_eval.py`
- [x] Manual test guide → `evaluation/EVAL_GUIDE.md`
- [x] Log weak entity types / failure patterns → `adversarial_report.json` summary section
- [ ] Feed failures back into templates (do after each eval run as needed)

---

## Phase 9 — Real-World Data (Optional)

- [ ] Collect 200–500 real user commands (natural typing, no format instructions)
- [ ] Manually annotate with Label Studio or script
- [ ] Add Urdu-English / informal Pakistani English patterns
- [ ] Merge real data into training sets
- [ ] Final retrain + full evaluation

---

## Phase 10 — Done Criteria

- [ ] Entity F1 acceptable on all major entity types (scheduling + learning)
- [ ] Adversarial test set passes at agreed threshold
- [ ] Typos and word-order variations handled reliably
- [ ] Models deployed and tested end-to-end in EVA pipeline

---

## Quick Reference — Problems → Phase

| Problem | Primary phase |
|---------|---------------|
| Partial extraction (`physic` instead of `physics exam`) | Phase 3, Phase 7 (CRF) |
| Spelling mistakes break NER | Phase 4, Phase 6 |
| Word order variation fails | Phase 2, Phase 4 |
| Wrong entity boundaries | Phase 3, Phase 7 |
| Dataset too clean / unnatural | Phase 2, Phase 4, Phase 9 |
| Model tags wrong words as entities | Phase 5 |
| Weak on one entity type (e.g. collaborator) | Phase 5 |
| NER misses known topics/days | Phase 6 |

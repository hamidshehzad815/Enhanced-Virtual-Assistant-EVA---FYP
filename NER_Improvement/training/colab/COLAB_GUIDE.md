# Google Colab — Phase 3 NER Training

Train both NER models on Colab GPU. No local install needed.

## Files you need

Upload **one** of these options to Colab:

### Option A — Upload whole folder (recommended)

Zip `NER_Improvement/` and upload to Google Drive, then unzip in Colab:

```
NER_Improvement/
├── config/labels.json
├── datasets/scheduling/final/scheduling_ner.json   # Phase 4 augmented (or raw/ for baseline)
├── datasets/learning/final/learning_ner.json
└── training/
    ├── ner_training_utils.py
    └── colab/
        ├── Train_Scheduling_NER.ipynb
        └── Train_Learning_NER.ipynb
```

### Option B — Minimum upload

Upload these 3 files into a Colab folder (e.g. `/content/eva_ner/`):

| File | From |
|------|------|
| `labels.json` | `NER_Improvement/config/labels.json` |
| `scheduling_ner.json` | `NER_Improvement/datasets/scheduling/final/` (Phase 4) or `raw/` (baseline) |
| `learning_ner.json` | `NER_Improvement/datasets/learning/final/` (Phase 4) or `raw/` (baseline) |

Copy `ner_training_utils.py` code into the notebook (included in notebook cells).

---

## Notebooks

| Notebook | Model | Deploy to |
|----------|-------|-----------|
| `Train_Scheduling_NER.ipynb` | scheduling + behavioral | `Eva_AI_Server/models/ner_model/` |
| `Train_Learning_NER.ipynb` | learning intents | `Eva_AI_Server/models/learning_ner/` |

Run **one notebook at a time**. Each takes ~15–30 min on Colab T4 GPU.

---

## After training

1. Download the `final_model.zip` from Colab (last cell creates it)
2. Unzip into your project:
   - Scheduling → `Eva_AI_Server/models/ner_model/`
   - Learning → `Eva_AI_Server/models/learning_ner/`
3. Save the F1 report JSON to `NER_Improvement/evaluation/`

Required files in model folder:
```
config.json
model.safetensors  (or pytorch_model.bin)
tokenizer.json
tokenizer_config.json
vocab.txt
```

---

## Hyperparameters (defaults in notebooks)

| Setting | Value |
|---------|-------|
| Base model | `bert-base-cased` |
| Max length | 128 |
| Epochs | 10 |
| Batch size | 16 |
| Learning rate | 3e-5 |
| Eval metric | entity F1 (seqeval) |
| Best model | saved by highest val F1 |

---

## Phase 3 fix included

Both notebooks use **correct BIO subword alignment**:
- `physics` → `physic` + `##s` → labels `B-task_name`, `I-task_name`
- Old bug: `##s` got `-100` → partial extraction

See `align_labels_with_tokens()` in `ner_training_utils.py`.

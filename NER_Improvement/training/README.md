# Phase 3 — NER Training

Train scheduling and learning NER with **correct BIO subword alignment** and **entity-level F1** evaluation.

## Google Colab (recommended)

No local install needed. Use GPU on Colab.

1. Upload `NER_Improvement/` folder to Google Drive (or zip and upload)
2. Open notebook in Colab:
   - `colab/Train_Scheduling_NER.ipynb` → scheduling + behavioral
   - `colab/Train_Learning_NER.ipynb` → learning intents
3. Set `DATA_ROOT` path in notebook
4. Run all cells
5. Download `*_model.zip` and copy to `Eva_AI_Server/models/`

Full instructions: **`colab/COLAB_GUIDE.md`**

---

## Files

| File | Purpose |
|------|---------|
| `colab/Train_Scheduling_NER.ipynb` | Colab notebook — scheduling NER |
| `colab/Train_Learning_NER.ipynb` | Colab notebook — learning NER |
| `colab/COLAB_GUIDE.md` | Upload paths, deploy steps |
| `ner_training_utils.py` | Shared alignment + dataset helpers |
| `train_ner.py` | Local CLI trainer (optional) |
| `test_alignment.py` | Unit test for BIO alignment fix |

---

## What gets fixed (Phase 3)

BERT splits `"physics"` → `physic` + `##s`. Old trainers ignored `##s` with `-100`.

**Correct alignment:**
```
physic  → B-task_name
##s     → I-task_name   ← was -100 (bug)
```

---

## After training — deploy

| Model | Colab output | Copy to |
|-------|--------------|---------|
| Scheduling | `scheduling_ner_output/final/` | `Eva_AI_Server/models/ner_model/` |
| Learning | `learning_ner_output/final/` | `Eva_AI_Server/models/learning_ner/` |

Also save F1 reports to:
- `evaluation/baseline_f1_scheduling.json`
- `evaluation/baseline_f1_learning.json`

---

## Local training (optional)

Only if you have torch/GPU locally:

```bash
cd NER_Improvement/training
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python train_ner.py --model scheduling --epochs 10
python train_ner.py --model learning --epochs 10
```

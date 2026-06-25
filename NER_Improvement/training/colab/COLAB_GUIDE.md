# Google Colab — NER Training

Train both NER models on Colab GPU.

## Upload

Zip `NER_Improvement/` to Drive (recommended) or upload minimum:

| File | Path |
|------|------|
| `labels.json` | `config/labels.json` |
| **Scheduling dataset** | `datasets/scheduling/final/scheduling_ner.json` |
| **Learning dataset** | `datasets/learning/final/learning_ner.json` |
| Notebooks | `training/colab/Train_*_NER.ipynb` |

**Use `final/` datasets** — they include augmentation, negatives, and balancing. Do **not** train on `raw/`.

## Notebooks

| Notebook | Deploy to |
|----------|-----------|
| `Train_Scheduling_NER.ipynb` | `Eva_AI_Server/models/ner_model/` |
| `Train_Learning_NER.ipynb` | `Eva_AI_Server/models/learning_ner/` |

Run **one at a time**. ~20–45 min each on T4.

## Hyperparameters (current)

| Setting | Value |
|---------|-------|
| Base model | `bert-base-uncased` |
| Max length | 128 |
| Epochs | 5 (max) |
| Early stopping | patience **2** (stops if val F1 flat) |
| Batch size | 16 |
| Learning rate | 2e-5 |
| Dropout | 0.2 |
| Best checkpoint | highest val entity F1 |

## After training

1. Download `*_ner_model.zip` from last cell
2. Unzip into `Eva_AI_Server/models/ner_model/` and `learning_ner/`
3. Restart AI server
4. Run adversarial eval locally:
   ```bash
   cd NER_Improvement/evaluation
   python run_adversarial_eval.py
   ```

Target: **90–96% adversarial pass rate**, not 100% synthetic val F1.

## Regenerate datasets locally (if you change templates)

```bash
cd NER_Improvement/generators
python3 build_dataset.py
python3 augment_dataset.py
python3 balance_dataset.py
python3 validate_dataset.py --path ../datasets/scheduling/final/scheduling_ner.json
python3 validate_dataset.py --path ../datasets/learning/final/learning_ner.json
```

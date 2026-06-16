# CLF_Improvement — Classifier 1 & 2 Improvement Workspace

This folder is a **standalone workflow** to improve EVA's two text classifiers:

- **CLF1** (input type): `command`, `general`, `out_of_scope`, `confirmation`, `multiple_command`
- **CLF2** (intent for commands): `scheduling_add`, `scheduling_delete`, `scheduling_update`, `scheduling_show`, `learning_create`, `learning_update`, `learning_delete`, `learning_show`, `behavioral`

The goal is to make the classifiers robust to **ambiguous “show” sentences**, e.g.
- "show physics exam task" → `scheduling_show`
- "show my behavioral summary" → `behavioral`

## Workflow

1. **Edit templates** in:
   - `templates/clf1/`
   - `templates/clf2/`
2. Generate datasets:

```bash
cd CLF_Improvement/generators
python3 build_dataset.py
python3 balance_dataset.py
python3 validate_dataset.py --path ../datasets/clf1/final/clf1.jsonl --path ../datasets/clf2/final/clf2.jsonl
```

3. Train on Colab (GPU):
   - `training/colab/Train_CLF1.ipynb`
   - `training/colab/Train_CLF2.ipynb`

4. Deploy trained model folders to:
   - CLF1 → `Eva_AI_Server/models/clf1/`
   - CLF2 → `Eva_AI_Server/models/intent_classifier/`

## Dataset format

Both datasets are **JSONL** lines:

```json
{"text": "show physics exam task", "label": "scheduling_show", "meta": {"source": "template", "template_id": "show_task_v1"}}
```

## Notes

- Generation is deterministic (seeded) to make experiments repeatable.
- `balance_dataset.py` equalizes class counts to reduce bias toward frequent labels.
- `validate_dataset.py` checks class coverage, duplicates, and basic sanity rules.


# Google Colab — CLF1 & CLF2 Training

Train EVA's sequence classifiers on Colab GPU.

## Upload

Recommended: upload the whole `CLF_Improvement/` folder to Google Drive, then set:

- `ROOT = Path("/content/drive/MyDrive/CLF_Improvement")`

Datasets:
- `datasets/clf1/final/clf1.jsonl`
- `datasets/clf2/final/clf2.jsonl`

## Notebooks

- `Train_CLF1.ipynb` → deploy to `Eva_AI_Server/models/clf1/`
- `Train_CLF2.ipynb` → deploy to `Eva_AI_Server/models/intent_classifier/`

## After training

Download the `final_model.zip` created by the last cell, unzip into the correct model folder.

Required files in model folder:

```
config.json
model.safetensors (or pytorch_model.bin)
tokenizer.json
tokenizer_config.json
vocab.txt
label_map.json
```


# 🧠 Transformers & BERT — EVA AI Server

## What Is a Transformer?

A **Transformer** is a deep learning architecture introduced in the 2017 paper *"Attention Is All You Need"*. It processes sequences of text by applying **self-attention**: every word in a sentence attends to every other word simultaneously, learning the relationships between them.

This is a fundamental departure from older recurrent models (RNNs/LSTMs) which processed text word-by-word and suffered from forgetting long-range dependencies.

### Core Idea: Self-Attention

Given the sentence: *"Add meeting with Ahmed on Friday"*

Self-attention allows the model to learn that:
- *"meeting"* relates to *"Add"* (action → object)
- *"Ahmed"* is a person (collaborator entity)
- *"Friday"* relates to *"on"* and represents a date

All these relationships are learned by computing **attention scores** between pairs of tokens.

---

## What Is BERT?

**BERT** (Bidirectional Encoder Representations from Transformers) is a pre-trained Transformer model by Google (2018). Key characteristics:

| Property | Detail |
|---|---|
| **Bidirectional** | Reads text left-to-right AND right-to-left simultaneously |
| **Pre-trained** | Trained on Wikipedia + BookCorpus (billions of words) |
| **Transfer learning** | Fine-tuned on downstream tasks (classification, NER, etc.) |
| **Architecture** | Only the Transformer encoder (not decoder) |

BERT introduced the concept of **masked language modeling**: randomly hiding words in a sentence and training the model to predict them from context. This forces the model to learn deep bidirectional representation.

---

## How EVA Uses Transformers

Both classifiers and the NER model in EVA are fine-tuned Transformer models loaded via the HuggingFace `transformers` library.

### In `classifier1.py` and `classifier2.py`:

```python
from transformers import AutoModelForSequenceClassification, AutoTokenizer

self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_dir))
self.model = AutoModelForSequenceClassification.from_pretrained(str(self.model_dir))
self.model.eval()
```

- `AutoTokenizer`: Converts raw text into token IDs that BERT understands
- `AutoModelForSequenceClassification`: A BERT encoder with a **classification head** on top
- `.eval()`: Switches model to inference mode (disables dropout, batch norm updates)

### In `ner.py`:

```python
from transformers import AutoModelForTokenClassification

model = AutoModelForTokenClassification.from_pretrained(str(candidate))
```

- `AutoModelForTokenClassification`: BERT encoder with per-token label predictions

---

## The Tokenization Process

Tokenization converts raw text into a format the model understands.

### Example Tokenization

Input: `"add physics exam on friday"`

```
Tokens: ["add", "physics", "exam", "on", "friday"]
Input IDs: [101, 5587, 10980, 8476, 2006, 5958, 102]
```

> `101` = [CLS] (classification token), `102` = [SEP] (separator token)

### Key Tokenizer Parameters (used in EVA):

```python
inputs = self.tokenizer(
    text,
    return_tensors="pt",       # PyTorch tensors
    truncation=True,           # Cut text longer than max_length
    padding=True,              # Pad shorter sequences
    max_length=64,             # Max 64 tokens for classifiers
)
```

- **Truncation**: Long inputs are cut to max_length (important for efficiency)
- **Padding**: Short inputs are padded to uniform length for batch processing
- **max_length=64** for classifiers (commands are short), **128** for NER (needs more context)

### Subword Tokenization

BERT uses **WordPiece tokenization**. Unknown or rare words are split into subwords:
- `"scheduling"` → `["schedule", "##ing"]`
- `"collaborator"` → `["collabor", "##ator"]`

The `##` prefix marks continuation subwords. This is handled automatically by `AutoTokenizer`.

---

## Inference: From Text to Prediction

```python
with torch.no_grad():                          # Disable gradient computation
    logits = self.model(**inputs).logits       # Raw scores per class
    probabilities = torch.softmax(logits, dim=-1)[0]  # Convert to probabilities
```

### `torch.no_grad()`
Inference doesn't need gradients. This saves memory and speeds up computation significantly. **Always used in production inference.**

### Logits
Raw unnormalized scores output by the model. Example for 5 classes:
```
logits = [-2.1, 0.3, 3.8, -1.2, 0.4]
```

### Softmax
Converts logits into a probability distribution that sums to 1.0:
```
softmax([-2.1, 0.3, 3.8, -1.2, 0.4]) = [0.01, 0.07, 0.89, 0.02, 0.08]
```

The class with the highest probability wins.

---

## Transfer Learning

EVA's models were not trained from scratch. They were:

1. **Pre-trained** on massive text corpora (Wikipedia, books) — already done
2. **Fine-tuned** on domain-specific labeled data (EVA's command examples)

This approach requires far less training data and time than training from scratch, while achieving high accuracy.

```
Pre-trained BERT
    │
    │ Fine-tuning on EVA dataset
    ▼
EVA Intent Classifier / NER Model
```

---

## Why HuggingFace Transformers Library?

The `transformers` library (by HuggingFace) provides:
- `AutoTokenizer` / `AutoModel` — load any compatible model from a local directory or Hub
- Consistent API across models (BERT, RoBERTa, DistilBERT, etc.)
- Model saving/loading, tokenizer files, config JSON

EVA uses `AutoModel*` classes (not model-specific classes) so the underlying model architecture can be swapped transparently by changing the saved model directory.

---

## Summary Table

| Concept | Role in EVA |
|---|---|
| Transformer architecture | Foundation of all 3 ML models |
| BERT (bidirectional encoding) | Reads commands in full context |
| Transfer learning | Models fine-tuned from pre-trained BERT |
| Tokenization (WordPiece) | Converts text to token IDs |
| Logits + Softmax | Output probabilities from model |
| `torch.no_grad()` | Efficient inference (no gradient tracking) |
| `AutoTokenizer` / `AutoModel*` | HuggingFace unified loading API |

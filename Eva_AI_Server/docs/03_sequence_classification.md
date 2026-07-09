# 🏷️ Text Classification — EVA AI Server

## What Is Text Classification?

**Text classification** (also called *text categorization*) is the NLP task of assigning a predefined label to a piece of text. A model reads a sentence and outputs which category it belongs to.

Examples:
- Email spam vs. not spam
- Sentiment: positive / negative / neutral
- **EVA**: Is this message a command, a question, or out of scope?

---

## EVA Has Two Classifiers

### Classifier 1 — Input Type Classifier (`classifier1.py`)

**Purpose**: Determine the *type* of input  
**Model**: `AutoModelForSequenceClassification` loaded from `settings.CLF1_MODEL_DIR`  
**Classes (5)**:

| Label | Meaning | Example |
|---|---|---|
| `command` | A direct directive for EVA | *"Add meeting on Monday"* |
| `general` | A conversational/general query | *"What can you do?"* |
| `out_of_scope` | Irrelevant or unsupported request | *"Tell me a joke"* |
| `confirmation` | A yes/no or confirmatory reply | *"Yes, do it"* |
| `multiple_command` | Multiple distinct commands in one message | *"Add X and delete Y"* |

### Classifier 2 — Intent Classifier (`classifier2.py`)

**Purpose**: Determine the specific *intent* of a command  
**Model**: `AutoModelForSequenceClassification` loaded from `settings.CLF2_MODEL_DIR`  
**Classes (8 supported intents + 1 legacy label rejected at runtime):**

| Label | Domain |
|---|---|
| `scheduling_add` | Add a task/event |
| `scheduling_delete` | Delete a task |
| `scheduling_update` | Update a task |
| `scheduling_show` | Show/list tasks |
| `learning_create` | Create a study plan |
| `learning_update` | Update a study plan (pause, resume, complete, skip, reschedule) |
| `learning_delete` | Delete a study plan |
| `behavioral` | Query behavioral patterns |

### Not supported in chat

| Removed / legacy | Use instead |
|---|---|
| Showing learning plan progress in chat (legacy Classifier 2 label `learning_show`) | **Roadmap screen** in the app — `GET /api/roadmaps/plans` and related backend APIs |

If an old model still predicts the legacy label, EVA replies that chat progress is not supported and directs the user to the Roadmap tab (`handlers/unsupported_chat_intents.py`).

---

## Architecture: Classification Head on BERT

```
Input Text
    │
    ▼
Tokenizer  →  [CLS] add meeting on monday [SEP]
    │
    ▼
BERT Encoder (12 layers of attention)
    │
    ▼
[CLS] token hidden state → Dense Layer → Logits (one per class)
    │
    ▼
Softmax → Probability Distribution
    │
    ▼
argmax → Predicted Label
```

The key insight: BERT produces a **[CLS] token** at the beginning of every sequence. After fine-tuning for classification, this token's hidden state encodes a rich representation of the whole sentence, which is then fed to a simple linear classification layer.

---

## Inference Code Walkthrough

```python
def predict(self, text: str) -> Dict[str, object]:
    # Step 1: Tokenize
    inputs = self.tokenizer(
        text,
        return_tensors="pt",    # PyTorch format
        truncation=True,        # Clip if too long
        padding=True,
        max_length=64,          # Short sentences → small max length
    )

    # Step 2: Forward pass (no gradient needed at inference)
    with torch.no_grad():
        logits = self.model(**inputs).logits
        probabilities = torch.softmax(logits, dim=-1)[0]

    # Step 3: Decode label
    pred_id = int(torch.argmax(probabilities).item())
    label = self.id2label.get(pred_id, str(pred_id))

    return {
        "label": label,
        "confidence": float(probabilities[pred_id].item()),
        "all_probs": {...},  # full probability dict per class
    }
```

**`confidence`**: The probability assigned to the winning class (0.0 – 1.0).  
A low confidence can signal ambiguous input and could trigger fallback behavior.

---

## Label Mapping

Models output integer class IDs (e.g., `0`, `1`, `2`). A **label map** translates these to human-readable strings.

EVA loads this from:
1. `label_map.json` in the model directory (preferred)
2. `label_encoder.pkl` (scikit-learn encoder — Classifier 2 fallback)
3. The model's `config.json` (`id2label` field)

```python
id2label = {
    0: "command",
    1: "general",
    2: "out_of_scope",
    3: "confirmation",
    4: "multiple_command"
}
```

---

## Pipeline Position

```
Classifier 1 Output: "command"
        │
        ▼  (only if "command")
Classifier 2 Output: "scheduling_add"
        │
        ▼
NER → Entity Extraction
```

If Classifier 1 returns anything other than `"command"`, Classifier 2 is **never called** — this is an intentional optimization and gating mechanism.

---

## Fine-Tuning Concepts

These models were originally **pre-trained BERT** models and then **fine-tuned**:

| Stage | Dataset | Objective |
|---|---|---|
| Pre-training | Wikipedia + Books | Predict masked words (MLM) |
| Fine-tuning | EVA command examples | Classify correct label |

Fine-tuning adjusts the model's weights to minimize **cross-entropy loss** on labeled examples:

```
Loss = -log(probability of correct class)
```

The lower the loss, the better the model distinguishes between classes.

---

## Singleton Pattern

Both classifiers use the singleton pattern — they are instantiated once at module import time and loaded into memory once at server startup:

```python
# At bottom of classifier1.py:
classifier1 = Classifier1()

# In main.py lifespan:
model1_ok = classifier1.load()
```

This avoids re-loading multi-hundred MB model files on every request. Subsequent calls to `predict()` reuse the already-loaded model.

---

## Summary Table

| Concept | Role in EVA |
|---|---|
| Sequence classification | Assign label to entire sentence |
| Two-stage classification | Coarse gating (Clf1) → Fine intent (Clf2) |
| [CLS] token | BERT's sentence-level representation |
| Softmax | Converts logits to probabilities |
| argmax | Picks the highest-probability class |
| Label map | Maps integer IDs to human-readable class names |
| Confidence score | Probability of the predicted class |
| Singleton pattern | Models loaded once, reused across requests |

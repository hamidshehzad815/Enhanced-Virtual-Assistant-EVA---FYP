# 🔍 Named Entity Recognition (NER) — EVA AI Server

## What Is Named Entity Recognition?

**Named Entity Recognition (NER)** is the NLP task of identifying and classifying **named entities** within text — i.e., specific real-world objects like people, dates, locations, or custom domain entities.

For EVA, NER extracts the structured data needed to execute a command. From:

> *"Add physics exam on Friday at 3pm with high priority"*

NER extracts:
```json
{
  "task_name": "physics exam",
  "date": "Friday",
  "time": "3pm",
  "priority": "high"
}
```

---

## Token Classification (vs. Sequence Classification)

While sequence classification assigns **one label to an entire sentence**, NER is a **token classification** task: it assigns a label to **every individual token** in the input.

```
Token:  [add]  [physics] [exam]  [on]  [friday] [at] [3pm]  [with] [high] [priority]
Label:  [O]    [B-TASK]  [I-TASK] [O]  [B-DATE]  [O] [B-TIME] [O]  [B-PRIORITY] [O]
```

The model (`AutoModelForTokenClassification`) outputs one label per token.

---

## BIO Tagging Scheme

EVA's NER model uses the **BIO (Beginning-Inside-Outside)** tagging scheme:

| Tag | Meaning |
|---|---|
| `O` | Outside any entity (not part of an entity) |
| `B-<TYPE>` | **Beginning** of an entity of type `<TYPE>` |
| `I-<TYPE>` | **Inside** (continuation) of an entity started with `B-<TYPE>` |

### Example

Sentence: *"delete my morning standup"*

```
Token:  [delete] [my] [morning] [standup]
BIO:    [O]      [O]  [B-TASK]  [I-TASK]
```

→ `task_name = "morning standup"` (merged from B + I tags)

### Why BIO?

- It handles **multi-word entities** (e.g., task names with spaces)
- It allows the model to unambiguously represent entity boundaries
- Avoids confusion between separate adjacent entities

---

## EVA's Entity Types

Common entity labels used in the system:

| Entity | Examples |
|---|---|
| `TASK` / `task_name` | *"morning standup"*, *"physics exam"* |
| `DATE` / `date` | *"Friday"*, *"tomorrow"*, *"2025-05-01"* |
| `TIME` / `time` | *"3pm"*, *"10:30am"* |
| `PRIORITY` / `priority` | *"high"*, *"urgent"* |
| `STATUS` / `status` | *"done"*, *"completed"* |
| `COLLABORATOR` | *"Ahmed"*, *"Sara"* |
| `DURATION` / `duration` | *"2 hours"*, *"30 minutes"* |
| `TOPIC` / `topic` | *"machine learning"*, *"DSA"* |

---

## Inference Code Walkthrough (`ner.py`)

```python
def extract(self, text: str, intent_hint: str = "") -> Dict[str, Any]:
    # Step 1: Tokenize with offset mapping
    encoded = self.tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=128,
        return_offsets_mapping=True,   # KEY: character offsets for each token
    )

    offsets = encoded.pop("offset_mapping")[0].tolist()

    # Step 2: Run model
    with torch.no_grad():
        logits = self.model(**encoded).logits
        pred_ids = torch.argmax(logits, dim=-1)[0].tolist()

    # Step 3: Decode labels with character positions
    tags_with_offsets = []
    for pred_id, (start, end) in zip(pred_ids, offsets):
        if start == end:  # skip special tokens ([CLS], [SEP]) — zero-length offsets
            continue
        tag = self.id2label.get(pred_id, "O")
        tags_with_offsets.append((tag, int(start), int(end)))

    # Step 4: Aggregate BIO spans into entity strings
    entities = self._aggregate_entities(text, tags_with_offsets)
    return entities
```

### `return_offsets_mapping=True`
This is a critical feature: the tokenizer returns the original **character start/end positions** for each token. This allows EVA to extract the exact substring from the original text, even after subword tokenization splits words.

**Why is this needed?**  
After subword tokenization, a token like `##ing` has no clear position. But with offsets, we know it spans characters 10–13 in the original string, so we can directly slice `original_text[10:13]`.

---

## Entity Aggregation (BIO → String)

The `_aggregate_entities` method converts a flat list of `(BIO_tag, start_char, end_char)` tuples into merged entity strings:

```python
# Input:
# [("B-TASK", 0, 7), ("I-TASK", 8, 13), ("O", 14, 16), ("B-DATE", 17, 23)]

# Character slicing from original text:
# "physics exam on friday"

# Output:
# {"task_name": "physics exam", "date": "friday"}
```

### Edge Case: Subword B-tags
Sometimes the model emits a `B-` tag for adjacent subword tokens of the *same* entity (e.g., `"F"` + `"##aisal"`). EVA's aggregator detects this and **treats them as continuation** (I-tags), not as separate entities:

```python
b_should_split = prefix == "B" and not (
    current_type
    and entity_type == current_type
    and start <= current_end + 1        # no gap between tokens
    and (not gap_text.strip())           # no text in between
)
```

---

## Fallback Mechanism (Hybrid NER)

The NER model is not infallible. For `scheduling_delete` and `scheduling_update` intents, EVA applies a **deterministic regex fallback** after the model:

```python
if intent_hint == "scheduling_delete":
    fallback_entities = extract_delete_entities_fallback(text)
    for key, value in fallback_entities.items():
        current_value = entities.get(key)
        if current_value in (None, "", [], {}):
            entities[key] = value   # only fill gaps, don't override model output
```

The fallback **only fills missing fields** — it never overrides a model prediction.

---

## Tokenizer Loading Strategy

The NER model uses a robust multi-stage tokenizer loading strategy:

1. Try **fast tokenizer** (uses Rust, handles offsets natively)
2. If that fails, build `vocab.json` + `merges.txt` from `tokenizer.json` for **RoBERTa slow tokenizer**
3. If both fail, skip this model directory and try the next candidate (checkpoint fallback)

```python
def _candidate_model_dirs(self) -> List[Path]:
    candidates = [self.model_dir]
    checkpoint_dirs = sorted(
        self.model_dir.glob("checkpoint-*"),
        key=lambda p: int(p.name.split("-")[-1]),
        reverse=True,
    )
    candidates.extend(checkpoint_dirs)
    return candidates
```

This means EVA can **automatically fall back to the latest training checkpoint** if the final model directory is corrupt or missing.

---

## Summary Table

| Concept | Role in EVA |
|---|---|
| Token classification | Per-token labeling (not sentence-level) |
| BIO tagging scheme | Marks beginning/inside/outside of entities |
| `AutoModelForTokenClassification` | BERT model with per-token output head |
| `return_offsets_mapping` | Maps tokens back to character positions in original text |
| Entity aggregation | Merges B/I token spans into full entity strings |
| Regex fallback | Fills NER gaps with deterministic rules |
| Checkpoint fallback | Automatically uses latest training checkpoint if model missing |

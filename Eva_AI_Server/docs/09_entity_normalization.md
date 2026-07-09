# 🧹 Entity Normalization & Scoping — EVA AI Server

## Overview

After entities are extracted by the NER model (and fallback), two important post-processing steps occur:

1. **Entity Scoping** — filter entities to only those relevant to the detected intent
2. **Entity Normalization** — map raw user values to canonical database-safe values

---

## Entity Scoping (`entity_scoper.py`)

### What Is Scoping?

NER models sometimes extract entities that are irrelevant to the detected intent. For example:
- Intent: `scheduling_show` (show tasks)
- NER extracts: `{ "task_name": "meeting", "collaborator": "Ahmed" }`
- But `collaborator` is not a valid filter for the show command!

**Scoping** filters the entity dict to only retain keys that are valid for the given intent.

### Intent-Entity Scope Map

```python
_INTENT_ENTITY_SCOPE = {
    "scheduling_add":    {"task_name", "date", "time", "priority", "duration", "collaborator"},
    "scheduling_delete": {"task_name", "date", "priority", "status"},
    "scheduling_update": {"task_name", "date", "priority", "status",
                          "new_title", "new_date", "new_time",
                          "new_priority", "new_status", "new_duration"},
    "scheduling_show":   {"date", "priority", "status", "task_name"},
    "learning_create":   {"topic", "subtopic", "duration", "start_date", "collaborator"},
    "learning_update":   {"topic", "subtopic", "date", "new_date", "new_duration",
                          "next_topic", "new_start_date"},
    "learning_delete":   {"topic", "subtopic", "date", "start_date"},
    "behavioral":        {"day"},
}
```

**Not supported:** showing learning progress via chat (no `learning_show` intent). Use the app **Roadmap** APIs/screens instead.

Any entity key not in the allowed set for the given intent is **silently dropped**.

---

## Entity Key Aliasing

NER models are not always consistent in the key names they output. For example, a collaborator entity might be labelled `"person"`, `"person_name"`, or `"collaborator"` depending on the training data version.

**Aliasing** normalizes all these variants to a single canonical key:

```python
_ENTITY_ALIASES = {
    # Collaborator variants:
    "person":        "collaborator",
    "person_name":   "collaborator",
    "people":        "collaborator",

    # Update intent title variants:
    "new_taskname":    "new_title",
    "new_task_name":   "new_title",
    "new_scheduled_date": "new_date",

    # Pass-through (already canonical):
    "task_name":  "task_name",
    "date":       "date",
    "priority":   "priority",
    # ...
}
```

Aliasing runs **before** scoping, so normalization happens first:

```python
def scope_entities(entities, intent):
    allowed = _INTENT_ENTITY_SCOPE.get(intent, set())
    scoped = {}
    for raw_key, value in entities.items():
        key = _normalize_key(raw_key)      # apply alias
        if allowed and key not in allowed: # then scope
            continue
        scoped[key] = value
    return scoped
```

---

## Value Normalization (`task_value_normalizer.py`)

Once entity keys are clean, entity **values** also need normalization. A user might say:
- *"urgent"* → should be stored as `"high"` priority
- *"done"* → should be stored as `"complete"` status

### Priority Canonicalization

```python
_PRIORITY_MAP = {
    "high":      "high",
    "urgent":    "high",
    "critical":  "high",
    "immediate": "high",
    "asap":      "high",
    "important": "high",
    "medium":    "medium",
    "normal":    "medium",
    "standard":  "medium",
    "moderate":  "medium",
    "low":       "low",
    "minor":     "low",
    "trivial":   "low",
    "backburner":"low",
    "optional":  "low",
}
```

### Status Canonicalization

```python
_STATUS_MAP = {
    "pending":    "pending",
    "ongoing":    "ongoing",
    "in progress":"ongoing",
    "active":     "ongoing",
    "complete":   "complete",
    "completed":  "complete",
    "done":       "complete",
    "finished":   "complete",
    "resolved":   "complete",
    "closed":     "complete",
}
```

Both functions return an **empty string** for unknown values, signaling to the handler that the value is invalid.

---

## Weekday Normalization

The `behavioral` intent expects a `day` entity (weekday name). But the NER model might extract a full date string like `"monday afternoon"` instead of just `"monday"`.

The `_extract_weekday()` function in `entity_scoper.py` handles this:

```python
_WEEKDAYS = {"monday", "tuesday", "wednesday", ..., "sunday"}

def _extract_weekday(value):
    normalized = value.strip().lower()
    if normalized in _WEEKDAYS:
        return normalized
    for weekday in _WEEKDAYS:
        if re.search(rf"\b{re.escape(weekday)}\b", normalized):
            return weekday   # extract weekday substring
    return None
```

Additionally, `main.py` has `_normalize_weekday_value()` and `_repair_weekday_date_entity()` which handle subword tokenizer artifacts where `"friday"` might be tokenized and returned as just `"day"` by the NER model — it searches the original text for the full weekday name.

---

## Canonical vs. User-Facing Values

The system maintains a strict separation:

| Layer | Values |
|---|---|
| **User input** | "urgent", "asap", "done", "finished" |
| **Canonical (DB)** | "high", "complete" |
| **Display** | Formatted by Gemini in natural language |

All database queries and storage use canonical values. User-facing text uses Gemini to generate natural phrasing.

---

## Duration Normalization

Durations are parsed from strings like *"2 hours"* or *"30 minutes"* into a uniform integer (minutes):

```python
def _parse_duration_update(value):
    raw = str(value or "").strip().lower()
    match = re.search(r"(\d+(?:\.\d+)?)", raw)
    amount = float(match.group(1))
    if "hour" in raw or "hr" in raw:
        return max(5, int(amount * 60))    # convert hours → minutes
    if "min" in raw:
        return max(5, int(amount))
    return max(5, int(amount))
```

The `max(5, ...)` enforces a minimum duration of 5 minutes.

---

## Pipeline Position of Scoping & Normalization

```
NER Model Output
    │
    ▼
Entity Aliasing     ← "person" → "collaborator"
    │
    ▼
Entity Scoping      ← drop "collaborator" for "scheduling_show" intent
    │
    ▼
Date Resolution     ← Duckling: "Friday" → "2025-05-02"
    │
    ▼
Value Normalization ← "urgent" → "high"
    │
    ▼
Handler (DB operation)
```

---

## Summary Table

| Concept | Role in EVA |
|---|---|
| Entity scoping | Filters entities to intent-specific allowed keys |
| Entity aliasing | Normalizes model-variant key names to canonical keys |
| Value canonicalization | Maps user synonyms to DB-safe priority/status values |
| Weekday normalization | Extracts clean weekday names from noisy NER output |
| Duration normalization | Converts "2 hours" → 120 (integer minutes) |
| Canonical values | Single source of truth for DB storage and queries |

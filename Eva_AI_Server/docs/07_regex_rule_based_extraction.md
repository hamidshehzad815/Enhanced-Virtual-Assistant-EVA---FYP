# 🔧 Regex-Based Rule-Driven Entity Extraction — EVA AI Server

## What Is Rule-Based NLP?

**Rule-based NLP** uses handcrafted patterns (regular expressions, keyword lists, grammar rules) to extract information from text — as opposed to ML models that learn patterns from data.

EVA uses rule-based extraction as a **fallback** to the NER model. This hybrid approach exploits the strengths of both methods:

| Approach | Strengths | Weaknesses |
|---|---|---|
| ML (NER model) | Handles varied phrasing, context-sensitive | Can miss rare patterns; needs training data |
| Rule-based (Regex) | Deterministic, zero training needed | Brittle to phrasing variations |

---

## Where Rule-Based Extraction Is Used in EVA

### 1. `delete_entity_fallback.py`
Extracts fields relevant to `scheduling_delete` when NER misses them:
- `task_name`, `date`, `priority`, `status`

### 2. `update_entity_fallback.py`
Extracts fields relevant to `scheduling_update` when NER misses them:
- `task_name`, `new_title`, `date`, `new_date`, `new_time`, `new_priority`, `new_status`, `new_duration`

### 3. `context/context_manager.py`
Rule-based classification for:
- Cancel intent detection (keyword set)
- Yes/No reply classification (keyword set)
- Number selection parsing (regex digit extraction)

### 4. `pipeline/entity_scoper.py`
Regex for extracting weekday names from potential date values.

---

## Regular Expressions: Core Concepts

### Basic Syntax Used in EVA

| Pattern | Meaning | Example Match |
|---|---|---|
| `\b` | Word boundary | `\bdelete\b` matches "delete" but not "undelete" |
| `\d{4}-\d{2}-\d{2}` | ISO date | `2025-05-01` |
| `(?i)` / `re.IGNORECASE` | Case-insensitive | Matches "Friday" and "friday" |
| `(a\|b\|c)` | Alternation (OR) | `(yes\|yeah\|yep)` |
| `(.+?)` | Non-greedy capture | Minimal match |
| `\s+` | Whitespace | Matches one or more spaces |
| `^...$` | Start/end of string | Full-string match |
| `re.search()` | Find first match anywhere in string | |
| `re.sub()` | Replace matches with a string | |

---

## Pattern Examples from EVA

### Date Patterns (`delete_entity_fallback.py`)

```python
_ISO_DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")

_RELATIVE_DATE_PATTERN = re.compile(
    r"\b(today|tomorrow|yesterday|tonight)\b",
    flags=re.IGNORECASE,
)

_DAY_OF_WEEK_PATTERN = re.compile(
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    flags=re.IGNORECASE,
)
```

Priority in extraction: ISO date > relative keyword > day of week.

### Structural Update Patterns (`update_entity_fallback.py`)

```python
# "rename physics exam to final physics exam"
rename_match = re.search(
    r"\brename\s+(.+?)\s+to\s+(.+)$",
    raw_text,
    flags=re.IGNORECASE,
)

# "mark my standup as done"
mark_match = re.search(
    rf"\bmark\s+(.+?)\s+as\s+({_STATUS_VALUE_TOKEN})\b",
    raw_text,
    flags=re.IGNORECASE,
)

# "reschedule meeting on Monday to Friday"
move_match = re.search(
    r"\b(?:reschedule|move)\s+(.+?)\s+to\s+(.+)$",
    raw_text,
    flags=re.IGNORECASE,
)
```

Each pattern captures **named groups** for the specific entities needed.

### Dynamic Regex Construction (`task_value_normalizer.py`)

EVA **dynamically builds regex alternations** from value lists:

```python
def build_value_regex(values: Iterable[str]) -> str:
    patterns = []
    for raw in values:
        normalized = normalize(raw)
        parts = [re.escape(part) for part in normalized.split()]
        patterns.append(r"[\s_-]+".join(parts))
    patterns.sort(key=len, reverse=True)   # longer phrases first
    return "|".join(patterns)
```

This turns `["high", "urgent", "critical", "in progress", "in-progress"]` into:
```
in[\s_-]+progress|in[\s_-]+progress|critical|urgent|high
```

**Longer phrases are matched first** to avoid partial matches (e.g., "in progress" before "progress").

---

## Stopword Filtering

The delete fallback removes common irrelevant words before extracting task names:

```python
_TASK_NAME_STOPWORDS = {
    "all", "of", "them", "my", "the", "a", "an",
    "task", "tasks", "every", "everything", "please", "just",
}
```

```python
tokens = [
    token
    for token in candidate.split()
    if token.lower() not in _TASK_NAME_STOPWORDS
]
```

**Stopwords** are common words (articles, pronouns, fillers) that carry no meaningful entity information.

---

## Fallback Application Strategy

The fallback is always applied **after** the NER model and **only fills gaps**:

```python
# In ner.py:
if intent_hint == "scheduling_delete":
    fallback_entities = extract_delete_entities_fallback(text)
    for key, value in fallback_entities.items():
        current_value = entities.get(key)
        if current_value in (None, "", [], {}):  # only if model missed it
            entities[key] = value
```

This ensures:
- ML predictions are **never overridden** by deterministic rules
- Rules only **augment** the model's output

---

## Salutation Stripping (main.py)

Before classification, EVA strips common greetings so they don't confuse the model:

```python
_SALUTATION_PATTERN = re.compile(
    r"^\s*(?:(?:hey|hi|hello|salam|assalamualaikum|aoa|yo|ok|okay)\b[\s,!:.-]*)*"
    r"(?:eva\b[\s,!:.-]*)*",
    flags=re.IGNORECASE,
)

def _nlu_text_for_classification(message: str) -> str:
    candidate = _SALUTATION_PATTERN.sub("", original).strip()
    if candidate and _looks_like_command_text(candidate):
        return candidate   # stripped version (better for classifier)
    return original        # keep original if no command follows
```

*"Hey eva, add physics exam on Friday"* → classifier sees *"add physics exam on friday"*

---

## Summary Table

| Concept | Role in EVA |
|---|---|
| Regular expressions | Pattern-based text matching and extraction |
| Fallback extraction | Supplements NER model for missed entities |
| Stopwords | Common words removed before entity extraction |
| Dynamic regex building | Constructs alternation patterns from value lists |
| Structural patterns | Intent-specific patterns (rename, mark, reschedule) |
| Salutation stripping | Removes greetings before classification |
| Hybrid ML + Rules | ML output is primary; rules fill gaps only |

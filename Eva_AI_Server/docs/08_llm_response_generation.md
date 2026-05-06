# 🤖 LLM Response Generation with Gemini — EVA AI Server

## What Is a Large Language Model (LLM)?

A **Large Language Model (LLM)** is a deep learning model trained on massive text corpora to predict and generate human-like text. Unlike the smaller task-specific models (classifiers, NER), LLMs are:

- **Generative**: They produce free-form text rather than fixed labels
- **Instruction-following**: Modern LLMs can follow natural language instructions ("respond like a helpful assistant")
- **Context-aware**: They can incorporate conversation history, user preferences, and structured data into their responses

Examples: GPT-4, Claude, **Gemini** (Google).

---

## How EVA Uses Gemini

EVA uses **Google Gemini** (accessed via the `google-generativeai` Python SDK) exclusively for **generating final natural language responses**. It is NOT used for classification or entity extraction — those are handled by the smaller, faster fine-tuned BERT models.

### Role Split

| Task | Technology | Why |
|---|---|---|
| Input type classification | Fine-tuned BERT (Classifier 1) | Fast, accurate on trained classes |
| Intent classification | Fine-tuned BERT (Classifier 2) | Fast, accurate on trained intents |
| Entity extraction | Fine-tuned BERT (NER model) | Efficient token-level labeling |
| Date/time parsing | Duckling (rule-based) | Deterministic, timezone-aware |
| Natural response generation | **Gemini (LLM)** | Fluent, personalized conversational replies |

---

## The `gemini.py` Service

The `GeminiService` class in `services/gemini.py` manages all interactions with the Gemini API.

### Key Method: `generate_reply()`

```python
def generate_reply(
    self,
    action_context: dict,   # Structured payload describing what happened
    user_name: str,          # For personalized responses ("Great, Ahmed!")
    history: list,           # Recent conversation history
) -> str:
```

### What Goes Into the Prompt

Gemini receives a structured **system prompt** that tells it:
- Its role (EVA, a smart assistant)
- The action that was taken (e.g., `{"action": "scheduling_add", "task": {...}}`)
- The user's name
- Recent conversation history (for context)

The LLM then generates a natural, context-appropriate response.

---

## Action Context Object

Instead of sending raw text to Gemini, EVA sends a **structured action context** — a JSON-like dictionary describing the outcome of the pipeline:

```python
# Example: After successfully adding a task
payload = {
    "action": "scheduling_add_success",
    "task": {
        "title": "Physics Exam",
        "due_datetime": "2025-05-02T15:00:00",
        "priority": "high"
    }
}
reply = gemini_service.generate_reply(payload, user_name="Ahmed", history=history)
```

Other example action types:
| Action Key | When |
|---|---|
| `"scheduling_add_success"` | Task added successfully |
| `"scheduling_delete_success"` | Task deleted |
| `"scheduling_show_empty"` | No tasks found for the query |
| `"entity_missing_date"` | Need to ask for the date |
| `"pending_yes_no_prompt"` | Asking for confirmation |
| `"model_unavailable"` | NER/classifier couldn't load |
| `"out_of_scope"` | Request is beyond EVA's capabilities |

---

## Conversation History

Gemini receives recent **conversation history** to maintain coherence across turns:

```python
history = [
    {"role": "user", "content": "Add physics exam on Friday"},
    {"role": "assistant", "content": "Added! Physics Exam on Friday at 3PM with high priority."},
    {"role": "user", "content": "Actually change the time to 4pm"},
]
```

This allows Gemini to generate contextually appropriate replies like:
> *"Done! I've updated Physics Exam to 4PM on Friday."*
> 
rather than a generic response that doesn't reference the previous exchange.

---

## The `_safe_reply()` Wrapper

EVA wraps all Gemini calls in a safety wrapper:

```python
def _safe_reply(
    action: str,
    user_name: Optional[str] = None,
    history=None,
    action_context=None,
) -> str:
    try:
        payload = {"action": action}
        if action_context:
            payload.update(action_context)
        return gemini_service.generate_reply(payload, user_name, history or [])
    except Exception:
        return "I am still here, but I could not process that clearly. Please try again."
```

If Gemini fails for any reason (network error, API quota, etc.), a **hardcoded fallback message** is returned rather than crashing. This ensures the API always returns a response.

---

## Prompt Engineering Concepts

### System Prompt
A **system prompt** is text given to an LLM before the conversation that defines its behavior, persona, and constraints. EVA's system prompt tells Gemini:
- It is EVA, a smart personal assistant
- It should be concise and friendly
- It should use the user's name when available
- It should only reference information provided in the action context

### Few-Shot Examples
Good system prompts often include **examples** of desired input/output pairs. This helps the LLM understand the expected response style without extensive fine-tuning.

### Grounding with Structured Data
By passing a JSON action context rather than free text, EVA **grounds** the LLM's response in factual data. This prevents hallucination (making up task details) because the LLM is told exactly what happened:

```
Action: scheduling_add_success
Task: { "title": "Physics Exam", "date": "Friday, 02 May 2025", "time": "3:00 PM" }
```

The LLM can only refer to data in this payload.

---

## Comparison: Fine-Tuned Models vs. LLM

| Aspect | Fine-tuned BERT (Clf/NER) | Gemini LLM |
|---|---|---|
| Task | Classification / labeling | Free-form generation |
| Speed | Very fast (~10-50ms) | Slower (API call, ~200-800ms) |
| Output | Fixed labels / spans | Natural language text |
| Control | Deterministic (same input → same output) | Stochastic (varies slightly) |
| Cost | Free (local model) | API cost per call |
| Hallucination risk | None (labels only) | Must be controlled via grounding |

---

## Summary Table

| Concept | Role in EVA |
|---|---|
| LLM (Large Language Model) | Gemini generates natural language responses |
| Action context | Structured payload tells Gemini what happened |
| Conversation history | Enables contextually coherent multi-turn replies |
| System prompt | Defines Gemini's persona and response style |
| Grounding | Prevents hallucination by providing structured facts |
| `_safe_reply()` | Error wrapper; returns fallback if Gemini fails |
| Gemini SDK | `google-generativeai` Python library for API access |

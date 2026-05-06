# 💬 Multi-Turn Dialogue & Conversational Context — EVA AI Server

## What Is Multi-Turn Dialogue?

Most NLP tasks are single-turn: one input → one output. **Multi-turn dialogue** involves maintaining **state across multiple conversational exchanges**. The system must remember what was said previously in order to respond intelligently.

Example multi-turn flow:
```
User:   "Delete my meeting tomorrow"
EVA:    "I found 3 meetings on Friday. Which one? (1) Standup, (2) Planning, (3) Sync"
User:   "2"
EVA:    "Deleted Planning meeting."
```

After the first exchange, EVA stores *pending context* (the list of tasks found, the intent, the next expected reply type). On the second message, it retrieves that context and acts on it.

---

## Redis as a Context Store

EVA uses **Redis** — an in-memory key-value store — to persist conversational context between requests. This is necessary because:

1. The server is **stateless** per HTTP request (FastAPI)
2. Multiple users interact simultaneously
3. Context must survive across different HTTP requests from the same user

### Key Design

```
Key:   "context:{user_id}"
Value: JSON-serialized context object
TTL:   300 seconds (5 minutes — configurable via settings.CONTEXT_TTL)
```

If the user doesn't respond within 5 minutes, the context **expires automatically** (Redis TTL). This prevents stale state from lingering indefinitely.

---

## Context Data Structure

A pending context object stored in Redis:

```json
{
  "pending_action": {
    "intent": "scheduling_delete",
    "stage": "identify",
    "entities": { "date": "2025-05-02" },
    "task_ids": ["abc123", "def456", "ghi789"]
  },
  "expected_response": "number",
  "missing_entity": null
}
```

| Field | Purpose |
|---|---|
| `pending_action.intent` | What the user was trying to do |
| `pending_action.stage` | Where in the multi-step flow we are |
| `pending_action.entities` | Entities gathered so far |
| `pending_action.task_ids` | List of matched task IDs (for disambiguation) |
| `expected_response` | What type of reply to expect: `"yes_no"`, `"free_text"`, `"number"` |
| `missing_entity` | Which entity the system is waiting for (e.g., `"date"`) |

---

## Context Manager Functions (`context_manager.py`)

### `is_cancel(text)`
Detects user intent to abandon the current flow:
```python
_CANCEL_KEYWORDS = {"cancel", "stop", "abort", "never mind", "forget it", "discard", ...}
```
If detected → Redis context deleted → user gets a cancellation confirmation.

### `handle_yes_no_reply(text)`
Classifies a reply as `"yes"`, `"no"`, or `"invalid"` using keyword sets:
```python
_YES_KEYWORDS = {"yes", "yeah", "yep", "sure", "go ahead", "ok", "okay", ...}
_NO_KEYWORDS  = {"no", "nope", "nah", "reject"}
```
This is a **rule-based classifier** (no ML) — simple keyword lookup is sufficient for binary confirmation.

### `handle_number_delete(text, context)`
Parses a numeric choice (e.g., "2") against a list of `task_ids` stored in context:
```python
match = re.search(r"\b(\d+)\b", normalized)
selected_index = int(match.group(1))
return task_ids[selected_index - 1]
```
Also handles "all" to delete all listed tasks.

### `handle_free_text_reply(user_id, context, reply)`
Merges a free-text reply into pending entities:
```python
if missing_entity:
    merged_entities[missing_entity] = cleaned_reply
else:
    # Intent-specific fallback assignment
    merged_entities["free_text_reply"] = cleaned_reply
```

---

## Expected Response Types

| `expected_response` | Meaning | Example |
|---|---|---|
| `"yes_no"` | Waiting for a binary confirmation | *"Are you sure you want to delete?"* |
| `"free_text"` | Waiting for an open-ended reply | *"What's the task name?"* |
| `"number"` | Waiting for a numeric selection from a list | *"Which task? (1) ... (2) ..."* |

The main handler in `main.py` branches on this value to route the reply correctly.

---

## The Multi-Turn Flow in `main.py`

```python
pending_context = fetched.context      # retrieved from Redis

if pending_context:
    if is_cancel(processed["processed"]):
        await redis_client.delete_context(payload.user_id)
        return { "response_text": "Cancelled." }

    if expected_response == "free_text":
        merged_entities = await handle_free_text_reply(...)
        routed_result = await route_intent(routed_intent, merged_entities, context)
        return { ..., "context_handled": True }

    if expected_response == "yes_no":
        yes_no_value = handle_yes_no_reply(processed["processed"])
        # Route based on yes or no...
```

The key principle: **pending context always takes priority** over fresh classification. If the user is mid-flow, EVA handles their reply in context rather than re-running the full NLU pipeline.

---

## `should_block_new_command()`

One subtle edge case: what if a user sends a new command while mid-confirmation?

```
User:  "Delete my exam"
EVA:   "Found: (1) Math exam, (2) Physics exam. Which one?"
User:  "Add lunch meeting tomorrow"     ← new command interrupts flow
```

EVA detects that model 1 classified this as `"command"` and blocks it:

```python
def should_block_new_command(model1_label: str) -> bool:
    return model1_label in {"command", "multiple_command"}
```

The user gets a reminder to answer the pending question first.

---

## `_should_assign_directly()`

For date/time replies, EVA avoids storing a full command sentence as a date value:

```python
def _should_assign_directly(missing_entity: str, reply: str) -> bool:
    if missing_entity in {"date", "time"} and _looks_like_full_command(reply):
        return False   # Don't store "add meeting tomorrow" as a date value
    return True
```

This prevents the system from setting `date = "add meeting on friday"` when the user types a new command instead of answering "when?".

---

## Redis Operations

| Operation | When Used |
|---|---|
| `set_context(user_id, data, ttl)` | After asking a follow-up question |
| `get_context(user_id)` | At start of every `/process` request |
| `delete_context(user_id)` | After context is resolved (or on cancel) |

Context is **always deleted after resolution** to prevent stale state from affecting future conversations.

---

## Summary Table

| Concept | Role in EVA |
|---|---|
| Multi-turn dialogue | Conversational state spanning multiple exchanges |
| Redis | In-memory context store (per-user, with TTL) |
| TTL (Time-To-Live) | Auto-expires context after 5 minutes of inactivity |
| `expected_response` | Signals what type of reply the system awaits |
| `context_handled` flag | Response field indicating a pending context was resolved |
| Cancel detection | Keyword-based rule to abort pending flows |
| Yes/no classification | Rule-based binary classifier for confirmation replies |
| Block new commands | Prevents command interruption during pending flows |

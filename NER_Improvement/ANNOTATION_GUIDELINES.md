# EVA NER — Annotation Guidelines

Strict rules for template generation and manual examples. **Inconsistency here causes boundary confusion and fake F1.**

## General

- One whitespace token = one label.
- `with`, `my`, `the`, `a`, `for`, `on`, `at` are **O** unless part of a slot value.
- Never tag filler pronouns: `my`, `me`, `our`.

## Scheduling

### `task_name`
- Core noun phrase only: `physics exam`, `Machine Learning Model Training`.
- **Do not** include: `with Sara`, `for tomorrow`, priority words.
- Short names allowed: `exam`, `quiz`, `viva`, `DA`.

### `person`
- Collaborator name only: `Usama`, `Ahmed`.
- `with` before person stays **O**.

### `date` / `time` / `new_date` / `new_time`
- Use `date` for existing schedule; `new_date` for rescheduled target.
- `today`, `tomorrow`, `Monday`, `5pm` are valid slot fills.
- Compact order allowed: `add exam with Usama today 5pm` (no `on` required).

### `new_status`
- Status **value token(s)** only: `complete`, `done`, `pending`, `in progress`.
- Verb-only templates (`complete {task_name}`) tag **task_name only** — status is implied, not extracted.

## Learning

### `topic` / `subtopic`
- `Python` + `basics` / `oop` as separate entities when both present.
- `roadmap`, `plan`, `session` stay **O** unless part of a defined slot.

### `start_date` / `duration`
- `today`, `60days`, `2 weeks` — use slot, not hardcoded in template without `{start_date}` / `{duration}`.

## Negative examples (~12% of training set)

- All-O: `thanks eva`, `show my tasks` (no task_name).
- Partial-O: `add my task for tomorrow` → only `B-date`.
- Must teach model **when not to fire**.

## Literal entities in templates

When status/date words are fixed in template text (not `{slots}`), use `literal_entities`:

```json
{
  "text": "mark {task_name} complete",
  "entities": ["task_name", "new_status"],
  "literal_entities": { "new_status": "complete" }
}
```

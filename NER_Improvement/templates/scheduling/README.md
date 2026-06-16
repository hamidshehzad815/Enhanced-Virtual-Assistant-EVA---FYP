# Scheduling NER — Sentence Templates

Phase 2, Step 1: template definitions for **scheduling_add**, **scheduling_delete**, **scheduling_update**, **scheduling_show**, and **behavioral**.

## Slot notation

| Slot | Entity label | Example fill (from `config/vocab.json`) |
|------|--------------|----------------------------------------|
| `{task_name}` | `task_name` | physics exam, morning standup |
| `{date}` | `date` | Monday, tomorrow, 2025-05-01 |
| `{time}` | `time` | 5PM, 10:30am |
| `{priority}` | `priority` | high, urgent, low |
| `{status}` | `status` | pending, complete, in progress |
| `{duration}` | `duration` | 2 hours, 30 minutes |
| `{person}` | `person` | Ahmed, Sara |
| `{day}` | `day` | monday, friday |
| `{new_taskname}` | `new_taskname` | updated exam title |
| `{new_date}` | `new_date` | Tuesday, next week |
| `{new_time}` | `new_time` | 6PM |
| `{new_priority}` | `new_priority` | high |
| `{new_status}` | `new_status` | complete |
| `{new_duration}` | `new_duration` | 1 hour |

## Files

| File | Intent | Template groups |
|------|--------|-----------------|
| `scheduling_add.json` | scheduling_add | 20+ groups, 200+ templates |
| `scheduling_delete.json` | scheduling_delete | 15+ groups, 150+ templates |
| `scheduling_update.json` | scheduling_update | 25+ groups, 250+ templates |
| `scheduling_show.json` | scheduling_show | 12+ groups, 120+ templates |
| `behavioral.json` | behavioral | 5+ groups, 50+ templates |

## JSON shape (each file)

```json
{
  "intent": "scheduling_add",
  "version": "1.0.0",
  "groups": [
    {
      "id": "core_direct",
      "label": "Direct imperative",
      "styles": ["direct"],
      "templates": [
        {
          "text": "add {task_name} on {date} at {time}",
          "entities": ["task_name", "date", "time"]
        }
      ]
    }
  ]
}
```

## Styles used across groups

- **direct** — plain command (`add physics exam on Monday`)
- **polite** — please / kindly / can you
- **question** — can you / could you / what about
- **entity_first** — entities before verb (`physics exam Monday 5PM add`)
- **implicit** — no action verb (`physics exam Monday 5PM`)
- **confirmation** — ends with ok / thanks / right
- **casual** — EVA, hey, u, gonna, need to
- **reminder** — remind me, don't forget
- **bulk** — all tasks / clear schedule (delete & show)

## Regenerate JSON

Source definitions live in `scheduling_templates.py`. To refresh JSON after edits:

```bash
python scheduling_templates.py
```

*(Dataset generator comes in Phase 2 Step 5 — not built yet.)*

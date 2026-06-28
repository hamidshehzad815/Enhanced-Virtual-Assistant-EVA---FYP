# Learning NER — Sentence Templates

Phase 2, Step 1: template definitions for **learning_create**, **learning_update**, **learning_delete** only.

**Not supported:** chat commands to show learning progress — use the app **Roadmap** tab (`GET /api/roadmaps/*`).

## Slot notation

| Slot | Entity label | Example fill (from `config/vocab.json`) |
|------|--------------|----------------------------------------|
| `{topic}` | `topic` | Python, JavaScript, MySQL |
| `{subtopic}` | `subtopic` | basics, intermediate, object oriented programming |
| `{start_date}` | `start_date` | Monday, tomorrow, next week |
| `{date}` | `date` | Friday, today, 2025-06-01 |
| `{duration}` | `duration` | 2 weeks, 1 month, 30 days |
| `{person}` | `person` | Ahmed, Sara |

## Files

| File | Intent | Template groups |
|------|--------|-----------------|
| `learning_create.json` | learning_create | 18+ groups, 180+ templates |
| `learning_update.json` | learning_update | 12+ groups, 100+ templates |
| `learning_delete.json` | learning_delete | 10+ groups, 80+ templates |

## JSON shape (each file)

```json
{
  "intent": "learning_create",
  "version": "1.0.0",
  "groups": [
    {
      "id": "core_topic_only",
      "label": "Topic only",
      "styles": ["direct"],
      "templates": [
        {
          "text": "learn {topic}",
          "entities": ["topic"]
        }
      ]
    }
  ]
}
```

## Styles used across groups

- **direct** — plain command (`learn Python`, `create Python roadmap`)
- **polite** — please / kindly / can you
- **question** — can you / could you / what about
- **entity_first** — entities before verb (`Python basics learn`)
- **implicit** — no action verb (`Python basics 2 weeks`)
- **confirmation** — ends with ok / thanks / right
- **casual** — EVA, hey, u, gonna, need to
- **roadmap** — roadmap / study plan / learning plan phrasing (create)

## Regenerate JSON

Source definitions live in `learning_templates.py`. To refresh JSON after edits:

```bash
python learning_templates.py
```

*(Dataset generator comes in Phase 2 Step 5 — not built yet.)*

# EVA NER — Entity Reference

Source: `Eva_AI_Server/models/ner_model/config.json`, `Eva_AI_Server/models/learning_ner/config.json`, `Eva_AI_Server/pipeline/entity_scoper.py`

EVA uses **two separate NER models**:

| Model | Path | Used for |
|-------|------|----------|
| **Scheduling NER** | `models/ner_model` | scheduling + behavioral intents |
| **Learning NER** | `models/learning_ner` | learning intents |

Both use **BIO tagging**: `O`, `B-<entity>`, `I-<entity>`.

---

## 1. Scheduling NER — Entity Types

**14 entity types** (from trained model labels):

| Entity (model label) | Canonical key (after scoping) | Description | Example values |
|----------------------|-------------------------------|-------------|----------------|
| `task_name` | `task_name` | Task or event name | `"physics exam"`, `"morning standup"` |
| `date` | `date` | Schedule date | `"Monday"`, `"tomorrow"`, `"2025-05-01"` |
| `time` | `time` | Schedule time | `"5PM"`, `"10:30am"` |
| `priority` | `priority` | Task priority | `"high"`, `"low"`, `"urgent"` |
| `status` | `status` | Task status filter | `"pending"`, `"complete"`, `"ongoing"` |
| `duration` | `duration` | Task duration | `"2 hours"`, `"30 minutes"` |
| `person` | `collaborator` | Collaborator name | `"Ahmed"`, `"Sara"` |
| `day` | `day` | Weekday (behavioral) | `"monday"`, `"friday"` |
| `new_taskname` | `new_title` | Updated task name | `"updated exam title"` |
| `new_date` | `new_date` | Updated date | `"Tuesday"`, `"next week"` |
| `new_time` | `new_time` | Updated time | `"6PM"` |
| `new_priority` | `new_priority` | Updated priority | `"high"` |
| `new_status` | `new_status` | Updated status | `"complete"` |
| `new_duration` | `new_duration` | Updated duration | `"1 hour"` |

### Scheduling NER — BIO Labels (29 total)

```
O
B-date,           I-date
B-day,            I-day
B-duration,       I-duration
B-new_date,       I-new_date
B-new_duration,   I-new_duration
B-new_priority,   I-new_priority
B-new_status,     I-new_status
B-new_taskname,   I-new_taskname
B-new_time,       I-new_time
B-person,         I-person
B-priority,       I-priority
B-status,         I-status
B-task_name,      I-task_name
B-time,           I-time
```

---

## 2. Learning NER — Entity Types

**6 entity types** (from trained model labels):

| Entity (model label) | Canonical key (after scoping) | Description | Example values |
|----------------------|-------------------------------|-------------|----------------|
| `topic` | `topic` | Learning subject / language | `"Python"`, `"JavaScript"`, `"MySQL"` |
| `subtopic` | `subtopic` | Roadmap subtopic / level | `"basics"`, `"oop"`, `"intermediate"` |
| `start_date` | `start_date` | Plan start date | `"Monday"`, `"tomorrow"` |
| `date` | `date` | Generic date (update/delete) | `"Friday"`, `"next week"` |
| `duration` | `duration` | Study duration | `"2 weeks"`, `"3 months"` |
| `person` | `person` | Collaborator (learning create) | `"Ahmed"` |

### Learning NER — BIO Labels (13 total)

```
O
B-date,        I-date
B-duration,    I-duration
B-person,      I-person
B-start_date,  I-start_date
B-subtopic,    I-subtopic
B-topic,       I-topic
```

---

## 3. Entities Per Command (Intent Scope)

After NER extraction, `entity_scoper.py` keeps only entities valid for the detected intent.

### Scheduling commands (Scheduling NER)

| Intent | Allowed entities |
|--------|------------------|
| `scheduling_add` | `task_name`, `date`, `time`, `priority`, `duration`, `collaborator` |
| `scheduling_delete` | `task_name`, `date`, `priority`, `status` |
| `scheduling_update` | `task_name`, `date`, `priority`, `status`, `new_title`, `new_date`, `new_time`, `new_priority`, `new_status`, `new_duration` |
| `scheduling_show` | `date`, `priority`, `status`, `task_name` |
| `behavioral` | `day` |

### Learning commands (Learning NER)

| Intent | Allowed entities |
|--------|------------------|
| `learning_create` | `topic`, `subtopic`, `start_date`, `duration`, `person` |
| `learning_update` | `topic`, `subtopic`, `date` |
| `learning_delete` | `topic`, `subtopic` |

Note: **`learning_show` is disabled** in `Eva_AI_Server/handlers/router.py` — not included in NER training data.

---

## 4. Key Aliases (Model Output → Canonical)

Applied in `entity_scoper.py` before intent filtering:

| Model may emit | Normalized to | Used in |
|----------------|---------------|---------|
| `person`, `person_name`, `people` | `collaborator` | scheduling intents |
| `new_taskname`, `new_task_name` | `new_title` | scheduling_update |
| `new_scheduled_date`, `new_start_date` | `new_date` | scheduling_update |
| `subject` | `task_name` | scheduling |
| `subject` | `topic` | learning_create, learning_delete, learning_update |
| `date` | `start_date` | learning_create only |

---

## 5. Required Entities Per Handler

Entities NER should extract; handlers ask user if missing.

| Intent | Required | Optional |
|--------|----------|----------|
| `scheduling_add` | `task_name`, `date`, `time` | `priority`, `duration`, `collaborator` |
| `scheduling_delete` | at least one filter | `task_name`, `date`, `priority`, `status` |
| `scheduling_update` | `task_name` + at least one `new_*` field | `date`, `priority`, `status` |
| `scheduling_show` | none (all filters optional) | `date`, `priority`, `status`, `task_name` |
| `behavioral` | `day` | — |
| `learning_create` | `topic` | `subtopic`, `start_date`, `duration`, `person` |
| `learning_update` | `topic` | `subtopic`, `date` |
| `learning_delete` | `topic` | `subtopic` |

---

## 6. Fixed Vocabularies (for fallback / validation)

### Learning topics (`SUPPORTED_TOPICS`)

Python, JavaScript, TypeScript, Java, C#, C++, Go, Rust, PHP, Kotlin, Swift, Ruby, Dart, C, Oracle, MySQL, Microsoft SQL Server, PostgreSQL, MongoDB, SQL

*(Plus aliases: `js`, `py`, `mongo`, `postgres`, etc. — see `utils/learning_utils.py`)*

### Priority values

Canonical: `low`, `medium`, `high`  
User variants: `urgent`, `critical`, `asap`, `normal`, etc.

### Status values

Canonical: `pending`, `ongoing`, `complete`  
User variants: `done`, `completed`, `in progress`, `active`, etc.

### Days (date / day / behavioral)

`monday` … `sunday`, plus relative: `today`, `tomorrow`, `yesterday`, `tonight`

---

## 7. Summary — All Unique Entities

### Scheduling NER (train & tag these)

```
task_name, date, time, priority, status, duration, person, day,
new_taskname, new_date, new_time, new_priority, new_status, new_duration
```

### Learning NER (train & tag these)

```
topic, subtopic, start_date, date, duration, person
```

### Combined unique set (both models)

```
task_name, date, time, priority, status, duration, person, day,
new_taskname, new_date, new_time, new_priority, new_status, new_duration,
topic, subtopic, start_date
```

Note: `date` and `person` appear in both models but serve different intents.  
Note: `day` exists only in scheduling NER (behavioral commands).

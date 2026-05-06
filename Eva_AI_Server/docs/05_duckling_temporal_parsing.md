# 📅 Temporal Expression Parsing with Duckling — EVA AI Server

## What Is Duckling?

**Duckling** is an open-source NLP library developed by **Meta (Facebook AI)**. It specializes in parsing **temporal expressions** — natural language phrases that refer to dates, times, and durations — and converting them into precise, structured values.

It is written in Haskell and runs as a standalone HTTP microservice.

### Examples

| Natural Language | Duckling Output |
|---|---|
| *"tomorrow"* | `2025-05-02T00:00:00.000+00:00` |
| *"next friday"* | `2025-05-09T00:00:00.000+00:00` |
| *"3pm"* | `2025-05-01T15:00:00.000+00:00` |
| *"2 hours"* | `{ "value": 2, "unit": "hour" }` |
| *"this week"* | interval from Monday → Sunday |

---

## Why Not Just Use the NER Model for Dates?

The NER model extracts the **text span** ("Friday", "3pm") but does **not** know what actual calendar date "Friday" refers to — it depends on:
- The **current date** (today is...)
- The **user's timezone** (Pakistan Standard Time vs. UTC)

Duckling solves exactly this: it resolves **relative expressions** like "tomorrow", "next week", or "in 2 days" into absolute ISO timestamps.

---

## How EVA Integrates Duckling

### Step 1: NER extracts raw string values

```json
{ "date": "Friday", "time": "3pm" }
```

### Step 2: `date_resolver.py` sends each value to Duckling

```python
async def resolve_all(entities: Dict[str, Any], timezone: str = "UTC") -> Dict[str, Any]:
    if "date" in resolved:
        resolved["date"] = await _resolve_value_list(
            resolved["date"],
            _resolve_single_date,
            normalized_timezone,
        )
    if "time" in resolved:
        resolved["time"] = await _resolve_value_list(
            resolved["time"],
            _resolve_single_time,
            normalized_timezone,
        )
    if "duration" in resolved:
        resolved["duration"] = await _resolve_value_list(
            resolved["duration"],
            _resolve_single_duration,
        )
```

### Step 3: Duckling returns a structured ISO datetime

```json
{ "date": "2025-05-02T00:00:00.000+05:00" }
```

---

## Timezone Handling

A critical challenge: Duckling must know the user's **timezone** to correctly resolve relative expressions.

- *"tomorrow at 9am"* in Pakistan (UTC+5) refers to a different UTC time than in New York (UTC-4)

EVA passes the resolved timezone from user settings:

```python
user_timezone = resolve_timezone_name((fetched.user or {}).get("timezone"))
resolved_entities = await resolve_all(scoped_entities, timezone=user_timezone)
```

`resolve_timezone_name()` normalizes common timezone aliases:
- `"PKT"` → `"Asia/Karachi"`
- `"UTC"` → `"UTC"`

---

## Duckling Service Communication (`services/duckling.py`)

Duckling runs as an HTTP server (typically on `localhost:8000`). EVA's `duckling_client` sends HTTP POST requests:

```
POST http://localhost:8000/parse
Body: { "locale": "en_US", "text": "Friday", "tz": "Asia/Karachi" }
Response: [{ "body": "Friday", "value": { "value": "2025-05-02T00:00:00.000+05:00", "grain": "day" } }]
```

The **grain** field tells us the precision:
- `"day"` → the expression refers to a full day
- `"hour"` / `"minute"` → time-level precision
- `"week"` / `"month"` → broader range

---

## Date Range Building (`utils/date_utils.py`)

For "show tasks" queries, EVA doesn't just need a point in time — it needs a **date window** (start + end UTC timestamps). The `build_date_range()` function uses the Duckling result and grain to compute these:

```python
if grain == "day":
    local_start = datetime.combine(local_base.date(), time.min, tzinfo=zone)
    local_end   = datetime.combine(local_base.date(), time.max, tzinfo=zone)
elif grain == "week":
    week_start_date = ...
    week_end_date   = week_start_date + 6 days
elif grain == "month":
    month_start = local_base.date().replace(day=1)
    last_day = monthrange(month_start.year, month_start.month)[1]
```

All ranges are then converted to **UTC-naive datetimes** for database storage:

```python
start_utc = local_start.astimezone(timezone.utc).replace(tzinfo=None)
end_utc   = local_end.astimezone(timezone.utc).replace(tzinfo=None)
```

---

## Duration Parsing

Duckling also resolves duration expressions:
- *"2 hours"* → `{ "value": 2, "unit": "hour" }` → 120 minutes
- *"30 minutes"* → `{ "value": 30, "unit": "minute" }` → 30 minutes

EVA uses durations for task scheduling (how long an event takes).

---

## Fallback When Duckling Is Unavailable

If Duckling fails to parse a value, `resolve_all()` returns the **original raw string** rather than failing:

```python
resolved = await duckling_client.resolve_date(value, timezone=timezone)
return resolved or value    # fall back to raw string if Duckling fails
```

This makes the pipeline resilient to Duckling downtime — the raw entity value is preserved and can sometimes still be used downstream.

---

## Local Datetime Presentation (`convert_tasks_to_local`)

When returning tasks to the user, stored UTC datetimes are converted back to the user's local time for display:

```python
local_dt = utc_naive_to_local(row.get("due_datetime"), user_timezone)
row["local_datetime_str"] = local_dt.strftime("%A %I:%M %p")   # e.g., "Friday 03:00 PM"
row["local_date_str"]     = local_dt.strftime("%A, %d %b %Y")  # e.g., "Friday, 02 May 2025"
row["local_time_str"]     = local_dt.strftime("%I:%M %p")       # e.g., "3:00 PM"
```

---

## Summary Table

| Concept | Role in EVA |
|---|---|
| Duckling | Meta's temporal parser — converts NL time expressions to ISO dates |
| Temporal resolution | Turns "Friday" into `2025-05-02T00:00:00` |
| Timezone-aware parsing | Resolves relative times in user's local timezone |
| Grain | Precision of extracted time (day / week / month / hour / minute) |
| Date range building | Computes start/end UTC bounds for "show tasks" window queries |
| UTC storage | All datetimes stored in UTC; converted to local on read |
| Duckling fallback | Returns raw string if Duckling fails (non-fatal) |

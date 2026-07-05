# Analytics API

Productivity analytics page: one call returns a de-duplicated, behavior-forward
payload — a **snapshot** of headline numbers, narrative **insights**, a daily
**activity** series, the flagship **behavioral** module (top days + their best
hours, focus time, momentum, procrastination), a **heatmap**, **work patterns**
(time-of-day + priority), and a **needs-attention** list.

> **Design principle — every headline metric has exactly one home.**
> The aggregate on-time rate and the canonical "completed" total live **only** in
> `snapshot`. The `on_time_rate` you see inside behavioral days/hours, heatmap
> cells, time-of-day buckets, and priority rows is a *per-slice breakdown*, not a
> duplicate. `activity`, `work_patterns.time_of_day`, and `work_patterns.by_priority`
> are breakdowns of that single total by a dimension — they carry no `total` field.

> **Resilience note:** everything is computed from MongoDB. The **behavioral**
> day/hour ranking *prefers* the Eva AI Server's scored output but falls back to a
> Mongo count-based ranking when the AI server is unavailable — see
> `behavioral.source`. No section ever goes blank.

Base path: `/api/analytics`

---

## `GET /api/analytics/dashboard`

| | |
|---|---|
| **Auth** | Required — `Authorization: Bearer <access_token>` |
| **Method** | `GET` |
| **Path** | `/api/analytics/dashboard` |
| **Request body** | None |

### Query params

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `days` | `7` \| `30` \| `90` | `30` | Lookback window. Drives **every** range-based section. The only exception is `snapshot.current_streak` (always "as of today"). |

Invalid `days` → `400`.

### Prerequisites

| Requirement | Affects |
|-------------|---------|
| User timezone on profile (`GET /api/auth/me` → `timezone`) | All date math (defaults to `UTC`) |
| Eva AI Server + `behavioral_analytics_enabled: true` | `behavioral.source` = `"ai"` (scored ranking). Otherwise `"history"` (Mongo fallback). |

---

### What it returns

Seven UI sections under `data`, plus metadata:

1. **`snapshot`** — the only home for headline numbers: productivity score, on-time rate, streak, completed (+Δ vs previous period).
2. **`insights`** — up to 5 rule-based narrative cards (a *narrative* layer — never introduces a metric not shown elsewhere).
3. **`activity`** — dense daily completion series over the range (a breakdown of the total; no `total` field).
4. **`behavioral`** — the flagship: **top days each with their own best hours**, focus time, momentum, procrastination signals, and low-data weekdays.
5. **`heatmap`** — day × hour completion grid (6AM–11PM).
6. **`work_patterns`** — two breakdowns: time-of-day distribution and per-priority reliability + focus time.
7. **`needs_attention`** — overdue count, due-soon list, pending-by-priority.

Plus metadata: `generated_at`, `timezone`, `range_days`, `meta`.

---

### Success response `200`

```json
{
  "status": "success",
  "data": {
    "generated_at": "2026-07-04T09:15:00.000Z",
    "timezone": "Asia/Karachi",
    "range_days": 30,
    "meta": { },
    "snapshot": { },
    "insights": [ ],
    "activity": { },
    "behavioral": { },
    "heatmap": { },
    "work_patterns": { },
    "needs_attention": { }
  }
}
```

---

### Type reference

#### Root `data`

| Field | Type | Description |
|-------|------|-------------|
| `generated_at` | `string` | ISO timestamp when the payload was built |
| `timezone` | `string` | IANA timezone used for all date math |
| `range_days` | `number` | Echo of query `days` (`7`, `30`, or `90`) |
| `meta` | `Meta` | Empty-state gating |
| `snapshot` | `Snapshot` | Headline numbers (single home) |
| `insights` | `Insight[]` | Narrative cards (may be empty) |
| `activity` | `Activity` | Daily completion series |
| `behavioral` | `Behavioral` | Top days/hours + focus + momentum + procrastination |
| `heatmap` | `Heatmap` | Day × hour completion grid |
| `work_patterns` | `WorkPatterns` | Time-of-day + priority breakdowns |
| `needs_attention` | `NeedsAttention` | Overdue / due-soon / pending |

#### `Meta`

| Field | Type | Description |
|-------|------|-------------|
| `has_enough_data` | `boolean` | `true` once all-time completions ≥ `min_tasks` (`20`) |
| `min_tasks` | `number` | Threshold to unlock full insights (`20`) |
| `tasks_remaining` | `number` | `max(0, min_tasks − all-time completed)` |

#### `Snapshot`

The **only** place headline numbers appear.

| Field | Type | Description |
|-------|------|-------------|
| `productivity_score` | `{ score, rating, caption }` | `score` `0–100`; `rating` ∈ `Excellent`(85+)/`Great`(70–84)/`Good`(55–69)/`Fair`(40–54)/`Building`(<40); `caption` matched to it |
| `on_time_rate` | `number` | On-time % over the range (`0–100`) |
| `current_streak` | `number` | Consecutive days with a completion, as of today |
| `completed` | `{ period, previous, change_percent }` | `period` = completions in range; `previous` = the equal window before it; `change_percent` = Δ |

#### `Insight`

Cards ordered by relevance, capped at 5. New user (0 completions) → a single
`rocket_launch` "get started" tip.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Position id (`"1"`, `"2"`, …) |
| `type` | `"positive" \| "warning" \| "tip" \| "info"` | Accent color |
| `icon` | `string` | Icon hint |
| `title` | `string` | Short bold headline |
| `message` | `string` | One-sentence detail |

Possible `icon` values: `local_fire_department`, `trending_up`, `trending_down`,
`verified`, `schedule`, `bolt`, `priority_high`, `warning_amber`, `wb_sunny`,
`calendar_month`, `rocket_launch`.

#### `Activity`

Dense series (one entry per day in range, zero-filled), oldest → newest.
Sum of `count` equals `snapshot.completed.period` — that's why there is no `total`.

| Field | Type | Description |
|-------|------|-------------|
| `series` | `ActivityPoint[]` | Length equals `range_days` |
| `active_days` | `number` | Days with ≥1 completion |
| `avg_per_active_day` | `number` | `period / active_days`, 1 decimal (`0` if none) |

**`ActivityPoint`**: `{ date: "YYYY-MM-DD" (local), count, on_time, late }`.

#### `Behavioral`

The flagship module. `top_days`/hours come from the AI server's scored ranking
when available (`source: "ai"`), otherwise a Mongo count ranking (`source: "history"`).

| Field | Type | Description |
|-------|------|-------------|
| `has_scores` | `boolean` | `true` when `top_days` is non-empty |
| `source` | `"ai" \| "history"` | Where `top_days` came from |
| `top_days` | `TopDay[]` | Top 3 most-productive weekdays, **each with its own best hours** |
| `focus` | `{ avg_minutes, sample_size }` | Average minutes to finish a task in range |
| `momentum` | `{ direction, delta, label }` | Behaviour trend vs the previous period |
| `procrastination` | `{ late_night_rate, reschedule_rate }` | % completed 10PM–5AM; % that were rescheduled |
| `unreliable_days` | `UnreliableDay[]` | Weekdays with `<5` completions (not enough to rank) |

**`TopDay`**

| Field | Type | Description |
|-------|------|-------------|
| `day` | `string` | e.g. `"Thursday"` |
| `day_num` | `number` | `0` = Monday … `6` = Sunday |
| `score` | `number` | AI productivity score, or relative count share (fallback) |
| `log_count` | `number` | Completions on that weekday |
| `on_time_rate` | `number` | Percentage `0–100` |
| `hours` | `TopHour[]` | That day's best 3 hour slots |

**`TopHour`**: `{ hour (0–23), hour_display, score, on_time_rate (0–100), log_count }`.

**`momentum.direction`** is `"up"` / `"down"` / `"steady"`; `delta` is the change in
a behaviour sub-score (on-time + consistency + volume, `0–100`) vs the previous
equal-length window; `label` is a ready sentence.

**`UnreliableDay`**: `{ day, log_count, needed (5) }`.

#### `Heatmap`

| Field | Type | Description |
|-------|------|-------------|
| `hour_range` | `{ start, end, start_display, end_display }` | Always `{ 6, 23, "6AM", "11PM" }` |
| `cells` | `HeatmapCell[]` | **Only cells with ≥1 completion** (sparse — fill a 7×18 grid with 0 in the UI). Keyed on the task's *scheduled* day/hour. The "peak" is the max-`count` cell (compute client-side). |

**`HeatmapCell`**: `{ day (0=Mon…6=Sun), day_name, hour (0–23), hour_display, count, on_time_rate (0–100) }`.

#### `WorkPatterns`

| Field | Type | Description |
|-------|------|-------------|
| `time_of_day` | `TimeBucket[]` | Always 4, Morning → Afternoon → Evening → Night |
| `by_priority` | `PriorityRow[]` | Always 3, `high` / `medium` / `low` |

**`TimeBucket`**: `{ key, label, range_display, count, percent (0–100), on_time_rate (0–100) }`.
Bucket hours: Morning `5–11`, Afternoon `12–16`, Evening `17–20`, Night `21–4`
(Night wraps midnight). The dominant bucket is the max-`count` entry (client-side).

**`PriorityRow`**: `{ priority, label, completed, on_time_rate (0–100), percent (0–100), avg_minutes }`
— `avg_minutes` is the average focus time for tasks of that priority.

#### `NeedsAttention`

| Field | Type | Description |
|-------|------|-------------|
| `overdue` | `number` | Pending/ongoing tasks past due (count) |
| `due_next_7d` | `number` | Pending/ongoing due in the next 7 days (count) |
| `due_soon` | `DueSoonTask[]` | Up to 8 tasks due in the next 48h |
| `pending_by_priority` | `{ high, medium, low }` | Counts of pending/ongoing per priority |

**`DueSoonTask`**: `{ id, title, due_datetime (ISO), priority }`.

---

### Example — populated

```json
{
  "status": "success",
  "data": {
    "generated_at": "2026-07-04T09:15:00.000Z",
    "timezone": "Asia/Karachi",
    "range_days": 30,
    "meta": { "has_enough_data": true, "min_tasks": 20, "tasks_remaining": 0 },
    "snapshot": {
      "productivity_score": { "score": 81, "rating": "Great", "caption": "Strong, consistent momentum. Keep it going." },
      "on_time_rate": 81,
      "current_streak": 5,
      "completed": { "period": 47, "previous": 41, "change_percent": 14.6 }
    },
    "insights": [
      { "id": "1", "type": "positive", "icon": "local_fire_department", "title": "On a roll", "message": "5-day completion streak — keep the momentum going!" },
      { "id": "2", "type": "info", "icon": "bolt", "title": "Your power hours", "message": "You're most productive on Thursday around 2PM." },
      { "id": "3", "type": "tip", "icon": "priority_high", "title": "High-priority tasks slip", "message": "High-priority tasks are on time only 64% of the time — plan them earlier in the day." }
    ],
    "activity": {
      "series": [
        { "date": "2026-06-05", "count": 0, "on_time": 0, "late": 0 },
        { "date": "2026-06-18", "count": 5, "on_time": 5, "late": 0 },
        { "date": "2026-07-04", "count": 2, "on_time": 1, "late": 1 }
      ],
      "active_days": 20,
      "avg_per_active_day": 2.4
    },
    "behavioral": {
      "has_scores": true,
      "source": "ai",
      "top_days": [
        {
          "day": "Thursday", "day_num": 3, "score": 0.9, "log_count": 8, "on_time_rate": 90,
          "hours": [
            { "hour": 14, "hour_display": "2PM", "score": 0.88, "on_time_rate": 92, "log_count": 5 },
            { "hour": 16, "hour_display": "4PM", "score": 0.7, "on_time_rate": 90, "log_count": 3 }
          ]
        },
        {
          "day": "Tuesday", "day_num": 1, "score": 0.8, "log_count": 7, "on_time_rate": 88,
          "hours": [ { "hour": 14, "hour_display": "2PM", "score": 0.7, "on_time_rate": 100, "log_count": 3 } ]
        }
      ],
      "focus": { "avg_minutes": 68, "sample_size": 47 },
      "momentum": { "direction": "up", "delta": 12, "label": "Your habits are improving versus the previous period." },
      "procrastination": { "late_night_rate": 8.5, "reschedule_rate": 12.8 },
      "unreliable_days": [
        { "day": "Friday", "log_count": 4, "needed": 5 },
        { "day": "Saturday", "log_count": 2, "needed": 5 },
        { "day": "Sunday", "log_count": 0, "needed": 5 }
      ]
    },
    "heatmap": {
      "hour_range": { "start": 6, "end": 23, "start_display": "6AM", "end_display": "11PM" },
      "cells": [
        { "day": 1, "day_name": "Tuesday", "hour": 14, "hour_display": "2PM", "count": 6, "on_time_rate": 100 },
        { "day": 3, "day_name": "Thursday", "hour": 14, "hour_display": "2PM", "count": 7, "on_time_rate": 85.7 }
      ]
    },
    "work_patterns": {
      "time_of_day": [
        { "key": "morning", "label": "Morning", "range_display": "5AM–12PM", "count": 11, "percent": 23.4, "on_time_rate": 81.8 },
        { "key": "afternoon", "label": "Afternoon", "range_display": "12PM–5PM", "count": 28, "percent": 59.6, "on_time_rate": 89.3 },
        { "key": "evening", "label": "Evening", "range_display": "5PM–9PM", "count": 6, "percent": 12.8, "on_time_rate": 66.7 },
        { "key": "night", "label": "Night", "range_display": "9PM–5AM", "count": 2, "percent": 4.3, "on_time_rate": 50 }
      ],
      "by_priority": [
        { "priority": "high", "label": "High", "completed": 14, "on_time_rate": 64.3, "percent": 29.8, "avg_minutes": 74 },
        { "priority": "medium", "label": "Medium", "completed": 24, "on_time_rate": 87.5, "percent": 51.1, "avg_minutes": 62 },
        { "priority": "low", "label": "Low", "completed": 9, "on_time_rate": 88.9, "percent": 19.1, "avg_minutes": 48 }
      ]
    },
    "needs_attention": {
      "overdue": 2,
      "due_next_7d": 9,
      "due_soon": [
        { "id": "674a1b2c3d4e5f6789012345", "title": "NLP assignment", "due_datetime": "2026-07-05T18:00:00+05:00", "priority": "high" }
      ],
      "pending_by_priority": { "high": 3, "medium": 6, "low": 2 }
    }
  }
}
```

### Example — new user / AI unavailable

Sections are always present. With no AI scores, `behavioral.source` is `"history"`
(Mongo fallback); empty states are conveyed by `meta` and low counts.

```json
{
  "status": "success",
  "data": {
    "generated_at": "2026-07-04T09:15:00.000Z",
    "timezone": "Asia/Karachi",
    "range_days": 30,
    "meta": { "has_enough_data": false, "min_tasks": 20, "tasks_remaining": 17 },
    "snapshot": {
      "productivity_score": { "score": 18, "rating": "Building", "caption": "Every completed task moves this number up." },
      "on_time_rate": 66.7,
      "current_streak": 1,
      "completed": { "period": 3, "previous": 0, "change_percent": 100 }
    },
    "insights": [
      { "id": "1", "type": "info", "icon": "wb_sunny", "title": "Afternoon person", "message": "67% of your work happens in the afternoon (12PM–5PM)." }
    ],
    "activity": {
      "series": [ { "date": "2026-06-24", "count": 1, "on_time": 1, "late": 0 } ],
      "active_days": 3,
      "avg_per_active_day": 1
    },
    "behavioral": {
      "has_scores": true,
      "source": "history",
      "top_days": [
        {
          "day": "Monday", "day_num": 0, "score": 1, "log_count": 2, "on_time_rate": 100,
          "hours": [ { "hour": 9, "hour_display": "9AM", "score": 1, "on_time_rate": 100, "log_count": 1 } ]
        }
      ],
      "focus": { "avg_minutes": 41, "sample_size": 3 },
      "momentum": { "direction": "up", "delta": 22, "label": "Your habits are improving versus the previous period." },
      "procrastination": { "late_night_rate": 0, "reschedule_rate": 0 },
      "unreliable_days": [
        { "day": "Monday", "log_count": 2, "needed": 5 },
        { "day": "Tuesday", "log_count": 1, "needed": 5 }
      ]
    },
    "heatmap": {
      "hour_range": { "start": 6, "end": 23, "start_display": "6AM", "end_display": "11PM" },
      "cells": []
    },
    "work_patterns": {
      "time_of_day": [
        { "key": "morning", "label": "Morning", "range_display": "5AM–12PM", "count": 1, "percent": 33.3, "on_time_rate": 100 },
        { "key": "afternoon", "label": "Afternoon", "range_display": "12PM–5PM", "count": 2, "percent": 66.7, "on_time_rate": 50 },
        { "key": "evening", "label": "Evening", "range_display": "5PM–9PM", "count": 0, "percent": 0, "on_time_rate": 0 },
        { "key": "night", "label": "Night", "range_display": "9PM–5AM", "count": 0, "percent": 0, "on_time_rate": 0 }
      ],
      "by_priority": [
        { "priority": "high", "label": "High", "completed": 0, "on_time_rate": 0, "percent": 0, "avg_minutes": 0 },
        { "priority": "medium", "label": "Medium", "completed": 3, "on_time_rate": 66.7, "percent": 100, "avg_minutes": 41 },
        { "priority": "low", "label": "Low", "completed": 0, "on_time_rate": 0, "percent": 0, "avg_minutes": 0 }
      ]
    },
    "needs_attention": {
      "overdue": 0,
      "due_next_7d": 2,
      "due_soon": [],
      "pending_by_priority": { "high": 0, "medium": 2, "low": 0 }
    }
  }
}
```

---

### Errors

| Status | When |
|--------|------|
| `400` | `days` is not `7`, `30`, or `90` |
| `401` | Missing or invalid JWT |
| `500` | Server error |

---

### Frontend / Flutter notes

**Single fetch for the whole page**

- Use only `GET /api/analytics/dashboard`. Refetch on range change (`?days=7|30|90`).

**Behavioral (flagship)**

- Render `top_days` as the headline "when you're productive" widget: 3 day cards,
  each expandable to its `hours` (best 2–3 slots) with per-slot on-time %.
- Show `momentum.direction` as an up/down/steady chip with `label`; `focus.avg_minutes`
  as an "avg focus time" stat; `procrastination` rates as gentle "watch-out" meters.
- `behavioral.source` tells you whether the ranking is AI-scored (`"ai"`) or a Mongo
  fallback (`"history"`) — optionally show a small "estimated" hint on `"history"`.

**No duplicated numbers**

- Show the aggregate on-time rate and completed total only from `snapshot`. The
  `on_time_rate` inside behavioral days/hours, heatmap cells, buckets, and priority
  rows is a per-slice breakdown.
- The heatmap "peak" cell and the "dominant" day-part are derivable client-side
  (max by `count`) — they are intentionally not sent.

**Heatmap**

- `cells` is sparse — build a 7×18 grid (Mon–Sun × 6AM–11PM), default missing slots
  to `count: 0`, color by `count`. `day` is `0` = Monday … `6` = Sunday.

**Empty states**

- If `!meta.has_enough_data`, show a "complete `meta.tasks_remaining` more tasks to
  unlock insights" prompt.

**Timezone**

- All boundaries use the user's profile timezone; refetch after they change it.

---

### Related APIs

| Need | API |
|------|-----|
| User timezone | `GET /api/auth/me` or `GET /api/profile` |
| Toggle behavioral analytics (affects `behavioral.source`) | `PATCH /api/settings` → `behavioral_analytics_enabled` — [settings-api.md](./settings-api.md) |
| Task details from `due_soon` | `GET /api/tasks/:id` — [tasks-api.md](./tasks-api.md) |
| Home screen (different from analytics) | `GET /api/dashboard` — [dashboard-api.md](./dashboard-api.md) |

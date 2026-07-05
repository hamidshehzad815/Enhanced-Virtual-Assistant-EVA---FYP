# Analytics API

Productivity analytics page: one call returns a de-duplicated, six-section payload —
a **snapshot** of headline numbers, narrative **insights**, a daily **activity**
series, a **productivity map** (heatmap + best times), **work patterns**
(time-of-day + priority), and a **needs-attention** list.

> **Design principle — every headline metric has exactly one home.**
> The aggregate on-time rate and the canonical "completed" total live **only** in
> `snapshot`. The `on_time_rate` you see inside heatmap cells, time-of-day buckets,
> and priority rows is a *per-slice breakdown*, not a duplicate. `activity`,
> `work_patterns.time_of_day`, and `work_patterns.by_priority` are breakdowns of that
> single total by a dimension — they carry no `total` field.

> **Resilience note:** everything is computed from MongoDB **except**
> `productivity_map.best_slots`, which comes from the Eva AI Server's scored hours.
> If the AI server is down or behavioral analytics is disabled, `best_slots` is `[]`
> and every other section still renders.

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
| `days` | `7` \| `30` \| `90` | `30` | Lookback window. Drives **every** range-based section (`snapshot`, `activity`, `productivity_map`, `work_patterns`). The only exception is `snapshot.current_streak`, which is always "as of today". |

Invalid `days` → `400`.

### Prerequisites

| Requirement | Affects |
|-------------|---------|
| User timezone on profile (`GET /api/auth/me` → `timezone`) | All date calculations (defaults to `UTC`) |
| Eva AI Server running + `behavioral_analytics_enabled: true` | `productivity_map.best_slots` only |

---

### What it returns

Six UI sections under `data`, plus metadata:

1. **`snapshot`** — the only home for headline numbers: productivity score, on-time rate, streak, completed (+Δ vs previous period).
2. **`insights`** — up to 5 rule-based narrative cards (a *narrative* layer — never introduces a metric not shown elsewhere).
3. **`activity`** — dense daily completion series over the range (a breakdown of the total; no `total` field).
4. **`productivity_map`** — "when you're at your best": day×hour heatmap + AI-scored best scheduling slots + weekdays that need more data.
5. **`work_patterns`** — two breakdowns: time-of-day distribution and on-time reliability per priority.
6. **`needs_attention`** — actionable now: overdue count, due-soon list, pending-by-priority.

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
    "productivity_map": { },
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
| `productivity_map` | `ProductivityMap` | Heatmap + best slots + unreliable days |
| `work_patterns` | `WorkPatterns` | Time-of-day + priority breakdowns |
| `needs_attention` | `NeedsAttention` | Overdue / due-soon / pending |

#### `Meta`

| Field | Type | Description |
|-------|------|-------------|
| `has_enough_data` | `boolean` | `true` once all-time completions ≥ `min_tasks` (`20`). Use to gate the rich page vs an "unlock insights" state. |
| `min_tasks` | `number` | Threshold to unlock full insights (`20`) |
| `tasks_remaining` | `number` | `max(0, min_tasks − all-time completed)` — for a "complete N more" prompt |

#### `Snapshot`

The **only** place headline numbers appear.

| Field | Type | Description |
|-------|------|-------------|
| `productivity_score` | `{ score, rating, caption }` | `score` `0–100`; `rating` one of `Excellent` (85+), `Great` (70–84), `Good` (55–69), `Fair` (40–54), `Building` (<40); `caption` is a short matched sentence |
| `on_time_rate` | `number` | On-time completion % over the range (`0–100`) |
| `current_streak` | `number` | Consecutive days with a completion, as of today (not range-bound) |
| `completed` | `{ period, previous, change_percent }` | `period` = completions in range; `previous` = completions in the equal window before it; `change_percent` = Δ (can be negative) |

The score blends four internal components — on-time (35%), consistency (25%),
volume (25%), streak (15%) — but only the final `score` is exposed (the component
breakdown was removed because it restated `on_time_rate` and `current_streak`).

#### `Insight`

Ready-to-render cards, ordered by relevance, capped at 5. For a brand-new user
(0 completions) a single `rocket_launch` "get started" tip is returned.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Position id within this response (`"1"`, `"2"`, …) |
| `type` | `"positive" \| "warning" \| "tip" \| "info"` | Drives accent color |
| `icon` | `string` | Icon hint (map to your own icon set) |
| `title` | `string` | Short bold headline |
| `message` | `string` | One-sentence detail |

Possible `icon` values: `local_fire_department`, `trending_up`, `trending_down`,
`verified`, `schedule`, `bolt`, `priority_high`, `warning_amber`, `wb_sunny`,
`calendar_month`, `rocket_launch`.

#### `Activity`

Dense series (one entry per day in the range, zero-filled), oldest → newest.
Sum of `count` equals `snapshot.completed.period` — that's why there is no `total`.

| Field | Type | Description |
|-------|------|-------------|
| `series` | `ActivityPoint[]` | Length equals `range_days` |
| `active_days` | `number` | Days with ≥1 completion |
| `avg_per_active_day` | `number` | `period / active_days`, 1 decimal (`0` if none) |

**`ActivityPoint`**

| Field | Type | Description |
|-------|------|-------------|
| `date` | `string` | Local date `YYYY-MM-DD` |
| `count` | `number` | Completions that day |
| `on_time` | `number` | On-time completions |
| `late` | `number` | Late completions |

#### `ProductivityMap`

| Field | Type | Description |
|-------|------|-------------|
| `hour_range` | `{ start, end, start_display, end_display }` | Always `{ 6, 23, "6AM", "11PM" }` |
| `cells` | `HeatmapCell[]` | **Only cells with ≥1 completion** (sparse — fill a 7×18 grid with 0 in the UI). Keyed on the task's *scheduled* day/hour. |
| `best_slots` | `BestSlot[]` | Top 3 AI-scored slots (empty when AI unavailable). The "peak" is just the max-`count` cell — compute it client-side. |
| `unreliable_days` | `UnreliableDay[]` | Weekdays with `<5` completions in range (not enough to rank) |

**`HeatmapCell`**

| Field | Type | Description |
|-------|------|-------------|
| `day` | `number` | `0` = Monday … `6` = Sunday |
| `day_name` | `string` | e.g. `"Thursday"` |
| `hour` | `number` | `0–23` |
| `hour_display` | `string` | e.g. `"2PM"` |
| `count` | `number` | Completions in the slot (use for color intensity) |
| `on_time_rate` | `number` | Percentage `0–100` (per-slice breakdown) |

**`BestSlot`**

| Field | Type | Description |
|-------|------|-------------|
| `day_name` | `string` | e.g. `"Thursday"` |
| `hour_display` | `string` | e.g. `"1PM"` |
| `on_time_rate` | `number` | Percentage `0–100` |
| `suggestion` | `string` | Ready-to-show tip, e.g. `"Plan deep work on Thursday around 1PM"` |

**`UnreliableDay`**

| Field | Type | Description |
|-------|------|-------------|
| `day` | `string` | Weekday name |
| `log_count` | `number` | Actual completions in range |
| `needed` | `number` | Minimum for a reliable rank (`5`) |

#### `WorkPatterns`

| Field | Type | Description |
|-------|------|-------------|
| `time_of_day` | `TimeBucket[]` | Always 4, Morning → Afternoon → Evening → Night |
| `by_priority` | `PriorityRow[]` | Always 3, `high` / `medium` / `low` |

**`TimeBucket`** — completions bucketed by local completion hour.

| Field | Type | Description |
|-------|------|-------------|
| `key` | `"morning" \| "afternoon" \| "evening" \| "night"` | Stable key |
| `label` | `string` | e.g. `"Afternoon"` |
| `range_display` | `string` | e.g. `"12PM–5PM"` (Night is `"9PM–5AM"`, wraps midnight) |
| `count` | `number` | Completions in the bucket |
| `percent` | `number` | Share of the range total, `0–100` |
| `on_time_rate` | `number` | Percentage `0–100` |

Bucket hours: Morning `5–11`, Afternoon `12–16`, Evening `17–20`, Night `21–4`.
The dominant bucket is the max-`count` entry — compute it client-side.

**`PriorityRow`** — how reliably each priority is finished on time.

| Field | Type | Description |
|-------|------|-------------|
| `priority` | `"high" \| "medium" \| "low"` | Priority key |
| `label` | `string` | `"High"` / `"Medium"` / `"Low"` |
| `completed` | `number` | Completed tasks of this priority in range |
| `on_time_rate` | `number` | Percentage `0–100` (`0` when `completed` is 0) |
| `percent` | `number` | Share of all completed across priorities, `0–100` |

#### `NeedsAttention`

| Field | Type | Description |
|-------|------|-------------|
| `overdue` | `number` | Pending/ongoing tasks past due (count only) |
| `due_next_7d` | `number` | Pending/ongoing tasks due in the next 7 days (count) |
| `due_soon` | `DueSoonTask[]` | Up to 8 tasks due in the next 48h |
| `pending_by_priority` | `{ high, medium, low }` | Counts of pending/ongoing tasks per priority |

**`DueSoonTask`**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Task MongoDB id |
| `title` | `string` | Task title |
| `due_datetime` | `string` | ISO datetime |
| `priority` | `"high" \| "medium" \| "low"` | |

---

### Example — populated

```http
GET /api/analytics/dashboard?days=30
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

```json
{
  "status": "success",
  "data": {
    "generated_at": "2026-07-04T09:15:00.000Z",
    "timezone": "Asia/Karachi",
    "range_days": 30,
    "meta": { "has_enough_data": true, "min_tasks": 20, "tasks_remaining": 0 },
    "snapshot": {
      "productivity_score": {
        "score": 81,
        "rating": "Great",
        "caption": "Strong, consistent momentum. Keep it going."
      },
      "on_time_rate": 81,
      "current_streak": 5,
      "completed": { "period": 47, "previous": 41, "change_percent": 14.6 }
    },
    "insights": [
      {
        "id": "1",
        "type": "positive",
        "icon": "local_fire_department",
        "title": "On a roll",
        "message": "5-day completion streak — keep the momentum going!"
      },
      {
        "id": "2",
        "type": "info",
        "icon": "bolt",
        "title": "Your power hours",
        "message": "You're most productive on Thursday around 2PM."
      },
      {
        "id": "3",
        "type": "tip",
        "icon": "priority_high",
        "title": "High-priority tasks slip",
        "message": "High-priority tasks are on time only 64% of the time — plan them earlier in the day."
      }
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
    "productivity_map": {
      "hour_range": { "start": 6, "end": 23, "start_display": "6AM", "end_display": "11PM" },
      "cells": [
        { "day": 1, "day_name": "Tuesday", "hour": 14, "hour_display": "2PM", "count": 6, "on_time_rate": 100 },
        { "day": 3, "day_name": "Thursday", "hour": 14, "hour_display": "2PM", "count": 7, "on_time_rate": 85.7 }
      ],
      "best_slots": [
        { "day_name": "Thursday", "hour_display": "1PM", "on_time_rate": 92, "suggestion": "Plan deep work on Thursday around 1PM" }
      ],
      "unreliable_days": [
        { "day": "Friday", "log_count": 4, "needed": 5 },
        { "day": "Saturday", "log_count": 2, "needed": 5 },
        { "day": "Sunday", "log_count": 0, "needed": 5 }
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
        { "priority": "high", "label": "High", "completed": 14, "on_time_rate": 64.3, "percent": 29.8 },
        { "priority": "medium", "label": "Medium", "completed": 24, "on_time_rate": 87.5, "percent": 51.1 },
        { "priority": "low", "label": "Low", "completed": 9, "on_time_rate": 88.9, "percent": 19.1 }
      ]
    },
    "needs_attention": {
      "overdue": 2,
      "due_next_7d": 9,
      "due_soon": [
        {
          "id": "674a1b2c3d4e5f6789012345",
          "title": "NLP assignment",
          "due_datetime": "2026-07-05T18:00:00+05:00",
          "priority": "high"
        }
      ],
      "pending_by_priority": { "high": 3, "medium": 6, "low": 2 }
    }
  }
}
```

### Example — new user / not enough data

Sections are always present; empty states are conveyed by `meta` and low counts.

```json
{
  "status": "success",
  "data": {
    "generated_at": "2026-07-04T09:15:00.000Z",
    "timezone": "Asia/Karachi",
    "range_days": 30,
    "meta": { "has_enough_data": false, "min_tasks": 20, "tasks_remaining": 17 },
    "snapshot": {
      "productivity_score": {
        "score": 18,
        "rating": "Building",
        "caption": "Every completed task moves this number up."
      },
      "on_time_rate": 66.7,
      "current_streak": 1,
      "completed": { "period": 3, "previous": 0, "change_percent": 100 }
    },
    "insights": [
      {
        "id": "1",
        "type": "info",
        "icon": "wb_sunny",
        "title": "Afternoon person",
        "message": "67% of your work happens in the afternoon (12PM–5PM)."
      }
    ],
    "activity": {
      "series": [ { "date": "2026-06-24", "count": 1, "on_time": 1, "late": 0 } ],
      "active_days": 3,
      "avg_per_active_day": 1
    },
    "productivity_map": {
      "hour_range": { "start": 6, "end": 23, "start_display": "6AM", "end_display": "11PM" },
      "cells": [],
      "best_slots": [],
      "unreliable_days": [
        { "day": "Monday", "log_count": 1, "needed": 5 },
        { "day": "Tuesday", "log_count": 0, "needed": 5 }
      ]
    },
    "work_patterns": {
      "time_of_day": [
        { "key": "morning", "label": "Morning", "range_display": "5AM–12PM", "count": 1, "percent": 33.3, "on_time_rate": 100 },
        { "key": "afternoon", "label": "Afternoon", "range_display": "12PM–5PM", "count": 2, "percent": 66.7, "on_time_rate": 50 },
        { "key": "evening", "label": "Evening", "range_display": "5PM–9PM", "count": 0, "percent": 0, "on_time_rate": 0 },
        { "key": "night", "label": "Night", "range_display": "9PM–5AM", "count": 0, "percent": 0, "on_time_rate": 0 }
      ],
      "by_priority": [
        { "priority": "high", "label": "High", "completed": 0, "on_time_rate": 0, "percent": 0 },
        { "priority": "medium", "label": "Medium", "completed": 3, "on_time_rate": 66.7, "percent": 100 },
        { "priority": "low", "label": "Low", "completed": 0, "on_time_rate": 0, "percent": 0 }
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

- Use only `GET /api/analytics/dashboard` — there are no sub-routes.
- Refetch when the user changes the range toggle (`?days=7|30|90`). The range drives every section except `snapshot.current_streak`.

**No duplicated numbers**

- Show the aggregate on-time rate and completed total only from `snapshot`. The `on_time_rate` inside cells / buckets / priority rows is a per-slice breakdown.
- The "peak" heatmap cell and the "dominant" day-part are **derivable client-side** (max by `count`) — they are intentionally not sent.

**Weekday numbers**

- `day` in heatmap cells: `0` = Monday … `6` = Sunday (same as calendar / learning schedules).

**Heatmap rendering**

- `cells` is sparse — build a 7×18 grid (Mon–Sun × 6AM–11PM), default missing slots to `count: 0`, color by `count`.

**Empty states**

- If `!meta.has_enough_data`, show a "complete `meta.tasks_remaining` more tasks to unlock insights" prompt.
- `best_slots` is `[]` when the AI server is unavailable or behavioral analytics is disabled — hide that sub-widget; the heatmap still renders from Mongo.

**Timezone**

- All boundaries use the user's profile timezone. Refetch after the user changes their timezone in profile.

---

### Related APIs

| Need | API |
|------|-----|
| User timezone | `GET /api/auth/me` or `GET /api/profile` |
| Toggle behavioral analytics (affects `best_slots`) | `PATCH /api/settings` → `behavioral_analytics_enabled` — [settings-api.md](./settings-api.md) |
| Task details from `due_soon` | `GET /api/tasks/:id` — [tasks-api.md](./tasks-api.md) |
| Home screen (different from analytics) | `GET /api/dashboard` — [dashboard-api.md](./dashboard-api.md) |

# Analytics Dashboard API

Single endpoint for the web analytics page.

## Endpoint

```
GET /api/analytics/dashboard
```

| | |
|---|---|
| **Auth** | Required — `Authorization: Bearer <access_token>` |
| **Query** | `days` optional: `7`, `30` (default), or `90` |
| **Timezone** | Uses `timezone` from authenticated user profile (`/api/auth/me`) |

### Errors

| Status | When |
|--------|------|
| `401` | Missing or invalid JWT |
| `400` | `days` is not `7`, `30`, or `90` |

### Prerequisites

- User must have `behavioral_analytics_enabled: true` in settings (for full AI behavioral data).
- AI server must be running for `behavioral` and `best_slots` (proxies `GET /analytics?type=full` on Eva AI Server).

---

## Response envelope

```json
{
  "status": "success",
  "data": { ... }
}
```

Top-level `data` fields:

| Field | Type | Description |
|-------|------|-------------|
| `generated_at` | ISO string | Server timestamp when payload was built |
| `timezone` | string | User timezone used for date calculations |
| `range_days` | number | Heatmap lookback (`7`, `30`, or `90`) |
| `hero` | object | Summary stat cards |
| `behavioral` | object | AI productivity scores + enrichments |
| `heatmap` | object | Day × hour completion grid |
| `tasks` | object | Task counts and at-risk list |
| `completion_trend` | object | Last 3 weeks of completions |
| `best_slots` | array | Top 3 best hour slots (from AI) |

---

## `hero`

Summary cards at the top of the page. Sourced from `activity_logs` and `tasks`.

| Field | Type | Description |
|-------|------|-------------|
| `completed_this_week` | number | Completions Mon–Sun (current week, user TZ) |
| `completed_last_week` | number | Completions previous week |
| `week_change_percent` | number | % change vs last week |
| `on_time_rate` | number | All-time on-time completion % |
| `total_completed` | number | All-time completed task count |
| `streak_days` | number | Consecutive days with ≥1 completion |
| `upcoming_7d` | number | Pending/ongoing tasks due in next 7 days |

---

## `behavioral`

AI behavioral scores (Eva AI Server) plus backend enrichments.

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | boolean | `false` if behavioral analytics is disabled |
| `has_enough_data` | boolean | `true` when ≥20 total completions |
| `thresholds` | object | `{ global: 20, per_day: 5 }` |
| `total_completed` | number | Total completions used by AI |
| `top_days` | array | Top 3 best days (AI-scored) |
| `hour_windows` | array | Top 3 consecutive hour blocks (see below) |
| `strength_summary` | string \| null | e.g. `"You're strongest Thursday & Wednesday afternoons."` |
| `unreliable_days` | array | Days with &lt;5 completions (not enough data to rank) |
| `completion_rate` | object | `{ total_completed, on_time, late, on_time_rate }` |
| `avg_time_taken` | number \| null | Avg minutes to complete (from AI) |

### `top_days[]` item

| Field | Type |
|-------|------|
| `day` | string — e.g. `"Thursday"` |
| `day_num` | number — `0` Monday … `6` Sunday |
| `score` | number — AI productivity score |
| `log_count` | number |
| `on_time_rate` | number — `0`–`1` |

### `hour_windows[]` item

Merged consecutive productive hours on the same day, ranked by combined score.

| Field | Type | Example |
|-------|------|---------|
| `day_num` | number | `1` |
| `day_name` | string | `"Tuesday"` |
| `start_hour` | number | `14` |
| `end_hour` | number | `16` |
| `start_display` | string | `"2PM"` |
| `end_display` | string | `"4PM"` |
| `label` | string | `"Tuesday 2PM–4PM"` |
| `score` | number | Combined score |
| `log_count` | number | Total completions in window |

### `unreliable_days[]` item

| Field | Type |
|-------|------|
| `day` | string |
| `day_num` | number |
| `log_count` | number |
| `needed` | number — usually `5` |

---

## `heatmap`

Day × hour grid from `activity_logs`. Only hours **6AM–11PM** are included in `cells`.

| Field | Type | Description |
|-------|------|-------------|
| `range_days` | number | Same as query `days` |
| `timezone` | string | User timezone |
| `hour_range` | object | `{ start: 6, end: 23, start_display: "6AM", end_display: "11PM" }` |
| `cells` | array | Only cells with ≥1 completion |
| `peak` | object \| null | Busiest cell (highest `count`) |
| `weakest` | object \| null | Lowest on-time / sparse cell with data |

### `cells[]` item

| Field | Type |
|-------|------|
| `day` | number — `0`–`6` |
| `day_name` | string |
| `hour` | number — `0`–`23` |
| `hour_display` | string — e.g. `"2PM"` |
| `count` | number |
| `on_time_rate` | number — percentage |
| `intensity` | number — same as `count` (for chart coloring) |

---

## `tasks`

From `tasks` collection for the authenticated user.

| Field | Type | Description |
|-------|------|-------------|
| `pending` | number | Pending + ongoing tasks |
| `complete` | number | Completed tasks |
| `overdue` | number | Pending/ongoing past due (count only) |
| `by_priority` | object | `{ high, medium, low }` counts |
| `due_within_48h` | array | Up to 10 tasks due in next 48 hours |
| `busiest_day_this_week` | object | Day with most due tasks this week |

### `due_within_48h[]` item

| Field | Type |
|-------|------|
| `id` | string |
| `title` | string |
| `due_datetime` | ISO string |
| `priority` | `"high"` \| `"medium"` \| `"low"` |
| `status` | `"pending"` \| `"ongoing"` |

### `busiest_day_this_week`

| Field | Type |
|-------|------|
| `day_num` | number |
| `day_name` | string |
| `task_count` | number |

---

## `completion_trend`

Last **3 weeks** of completions from `activity_logs`.

| Field | Type |
|-------|------|
| `weeks` | number — always `3` |
| `trend` | array |

### `trend[]` item

| Field | Type |
|-------|------|
| `week` | number — ISO week number |
| `count` | number — total completions |
| `on_time` | number |
| `late` | number |
| `on_time_rate` | number — percentage |

---

## `best_slots`

Top **3** hour slots from AI behavioral hours data, sorted by score.

| Field | Type |
|-------|------|
| `day_num` | number |
| `day_name` | string |
| `hour` | number |
| `hour_display` | string |
| `score` | number |
| `on_time_rate` | number |
| `log_count` | number |
| `suggestion` | string — human-readable scheduling tip |

Empty array `[]` when no AI hours data or behavioral analytics disabled.

---

## Example request

```http
GET /api/analytics/dashboard?days=30
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

## Example response (abbreviated)

```json
{
  "status": "success",
  "data": {
    "generated_at": "2026-06-26T04:39:29.771Z",
    "timezone": "Asia/Karachi",
    "range_days": 30,
    "hero": {
      "completed_this_week": 5,
      "completed_last_week": 14,
      "week_change_percent": -64.3,
      "on_time_rate": 82.4,
      "total_completed": 68,
      "streak_days": 1,
      "upcoming_7d": 14
    },
    "behavioral": {
      "enabled": true,
      "has_enough_data": true,
      "top_days": [{ "day": "Thursday", "day_num": 3, "score": 0.74, "log_count": 17, "on_time_rate": 1 }],
      "hour_windows": [{ "label": "Tuesday 2PM–4PM", "score": 2.11, "log_count": 9 }],
      "strength_summary": "You're strongest Thursday & Wednesday afternoons.",
      "unreliable_days": [],
      "completion_rate": { "total_completed": 68, "on_time": 56, "late": 12, "on_time_rate": 82.4 },
      "avg_time_taken": 67.49
    },
    "heatmap": {
      "range_days": 30,
      "hour_range": { "start": 6, "end": 23, "start_display": "6AM", "end_display": "11PM" },
      "cells": [{ "day": 3, "day_name": "Thursday", "hour": 13, "count": 5, "on_time_rate": 100 }],
      "peak": { "day_name": "Friday", "hour_display": "1PM", "count": 8 },
      "weakest": { "day_name": "Friday", "hour_display": "9PM", "on_time_rate": 0 }
    },
    "tasks": {
      "pending": 45,
      "complete": 64,
      "overdue": 3,
      "by_priority": { "high": 4, "medium": 40, "low": 1 },
      "due_within_48h": [],
      "busiest_day_this_week": { "day_num": 4, "day_name": "Friday", "task_count": 4 }
    },
    "completion_trend": {
      "weeks": 3,
      "trend": [{ "week": 24, "count": 21, "on_time": 17, "late": 4, "on_time_rate": 81 }]
    },
    "best_slots": [
      {
        "day_name": "Thursday",
        "hour_display": "1PM",
        "score": 0.875,
        "suggestion": "Best time to plan deep work: Thursday around 1PM"
      }
    ]
  }
}
```

---

## Demo data

```bash
cd Eva_Backend_Server
node scripts/seed-areej-behavioral-analytics.js --clean
```

Login as seeded user, copy JWT, then call the endpoint.

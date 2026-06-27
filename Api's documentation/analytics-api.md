# Analytics API

Productivity analytics page: one call returns hero stats, behavioral scores, heatmap, task overview, completion trend, and best scheduling slots.

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
| `days` | `7` \| `30` \| `90` | `30` | Lookback window for **heatmap** only. Completion trend is always last **3 weeks** regardless of this value. |

Invalid `days` → `400`.

### Prerequisites (for full payload)

| Requirement | Affects |
|-------------|---------|
| User timezone on profile (`GET /api/auth/me` → `timezone`) | All date/week calculations |
| `behavioral_analytics_enabled: true` in settings | Rich `behavioral` + `best_slots` data |
| Eva AI Server running | `behavioral` scores and `best_slots` (backend proxies AI `/analytics?type=full`) |

When behavioral analytics is off or AI is down, `behavioral.enabled` may be `false` and `best_slots` may be `[]` — other sections still return from MongoDB.

---

### What it returns

Seven UI sections under `data`:

1. **`hero`** — top stat cards (this week vs last week, streak, on-time rate)
2. **`behavioral`** — AI productivity scores + hour windows + strength summary
3. **`heatmap`** — day × hour completion grid (6AM–11PM)
4. **`tasks`** — counts, priority breakdown, due-soon list
5. **`completion_trend`** — last 3 ISO weeks of completions
6. **`best_slots`** — top 3 AI-recommended hour slots for scheduling

Plus metadata: `generated_at`, `timezone`, `range_days`.

---

### Success response `200`

```json
{
  "status": "success",
  "data": {
    "generated_at": "2026-06-26T04:39:29.771Z",
    "timezone": "Asia/Karachi",
    "range_days": 30,
    "hero": { },
    "behavioral": { },
    "heatmap": { },
    "tasks": { },
    "completion_trend": { },
    "best_slots": [ ]
  }
}
```

---

### Type reference

#### Root `data`

| Field | Type | Description |
|-------|------|-------------|
| `generated_at` | `string` | ISO timestamp when payload was built |
| `timezone` | `string` | User IANA timezone used for all date math |
| `range_days` | `number` | Echo of query `days` (`7`, `30`, or `90`) |
| `hero` | `HeroStats` | Summary stat cards |
| `behavioral` | `BehavioralSection` | AI scores + enrichments |
| `heatmap` | `HeatmapSection` | Productivity grid |
| `tasks` | `TasksSection` | Task counts and at-risk list |
| `completion_trend` | `CompletionTrendSection` | Weekly completion bars |
| `best_slots` | `BestSlot[]` | Top 3 scheduling suggestions (may be empty) |

#### `HeroStats`

| Field | Type | Description |
|-------|------|-------------|
| `completed_this_week` | `number` | Completions Mon–Sun (current week, user TZ) |
| `completed_last_week` | `number` | Completions previous calendar week |
| `week_change_percent` | `number` | % change vs last week (can be negative) |
| `on_time_rate` | `number` | All-time on-time completion % (`0–100`) |
| `total_completed` | `number` | All-time completed task count |
| `streak_days` | `number` | Consecutive days with ≥1 completion |
| `upcoming_7d` | `number` | Pending/ongoing tasks due in next 7 days |

#### `BehavioralSection`

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `boolean` | `false` when user disabled behavioral analytics in settings |
| `has_enough_data` | `boolean` | `true` when ≥20 total completions (AI threshold) |
| `thresholds` | `{ global: number, per_day: number }` | `{ global: 20, per_day: 5 }` — system constants |
| `total_completed` | `number` | Completions counted by AI scorer |
| `top_days` | `TopDay[]` | Top 3 best weekdays by AI score |
| `hour_windows` | `HourWindow[]` | Top 3 merged consecutive productive hour blocks |
| `strength_summary` | `string \| null` | Human sentence, e.g. `"You're strongest Thursday & Wednesday afternoons."` |
| `unreliable_days` | `UnreliableDay[]` | Weekdays with &lt;5 logs (not enough data to rank) |
| `completion_rate` | `{ total_completed, on_time, late, on_time_rate }` | On-time breakdown |
| `avg_time_taken` | `number \| null` | Average minutes to complete a task (from AI) |

**`TopDay`**

| Field | Type | Description |
|-------|------|-------------|
| `day` | `string` | e.g. `"Thursday"` |
| `day_num` | `number` | `0` = Monday … `6` = Sunday |
| `score` | `number` | AI productivity score |
| `log_count` | `number` | Completions on that weekday |
| `on_time_rate` | `number` | `0`–`1` fraction |

**`HourWindow`**

Merged consecutive productive hours on the same day, ranked by combined score.

| Field | Type | Example |
|-------|------|---------|
| `day_num` | `number` | `1` |
| `day_name` | `string` | `"Tuesday"` |
| `start_hour` | `number` | `14` (24h) |
| `end_hour` | `number` | `16` |
| `start_display` | `string` | `"2PM"` |
| `end_display` | `string` | `"4PM"` |
| `label` | `string` | `"Tuesday 2PM–4PM"` |
| `score` | `number` | Combined window score |
| `log_count` | `number` | Completions in window |

**`UnreliableDay`**

| Field | Type | Description |
|-------|------|-------------|
| `day` | `string` | Weekday name |
| `day_num` | `number` | `0`–`6` |
| `log_count` | `number` | Actual completions |
| `needed` | `number` | Usually `5` — minimum for reliable ranking |

#### `HeatmapSection`

| Field | Type | Description |
|-------|------|-------------|
| `range_days` | `number` | Same as query `days` |
| `timezone` | `string` | User timezone |
| `hour_range` | `{ start, end, start_display, end_display }` | Always `{ start: 6, end: 23, start_display: "6AM", end_display: "11PM" }` |
| `cells` | `HeatmapCell[]` | **Only cells with ≥1 completion** (sparse array — fill missing slots with 0 in UI) |
| `peak` | `HeatmapCell \| null` | Busiest cell (highest `count`) |
| `weakest` | `HeatmapCell \| null` | Lowest on-time / sparse cell with data |

**`HeatmapCell`**

| Field | Type | Description |
|-------|------|-------------|
| `day` | `number` | `0`–`6` (Mon–Sun) |
| `day_name` | `string` | e.g. `"Friday"` |
| `hour` | `number` | `0`–`23` |
| `hour_display` | `string` | e.g. `"2PM"` |
| `count` | `number` | Completions in that slot |
| `on_time_rate` | `number` | Percentage `0–100` |
| `intensity` | `number` | Same as `count` — use for heatmap color scale |

#### `TasksSection`

| Field | Type | Description |
|-------|------|-------------|
| `pending` | `number` | Pending + ongoing tasks |
| `complete` | `number` | Completed tasks |
| `overdue` | `number` | Pending/ongoing past due (**count only**, no task list) |
| `by_priority` | `{ high, medium, low }` | Counts per priority |
| `due_within_48h` | `DueSoonTask[]` | Up to **10** tasks due in next 48 hours |
| `busiest_day_this_week` | `{ day_num, day_name, task_count }` | Weekday with most due tasks this week |

**`DueSoonTask`**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Task MongoDB id |
| `title` | `string` | Task title |
| `due_datetime` | `string` | ISO datetime |
| `priority` | `"high" \| "medium" \| "low"` | |
| `status` | `"pending" \| "ongoing"` | |

#### `CompletionTrendSection`

| Field | Type | Description |
|-------|------|-------------|
| `weeks` | `number` | Always `3` |
| `trend` | `WeekTrend[]` | One entry per week (oldest → newest or as returned) |

**`WeekTrend`**

| Field | Type | Description |
|-------|------|-------------|
| `week` | `number` | ISO week number |
| `count` | `number` | Total completions that week |
| `on_time` | `number` | On-time completions |
| `late` | `number` | Late completions |
| `on_time_rate` | `number` | Percentage `0–100` |

#### `BestSlot`

Top hour slots from AI behavioral data, sorted by score (max 3).

| Field | Type | Description |
|-------|------|-------------|
| `day_num` | `number` | `0`–`6` |
| `day_name` | `string` | e.g. `"Thursday"` |
| `hour` | `number` | `0`–`23` |
| `hour_display` | `string` | e.g. `"1PM"` |
| `score` | `number` | AI slot score |
| `on_time_rate` | `number` | On-time rate for that slot |
| `log_count` | `number` | Sample size |
| `suggestion` | `string` | Ready-to-show tip, e.g. `"Best time to plan deep work: Thursday around 1PM"` |

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
      "thresholds": { "global": 20, "per_day": 5 },
      "total_completed": 68,
      "top_days": [
        {
          "day": "Thursday",
          "day_num": 3,
          "score": 0.74,
          "log_count": 17,
          "on_time_rate": 1
        }
      ],
      "hour_windows": [
        {
          "day_num": 1,
          "day_name": "Tuesday",
          "start_hour": 14,
          "end_hour": 16,
          "start_display": "2PM",
          "end_display": "4PM",
          "label": "Tuesday 2PM–4PM",
          "score": 2.11,
          "log_count": 9
        }
      ],
      "strength_summary": "You're strongest Thursday & Wednesday afternoons.",
      "unreliable_days": [],
      "completion_rate": {
        "total_completed": 68,
        "on_time": 56,
        "late": 12,
        "on_time_rate": 82.4
      },
      "avg_time_taken": 67.49
    },
    "heatmap": {
      "range_days": 30,
      "timezone": "Asia/Karachi",
      "hour_range": {
        "start": 6,
        "end": 23,
        "start_display": "6AM",
        "end_display": "11PM"
      },
      "cells": [
        {
          "day": 3,
          "day_name": "Thursday",
          "hour": 13,
          "hour_display": "1PM",
          "count": 5,
          "on_time_rate": 100,
          "intensity": 5
        }
      ],
      "peak": {
        "day": 4,
        "day_name": "Friday",
        "hour": 13,
        "hour_display": "1PM",
        "count": 8,
        "on_time_rate": 87.5,
        "intensity": 8
      },
      "weakest": {
        "day": 4,
        "day_name": "Friday",
        "hour": 21,
        "hour_display": "9PM",
        "count": 2,
        "on_time_rate": 0,
        "intensity": 2
      }
    },
    "tasks": {
      "pending": 45,
      "complete": 64,
      "overdue": 3,
      "by_priority": { "high": 4, "medium": 40, "low": 1 },
      "due_within_48h": [
        {
          "id": "674a1b2c3d4e5f6789012345",
          "title": "NLP assignment",
          "due_datetime": "2026-06-27T18:00:00+05:00",
          "priority": "high",
          "status": "pending"
        }
      ],
      "busiest_day_this_week": {
        "day_num": 4,
        "day_name": "Friday",
        "task_count": 4
      }
    },
    "completion_trend": {
      "weeks": 3,
      "trend": [
        {
          "week": 22,
          "count": 18,
          "on_time": 14,
          "late": 4,
          "on_time_rate": 77.8
        },
        {
          "week": 23,
          "count": 21,
          "on_time": 17,
          "late": 4,
          "on_time_rate": 81
        },
        {
          "week": 24,
          "count": 15,
          "on_time": 12,
          "late": 3,
          "on_time_rate": 80
        }
      ]
    },
    "best_slots": [
      {
        "day_num": 3,
        "day_name": "Thursday",
        "hour": 13,
        "hour_display": "1PM",
        "score": 0.875,
        "on_time_rate": 0.92,
        "log_count": 12,
        "suggestion": "Best time to plan deep work: Thursday around 1PM"
      }
    ]
  }
}
```

### Example — limited behavioral data

New user or behavioral analytics disabled:

```json
{
  "status": "success",
  "data": {
    "generated_at": "2026-06-26T04:39:29.771Z",
    "timezone": "Asia/Karachi",
    "range_days": 30,
    "hero": {
      "completed_this_week": 0,
      "completed_last_week": 0,
      "week_change_percent": 0,
      "on_time_rate": 0,
      "total_completed": 3,
      "streak_days": 0,
      "upcoming_7d": 2
    },
    "behavioral": {
      "enabled": false,
      "has_enough_data": false,
      "thresholds": { "global": 20, "per_day": 5 },
      "total_completed": 3,
      "top_days": [],
      "hour_windows": [],
      "strength_summary": null,
      "unreliable_days": [
        { "day": "Monday", "day_num": 0, "log_count": 1, "needed": 5 }
      ],
      "completion_rate": {
        "total_completed": 3,
        "on_time": 2,
        "late": 1,
        "on_time_rate": 66.7
      },
      "avg_time_taken": null
    },
    "heatmap": {
      "range_days": 30,
      "timezone": "Asia/Karachi",
      "hour_range": {
        "start": 6,
        "end": 23,
        "start_display": "6AM",
        "end_display": "11PM"
      },
      "cells": [],
      "peak": null,
      "weakest": null
    },
    "tasks": {
      "pending": 2,
      "complete": 3,
      "overdue": 0,
      "by_priority": { "high": 0, "medium": 2, "low": 0 },
      "due_within_48h": [],
      "busiest_day_this_week": { "day_num": 0, "day_name": "Monday", "task_count": 1 }
    },
    "completion_trend": {
      "weeks": 3,
      "trend": [
        { "week": 22, "count": 0, "on_time": 0, "late": 0, "on_time_rate": 0 },
        { "week": 23, "count": 2, "on_time": 1, "late": 1, "on_time_rate": 50 },
        { "week": 24, "count": 1, "on_time": 1, "late": 0, "on_time_rate": 100 }
      ]
    },
    "best_slots": []
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

- Use only `GET /api/analytics/dashboard` — there are no sub-routes like `/hero` or `/heatmap`.
- Refetch when user changes the range toggle (`?days=7|30|90`).

**Weekday numbers**

- `day_num` / `day` on heatmap and behavioral objects: **`0` = Monday … `6` = Sunday** (same as learning schedules and calendar).

**Heatmap rendering**

- `cells` is sparse — build a full 7×18 grid (Mon–Sun × 6AM–11PM) and default missing slots to `count: 0`.
- Color cells with `intensity` (equals `count`). Show `peak` / `weakest` as highlighted callouts if present.
- `on_time_rate` on cells is `0–100` (percentage), unlike `TopDay.on_time_rate` which is `0–1`.

**Behavioral empty states**

- If `!behavioral.has_enough_data`, show a message like “Complete more tasks to unlock insights” using `thresholds.global` (20).
- If `unreliable_days` is non-empty, optionally show which weekdays need more data (`needed` vs `log_count`).
- Display `strength_summary` as-is when non-null.

**Tasks section**

- `overdue` is a **number only** — link to calendar/tasks screen for details, do not expect an overdue list here.
- `due_within_48h` is capped at 10 items — show “View all” if `upcoming_7d` or pending count is higher.

**Best slots**

- Render `suggestion` strings directly in cards or tooltips.
- Empty `best_slots` is normal when AI is unavailable or analytics disabled.

**Settings link**

- Behavioral section respects `behavioral_analytics_enabled` from [settings-api.md](./settings-api.md). Offer a toggle or link to settings when `behavioral.enabled === false`.

**Timezone**

- All week boundaries use the user’s profile timezone. After user changes timezone in profile, refetch analytics.

**Performance**

- One response can be large — cache per `(days)` selection; avoid polling more often than on screen focus or pull-to-refresh.

---

### Related APIs

| Need | API |
|------|-----|
| User timezone | `GET /api/auth/me` or `GET /api/profile` |
| Toggle behavioral analytics | `PATCH /api/settings` → `behavioral_analytics_enabled` — [settings-api.md](./settings-api.md) |
| Task details from `due_within_48h` | `GET /api/tasks/:id` — [tasks-api.md](./tasks-api.md) |
| Home screen (different from analytics) | `GET /api/dashboard` — [dashboard-api.md](./dashboard-api.md) |

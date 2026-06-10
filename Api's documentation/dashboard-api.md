# Dashboard API

Home screen aggregated data: up next task, daily progress, learning focus cards, today's schedule.

---

## `GET /api/dashboard`

| | |
|---|---|
| **Auth** | Required |
| **Method** | `GET` |
| **Path** | `/api/dashboard` |
| **Query params** | None |
| **Request body** | None |

### What it returns

Four widgets in one call:

1. **`up_next`** — first non-complete task due **today** (user timezone)
2. **`daily_progress`** — completion stats for today
3. **`learning`** — active/paused learning goals with next topic
4. **`today_schedule`** — all tasks due today, sorted by time

Tasks included: owned by user **or** collaborator with `status: "accepted"`.

---

### Success response `200`

```json
{
  "status": "success",
  "data": {
    "timezone": "Asia/Karachi",
    "up_next": { },
    "daily_progress": { },
    "learning": [ ],
    "today_schedule": [ ]
  }
}
```

---

### Type reference

#### Root `data`

| Field | Type | Description |
|-------|------|-------------|
| `timezone` | `string` | User IANA timezone |
| `up_next` | `DashboardTask \| null` | Next incomplete task today; `null` if none |
| `daily_progress` | `DailyProgress` | Today's completion ring |
| `learning` | `LearningCard[]` | Active/paused goals (may be empty) |
| `today_schedule` | `DashboardTask[]` | All today's tasks (may be empty) |

#### `DailyProgress`

| Field | Type | Description |
|-------|------|-------------|
| `date` | `string` | Local date `YYYY-MM-DD` |
| `timezone` | `string` | Same as user timezone |
| `completed_tasks` | `number` | Count with stored status complete |
| `total_tasks` | `number` | All tasks due today |
| `completion_percentage` | `number` | `0–100` integer (rounded) |

#### `DashboardTask`

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | `string` | MongoDB task id |
| `title` | `string` | Task title |
| `status` | `"pending" \| "complete"` | Stored status (DB only has these two) |
| `display_status` | `"pending" \| "ongoing" \| "overdue" \| "complete"` | **Use this for UI badges/colors** |
| `priority` | `"low" \| "medium" \| "high"` | Task priority |
| `day` | `string \| null` | Weekday label, e.g. `"Thursday"` |
| `time` | `string \| null` | Clock label, e.g. `"3:00 PM"` |
| `due_datetime` | `string \| null` | ISO with offset in user TZ |
| `is_learning_task` | `boolean` | `true` if linked to a learning plan |
| `learning_goal_id` | `string \| null` | Learning goal id when `is_learning_task` |

**`display_status` rules (derived, not stored):**

| Value | When |
|-------|------|
| `complete` | Task marked complete |
| `pending` | Not complete, now before due time |
| `ongoing` | Not complete, now inside task duration window |
| `overdue` | Not complete, now after duration window |

#### `LearningCard`

| Field | Type | Description |
|-------|------|-------------|
| `learning_goal_id` | `string` | Goal id |
| `title` | `string` | Goal title |
| `roadmap_key` | `string \| null` | Roadmap subject key |
| `status` | `"active" \| "paused"` | Goal status |
| `progress_percent` | `number` | `0–100` from completed/total topics |
| `next_topic` | `LearningTopic \| null` | Next pending/ongoing topic; `null` if none scheduled |

#### `LearningTopic`

| Field | Type | Description |
|-------|------|-------------|
| `topic_id` | `string` | Roadmap topic id |
| `title` | `string` | Topic title |
| `status` | `string` | Topic status (`pending`, `ongoing`, etc.) |
| `day` | `string \| null` | Formatted weekday |
| `time` | `string \| null` | Formatted time |
| `scheduled_datetime` | `string \| null` | ISO with offset |

---

### Example — populated

```json
{
  "status": "success",
  "data": {
    "timezone": "Asia/Karachi",
    "up_next": {
      "task_id": "674a1b2c3d4e5f6789012345",
      "title": "NLP Mid Exam",
      "status": "pending",
      "display_status": "pending",
      "priority": "high",
      "day": "Thursday",
      "time": "3:00 PM",
      "due_datetime": "2026-06-05T15:00:00+05:00",
      "is_learning_task": false,
      "learning_goal_id": null
    },
    "daily_progress": {
      "date": "2026-06-05",
      "timezone": "Asia/Karachi",
      "completed_tasks": 1,
      "total_tasks": 2,
      "completion_percentage": 50
    },
    "learning": [
      {
        "learning_goal_id": "674a1b2c3d4e5f6789012346",
        "title": "Python roadmap",
        "roadmap_key": "functions",
        "status": "active",
        "progress_percent": 30,
        "next_topic": {
          "topic_id": "674a1b2c3d4e5f6789012347",
          "title": "Functions intro",
          "status": "pending",
          "day": "Thursday",
          "time": "7:00 PM",
          "scheduled_datetime": "2026-06-05T19:00:00+05:00"
        }
      }
    ],
    "today_schedule": [
      {
        "task_id": "674a1b2c3d4e5f6789012348",
        "title": "Math Lecture",
        "status": "complete",
        "display_status": "complete",
        "priority": "medium",
        "day": "Thursday",
        "time": "8:00 AM",
        "due_datetime": "2026-06-05T08:00:00+05:00",
        "is_learning_task": false,
        "learning_goal_id": null
      },
      {
        "task_id": "674a1b2c3d4e5f6789012345",
        "title": "NLP Mid Exam",
        "status": "pending",
        "display_status": "pending",
        "priority": "high",
        "day": "Thursday",
        "time": "3:00 PM",
        "due_datetime": "2026-06-05T15:00:00+05:00",
        "is_learning_task": false,
        "learning_goal_id": null
      }
    ]
  }
}
```

### Example — empty day

```json
{
  "status": "success",
  "data": {
    "timezone": "Asia/Karachi",
    "up_next": null,
    "daily_progress": {
      "date": "2026-06-05",
      "timezone": "Asia/Karachi",
      "completed_tasks": 0,
      "total_tasks": 0,
      "completion_percentage": 0
    },
    "learning": [],
    "today_schedule": []
  }
}
```

---

### Errors

| Status | When |
|--------|------|
| `401` | No token / expired token |
| `500` | Server error |

---

### Flutter / frontend notes

- Call after login; store token in secure storage.
- Bind progress ring to `daily_progress.completion_percentage` (0–100).
- Use `display_status` for schedule row tags, not raw `status`.
- Handle `next_topic: null` on learning cards (goal exists but no upcoming topic).
- Empty arrays / `up_next: null` are normal — show empty states, not errors.

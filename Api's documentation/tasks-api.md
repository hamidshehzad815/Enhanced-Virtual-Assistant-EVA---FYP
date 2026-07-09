# Tasks API

Calendar and task-detail endpoints for listing, reading, updating, and deleting the authenticated user's tasks.

Base path: `/api/tasks`

---

## `GET /api/tasks/calendar`

| | |
|---|---|
| **Auth** | Required |
| **Method** | `GET` |
| **Path** | `/api/tasks/calendar` |

Returns **all non-deleted tasks owned by the user**, sorted by `due_datetime`. Use on the **calendar screen** — unlike `GET /api/tasks`, it includes past and completed tasks (not limited to upcoming).

### Query params (all optional)

| Param | Description |
|-------|-------------|
| `status` | `pending` or `complete` |
| `priority` | `low`, `medium`, or `high` |
| `subject` | Case-insensitive title search |
| `date` | Single day `YYYY-MM-DD` (user timezone) |

### Success `200`

```json
{
  "status": "success",
  "data": {
    "timezone": "Asia/Karachi",
    "total": 2,
    "tasks": [
      {
        "id": "507f1f77bcf86cd799439012",
        "title": "Physics exam",
        "due_datetime": "2026-06-19T20:48:00+05:00",
        "duration": 120,
        "priority": "medium",
        "status": "pending",
        "display_status": "pending",
        "is_learning_task": false,
        "learning_goal_id": null,
        "learning_session_id": null,
        "editable": true
      }
    ]
  }
}
```

### Errors

| HTTP | When |
|------|------|
| `401` | Missing/invalid token |

---

## `GET /api/tasks/:id`

| | |
|---|---|
| **Auth** | Required |
| **Method** | `GET` |
| **Path** | `/api/tasks/:id` |

Fetch a single task owned by the user.

### Success `200`

```json
{
  "status": "success",
  "data": {
    "timezone": "Asia/Karachi",
    "task": {
      "id": "507f1f77bcf86cd799439012",
      "title": "Physics exam",
      "description": "Review chapter 3",
      "due_datetime": "2026-06-19T20:48:00+05:00",
      "duration": 120,
      "priority": "medium",
      "status": "pending",
      "display_status": "pending",
      "is_learning_task": false,
      "learning_goal_id": null,
      "learning_session_id": null,
      "editable": true
    }
  }
}
```

### Errors

| HTTP | When |
|------|------|
| `400` | Invalid task id |
| `404` | Task not found or not owned by user |

---

## `PATCH /api/tasks/:id`

| | |
|---|---|
| **Auth** | Required |
| **Method** | `PATCH` |
| **Path** | `/api/tasks/:id` |
| **Body** | JSON — at least one field required |

Update task fields from calendar or task detail UI.

**Learning sessions** (`is_learning_task: true`) are **read-only** here — use roadmap session APIs instead.

### Body fields (all optional, min 1 required)

| Field | Type | Rules |
|-------|------|-------|
| `title` | `string` | 1–200 chars |
| `description` | `string \| null` | Max 1000; `null` or `""` clears |
| `due_datetime` | `string` | ISO datetime |
| `duration` | `number` | Minutes, 5–1440 |
| `priority` | `string` | `low`, `medium`, `high` |
| `status` | `string` | `pending` or `complete` |

### Success `200`

```json
{
  "status": "success",
  "message": "Task updated",
  "data": {
    "timezone": "Asia/Karachi",
    "task": { }
  }
}
```

### Errors

| HTTP | When |
|------|------|
| `400` | Invalid id, empty body, or validation failure |
| `404` | Task not found |
| `409` | Task is a learning session (`is_learning_task: true`) — edit via roadmap |

> **Note:** For status-only updates from the tasks list, `PATCH /api/tasks/:id/status` with `{ "status": "complete" }` still works for **normal tasks only**. Learning sessions return `409`.

---

## `DELETE /api/tasks/:id`

| | |
|---|---|
| **Auth** | Required |
| **Method** | `DELETE` |
| **Path** | `/api/tasks/:id` |

Soft-deletes the task (`is_deleted: true`).

### Success `200`

```json
{
  "status": "success",
  "message": "Task deleted",
  "data": {
    "task_id": "507f1f77bcf86cd799439012",
    "is_deleted": true
  }
}
```

### Errors

| HTTP | When |
|------|------|
| `400` | Invalid task id |
| `404` | Task not found |
| `409` | Task is a learning session — delete via roadmap / cancel plan |

---

## Task object (shared shape)

| Field | Type | Notes |
|-------|------|-------|
| `id` | `string` | Task id |
| `title` | `string` | |
| `description` | `string \| null` | Detail / PATCH responses only |
| `due_datetime` | `string` | ISO with offset in user TZ |
| `duration` | `number` | Minutes |
| `priority` | `"low" \| "medium" \| "high"` | |
| `status` | `"pending" \| "complete"` | Stored status |
| `display_status` | `"pending" \| "ongoing" \| "overdue" \| "complete"` | **Use for UI badges** |
| `completed_at` | `string \| null` | When marked complete |
| `is_learning_task` | `boolean` | |
| `learning_goal_id` | `string \| null` | Roadmap plan id when `is_learning_task` |
| `learning_session_id` | `string \| null` | Roadmap session id (`roadmap_topics._id`) when `is_learning_task` |
| `editable` | `boolean` | `false` for learning sessions; calendar/tasks UI must not PATCH/DELETE |

---

## Calendar frontend flow

1. `GET /api/tasks/calendar` — load all tasks
2. Group `tasks[]` by local date from `due_datetime` on the client
3. Tap task:
   - **`editable: false`** → open roadmap session (`GET /api/learning/:goalId/sessions/:sessionId`); do not show task edit form
   - **`editable: true`** → `GET /api/tasks/:id` for detail; `PATCH` / `DELETE` as usual
4. Use `display_status` for normal task badges; use roadmap `session_state` for learning sessions

---

## Related endpoints

| Endpoint | Use |
|----------|-----|
| `GET /api/tasks` | Paginated tasks page (upcoming by default) |
| `PATCH /api/tasks/:id/status` | Quick complete/uncomplete toggle |
| `GET /api/dashboard` | Today's schedule widget only |

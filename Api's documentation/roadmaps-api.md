# Roadmaps API

User learning roadmaps (goals + sessions).

See [README.md](./README.md) for auth and error envelopes.  
**Frontend UI (buttons, popup, all cases):** [roadmaps-frontend-actions-guide.md](./roadmaps-frontend-actions-guide.md)

---

## Available endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/roadmaps/plans` | **All user plans** (no `sessions[]`) |
| `GET` | `/api/roadmaps/:goalId/schedule-dates` | **Reschedule picker dates** (plan learning weekdays only) |
| `GET` | `/api/roadmaps/:goalId` | Roadmap + sessions for one plan |
| `GET` | `/api/learning/:goalId/sessions/:sessionId` | Single session detail (popup / detail screen) |
| `PATCH` | `/api/learning/:goalId/sessions/:sessionId` | Reschedule, complete, or skip a session |
| `PATCH` | `/api/learning/:goalId/status` | Pause, resume, or cancel a plan |

---

## UX flow

1. `GET /api/roadmaps/plans` → show list of user's learning plans.
2. User picks a plan → `GET /api/roadmaps/:goalId` → render roadmap + sessions.
3. Tap session → `GET /api/learning/:goalId/sessions/:sessionId` → session detail popup.
4. After any mutation → use response `data.roadmap` / `data.session` to refresh UI.

---

## Resolution rules

| Rule | Behavior |
| ---- | -------- |
| Fetch roadmap | Use **`goalId`** from `GET /api/roadmaps/plans` → `roadmap.id` |
| Chat create (same language) | Blocked while any **active** or **paused** plan exists for that language |
| Multiple plans | User may have Python, JavaScript, SQL, etc. at the same time (different `goalId`) |
| Deleted / cancelled | `404` on `GET /api/roadmaps/:goalId` |


---

## Session object (`roadmap.sessions[]`)


| Field                | Type            | Notes                                                                                |
| -------------------- | --------------- | ------------------------------------------------------------------------------------ |
| `id`                 | `string`        | Session (topic) id                                                                   |
| `order`              | `number`        | 1-based order in plan                                                                |
| `title`              | `string`        | Read-only                                                                            |
| `status`             | `string`        | `pending`, `ongoing`, `completed`, `skipped` — **current value from server**         |
| `scheduled_date`     | `string | null` | ISO datetime in user TZ                                                              |
| `estimated_duration` | `number`        | Minutes — read-only                                                                  |
| `resources`          | `array`         | `{ title, url, thumbnail?, channel_name? }` — read-only                              |
| `session_state`      | `string`        | Computed: `locked`, `unlocked_future`, `ongoing`, `overdue`, `completed`, `skipped`, `upcoming` |
| `is_current`         | `boolean`       | `true` for the current pending session                                               |
| `unlock_at`          | `string | null` | When locked current session becomes actionable                                       |
| `completed_at`       | `string | null` | Only when `status` is `completed` or `skipped`                                       |
| `collaborator_progress` | `array`      | Per-collaborator status on **this** session: `{ user_id, status }` (status = that collaborator's session `status`). `[]` for solo plans or the `plans`/mutation payloads. |


Use `status` + `session_state` to decide what the session detail screen may offer. The frontend shows update options; the server enforces rules.

---

## Collaborators (`roadmap.collaborators[]`)

When someone accepts a plan invite, the plan is **cloned** into their account and
they progress independently. The owner's roadmap responses surface each
collaborator and — for accepted ones — how far they've reached on the shared plan.
`GET /api/roadmaps/plans` includes `collaborators[]` **without** per-session data;
`GET /api/roadmaps/:goalId` adds `progress` here and `collaborator_progress` on
each session. Only public profile fields are exposed.

| Field | Type | Notes |
|-------|------|-------|
| `user._id` | `string` | Collaborator user id (match against `sessions[].collaborator_progress[].user_id`) |
| `user.name` | `string \| null` | Display name |
| `user.username` | `string \| null` | Handle |
| `user.profile_picture` | `string \| null` | Avatar URL; fall back to initials when `null` |
| `status` | `"pending" \| "accepted" \| "rejected"` | Invite status |
| `progress` | `object \| null` | `null` until accepted (or for `plans` list) |
| `progress.completed_topics` | `number` | Sessions the collaborator has completed |
| `progress.total_topics` | `number` | Sessions in their copy of the plan |
| `progress.progress_percent` | `number` | `0–100` |
| `progress.current_order` | `number \| null` | Session `order` they're currently on; `null` when finished |
| `progress.plan_status` | `string` | Their plan status: `active`, `completed`, `paused`, `cancelled` |

| `session_state`   | Reschedule | Skip | Complete |
| ----------------- | ---------- | ---- | -------- |
| `locked`          | no         | no   | no       |
| `unlocked_future` | yes        | yes  | no       |
| `ongoing`         | yes        | no   | yes      |
| `overdue`         | yes        | no   | yes      |

`ongoing` = from scheduled start through `estimated_duration` (default 90 min). `overdue` = after that window ends.

---

## `GET /api/roadmaps/plans`

List **all learning plans** the user has created. Returns roadmap metadata only — **no `sessions[]`**.

Use this for a “My learning plans” screen. Load sessions with `GET /api/roadmaps/:goalId`.


|                      |                                                                          |
| -------------------- | ------------------------------------------------------------------------ |
| **Auth**             | Required                                                                 |
| **Method**           | `GET`                                                                    |
| **Path**             | `/api/roadmaps/plans`                                                    |
| **Query (optional)** | `status` — comma-separated: `active`, `paused`, `completed`, `cancelled` |
| **Body**             | None                                                                     |


### Example request

```http
GET /api/roadmaps/plans HTTP/1.1
Authorization: Bearer <access_token>
```

```http
GET /api/roadmaps/plans?status=active,paused HTTP/1.1
Authorization: Bearer <access_token>
```

### Success `200`

```json
{
  "status": "success",
  "data": {
    "timezone": "Asia/Karachi",
    "roadmaps": [
      {
        "id": "674a1b2c3d4e5f6789012301",
        "title": "Python basics",
        "language": "Python",
        "language_key": "python",
        "track_label": "Basics",
        "status": "active",
        "start_date": "2026-06-01",
        "end_date": "2026-07-15",
        "completed_topics": 2,
        "total_topics": 8,
        "progress_percent": 25,
        "session_count": 8,
        "sessions_summary": {
          "completed": 2,
          "skipped": 0,
          "pending": 6,
          "ongoing": 0
        },
        "collaborators": [
          {
            "user": {
              "_id": "507f1f77bcf86cd799439099",
              "name": "Aisha Khan",
              "username": "aisha",
              "profile_picture": null
            },
            "status": "accepted",
            "progress": null
          }
        ]
      }
    ]
  }
}
```

No `sessions` array on each item. Cancelled / deleted plans are excluded (`is_deleted: false`).

### Errors

| Status | When |
| ------ | ---- |
| `400`  | Invalid `status` filter |
| `401`  | Auth failure |

---

## `GET /api/roadmaps/:goalId/schedule-dates`

Returns **calendar dates** the user may pick when rescheduling the **current session** for a plan. Only dates that fall on the plan’s **learning schedule weekdays** are included (same rules as `PATCH /api/learning/:goalId/sessions/:sessionId` with `scheduled_date`).

Use this to drive a **limited date picker** instead of a full calendar.


|            |                                                              |
| ---------- | ------------------------------------------------------------ |
| **Auth**   | Required                                                     |
| **Method** | `GET`                                                        |
| **Path**   | `/api/roadmaps/:goalId/schedule-dates`                       |
| **Query**  | `horizon_weeks` (optional, default `12`, max `52`) — how far ahead to list dates |
| **Body**   | None                                                         |


### Example request

```http
GET /api/roadmaps/674a1b2c3d4e5f6789012301/schedule-dates HTTP/1.1
Authorization: Bearer <access_token>
```

### Success `200`

```json
{
  "status": "success",
  "data": {
    "timezone": "Asia/Karachi",
    "goal_id": "674a1b2c3d4e5f6789012301",
    "schedule_id": "sched-evening",
    "schedule_label": "Evening",
    "weekdays": [
      { "day": 0, "day_label": "Monday", "time": "18:00", "duration_minutes": 90 },
      { "day": 4, "day_label": "Friday", "time": "18:00", "duration_minutes": 90 }
    ],
    "range": {
      "from": "2026-06-27",
      "to": "2026-09-19"
    },
    "dates": [
      {
        "date": "2026-06-30",
        "day": 0,
        "day_label": "Monday",
        "time": "18:00",
        "duration_minutes": 90,
        "scheduled_datetime": "2026-06-30T18:00:00+05:00"
      }
    ]
  }
}
```

| Field | Notes |
| ----- | ----- |
| `weekdays` | Recurring slots from the plan’s linked learning schedule (`day` 0=Mon … 6=Sun) |
| `dates[]` | Concrete **YYYY-MM-DD** values from **today** (user TZ) through `range.to` |
| `scheduled_datetime` | Slot start in user timezone — pass to UI or use `date` with `PATCH` reschedule |

Only **active** plans return dates. Pick a date from `dates[]`, then call `PATCH /api/learning/:goalId/sessions/:sessionId` with `{ "scheduled_date": "YYYY-MM-DD" }`.

### Errors

| Status | When |
| ------ | ---- |
| `400`  | Invalid goal id, non-active plan, invalid `horizon_weeks` |
| `401`  | Auth failure |
| `404`  | Goal or user settings not found |

---

## `GET /api/roadmaps/:goalId`

Load one learning plan with **all sessions**. Use `id` from `GET /api/roadmaps/plans`.


|            |                           |
| ---------- | ------------------------- |
| **Auth**   | Required                  |
| **Method** | `GET`                     |
| **Path**   | `/api/roadmaps/:goalId`   |
| **Body**   | None                      |


### Example request

```http
GET /api/roadmaps/674a1b2c3d4e5f6789012301 HTTP/1.1
Authorization: Bearer <access_token>
```

### Success `200`

```json
{
  "status": "success",
  "data": {
    "timezone": "Asia/Karachi",
    "language": {
      "key": "python",
      "label": "Python"
    },
    "roadmap": {
      "id": "674a1b2c3d4e5f6789012301",
      "title": "Python basics",
      "language": "Python",
      "language_key": "python",
      "track_label": "Basics",
      "status": "active",
      "start_date": "2026-06-01",
      "end_date": "2026-07-15",
      "completed_topics": 1,
      "total_topics": 8,
      "progress_percent": 13,
      "session_count": 8,
      "sessions_summary": {
        "completed": 1,
        "skipped": 0,
        "pending": 7,
        "ongoing": 0
      },
      "collaborators": [
        {
          "user": {
            "_id": "507f1f77bcf86cd799439099",
            "name": "Aisha Khan",
            "username": "aisha",
            "profile_picture": null
          },
          "status": "accepted",
          "progress": {
            "completed_topics": 1,
            "total_topics": 8,
            "progress_percent": 13,
            "current_order": 2,
            "plan_status": "active"
          }
        }
      ],
      "sessions": [
        {
          "id": "674a1b2c3d4e5f6789012302",
          "order": 1,
          "title": "Variables and types",
          "status": "completed",
          "scheduled_date": "2026-06-02T18:00:00+05:00",
          "estimated_duration": 90,
          "resources": [
            {
              "title": "Python variables explained",
              "url": "https://www.youtube.com/watch?v=example1",
              "thumbnail": "https://i.ytimg.com/vi/example1/hqdefault.jpg",
              "channel_name": "Corey Schafer"
            }
          ],
          "session_state": "completed",
          "is_current": false,
          "unlock_at": null,
          "completed_at": "2026-06-03T19:30:00+05:00",
          "collaborator_progress": [
            { "user_id": "507f1f77bcf86cd799439099", "status": "completed" }
          ]
        },
        {
          "id": "674a1b2c3d4e5f6789012303",
          "order": 2,
          "title": "Control flow",
          "status": "pending",
          "scheduled_date": "2026-06-05T18:00:00+05:00",
          "estimated_duration": 90,
          "resources": [
            {
              "title": "If else in Python",
              "url": "https://www.youtube.com/watch?v=example2"
            }
          ],
          "session_state": "overdue",
          "is_current": true,
          "unlock_at": null
        }
      ]
    }
  }
}
```

### Errors

| Status | When |
| ------ | ---- |
| `400`  | Invalid `goalId` |
| `401`  | Auth failure |
| `404`  | Goal not found or not owned by user |


---

## `GET /api/learning/:goalId/sessions/:sessionId`

Load **one session** with full detail for the roadmap popup / detail screen.

Uses the same session shape as `roadmap.sessions[]` (including `session_state`, `is_current`, `unlock_at`, `resources`).


|                  |                                             |
| ---------------- | ------------------------------------------- |
| **Auth**         | Required                                    |
| **Method**       | `GET`                                       |
| **Path**         | `/api/learning/:goalId/sessions/:sessionId` |
| **Body**         | None                                        |


`:goalId` = `roadmap.id` from `GET /api/roadmaps`.  
`:sessionId` = `sessions[].id` from the same roadmap.

### Example request

```http
GET /api/learning/674a1b2c3d4e5f6789012301/sessions/674a1b2c3d4e5f6789012303 HTTP/1.1
Authorization: Bearer <access_token>
```

### Success `200`

```json
{
  "status": "success",
  "data": {
    "timezone": "Asia/Karachi",
    "language": { "key": "python", "label": "Python" },
    "roadmap": {
      "id": "674a1b2c3d4e5f6789012301",
      "title": "Python basics",
      "language": "Python",
      "language_key": "python",
      "track_label": "Basics",
      "status": "active",
      "start_date": "2026-06-01",
      "end_date": "2026-07-15",
      "completed_topics": 1,
      "total_topics": 8,
      "progress_percent": 13,
      "session_count": 8,
      "sessions_summary": {
        "completed": 1,
        "skipped": 0,
        "pending": 7,
        "ongoing": 0
      }
    },
    "session": {
      "id": "674a1b2c3d4e5f6789012303",
      "order": 2,
      "title": "Control flow",
      "status": "pending",
      "scheduled_date": "2026-06-05T18:00:00+05:00",
      "estimated_duration": 90,
      "resources": [
        {
          "title": "If else in Python",
          "url": "https://www.youtube.com/watch?v=example2"
        }
      ],
      "session_state": "locked",
      "is_current": true,
      "unlock_at": "2026-06-04T18:00:00+05:00"
    }
  }
}
```

**Use `data.session` for the popup.**  
`data.roadmap` is a **summary only** (plan title, progress, status) — **no `sessions[]` list**.  
For the full list, use `GET /api/roadmaps/:goalId` or the `PATCH` session response (which still returns the full roadmap for refresh).

### Errors


| Status | When |
| ------ | ---- |
| `400`  | Invalid goal or session id |
| `401`  | Auth failure |
| `404`  | Goal or session not found (or not owned by user) |

---

## `PATCH /api/learning/:goalId/sessions/:sessionId`

Update session **date** and/or **status** (same rules as chat).


|                  |                                             |
| ---------------- | ------------------------------------------- |
| **Auth**         | Required                                    |
| **Method**       | `PATCH`                                     |
| **Path**         | `/api/learning/:goalId/sessions/:sessionId` |
| **Content-Type** | `application/json`                          |


### Allowed body fields only


| Field            | Type     | Values                            |
| ---------------- | -------- | --------------------------------- |
| `scheduled_date` | `string` | `YYYY-MM-DD` (local learning day) |
| `status`         | `string` | `completed` or `skipped`          |


Any other field → `400` `Invalid session fields: ...`  
Empty body → `400` `No valid session fields provided`

### Example request bodies

**Reschedule current session to another learning day:**

```json
{
  "scheduled_date": "2026-06-15"
}
```

**Mark current in-progress or overdue session complete:**

```json
{
  "status": "completed"
}
```

**Skip current unlocked-future session:**

```json
{
  "status": "skipped"
}
```

**Reschedule and complete in one call** (both fields allowed if rules pass for each):

```json
{
  "scheduled_date": "2026-06-15",
  "status": "completed"
}
```

### Date rules (same as chat reschedule)

- Goal must be **active**
- Only the **current** session can be rescheduled
- Not in the past (user timezone)
- Must fall on a **learning day** from user schedules
- No **quiet hours** conflict
- No **task overlap** on calendar
- May **rebase** later pending sessions + update plan `end_date`

### Status rules (same as chat)

- Goal must be **active**
- Only **current** session
- `completed` → session must be **`ongoing` or `overdue`**
- `skipped` → session must be **`unlocked_future`**
- Completed/skipped sessions cannot be edited → `400`

### Success `200`

```json
{
  "status": "success",
  "message": "Session updated",
  "data": {
    "timezone": "Asia/Karachi",
    "language": { "key": "python", "label": "Python" },
    "roadmap": {
      "id": "674a1b2c3d4e5f6789012301",
      "title": "Python basics",
      "language": "Python",
      "language_key": "python",
      "track_label": "Basics",
      "status": "active",
      "start_date": "2026-06-01",
      "end_date": "2026-07-20",
      "completed_topics": 2,
      "total_topics": 8,
      "progress_percent": 25,
      "session_count": 8,
      "sessions_summary": {
        "completed": 2,
        "skipped": 0,
        "pending": 6,
        "ongoing": 0
      },
      "sessions": []
    },
    "session": {
      "id": "674a1b2c3d4e5f6789012303",
      "order": 2,
      "title": "Control flow",
      "status": "completed",
      "scheduled_date": "2026-06-05T18:00:00+05:00",
      "estimated_duration": 90,
      "resources": [],
      "session_state": "completed",
      "is_current": false,
      "unlock_at": null,
      "completed_at": "2026-06-13T10:15:00+05:00"
    },
    "sessions": []
  }
}
```

Use `data.roadmap`, `data.session`, and `data.sessions` to refresh roadmap + detail screens. (`sessions` mirrors `roadmap.sessions` — prefer `roadmap.sessions` for full list.)

### Errors


| Status | When                                              |
| ------ | ------------------------------------------------- |
| `400`  | Validation, terminal session, inactive plan       |
| `401`  | Auth failure                                      |
| `404`  | Goal or session not found                         |
| `409`  | Locked, wrong session, overlap, quiet hours, etc. |


---

## `PATCH /api/learning/:goalId/status`

Pause, resume, or cancel a learning plan.


|                  |                                |
| ---------------- | ------------------------------ |
| **Auth**         | Required                       |
| **Method**       | `PATCH`                        |
| **Path**         | `/api/learning/:goalId/status` |
| **Content-Type** | `application/json`             |


### Request body


| Field    | Type     | Values                             |
| -------- | -------- | ---------------------------------- |
| `status` | `string` | `active`, `paused`, or `cancelled` |


`completed` is **not** allowed here (set by AI when all topics finish).

### Example request bodies

**Pause active plan:**

```json
{
  "status": "paused"
}
```

**Resume paused plan:**

```json
{
  "status": "active"
}
```

**Cancel / remove plan** (soft-delete + notifications):

```json
{
  "status": "cancelled"
}
```

### Success `200` — pause or resume

```json
{
  "status": "success",
  "message": "Learning goal updated",
  "data": {
    "timezone": "Asia/Karachi",
    "goal": {
      "_id": "674a1b2c3d4e5f6789012301",
      "title": "Python basics",
      "subject": "python",
      "status": "paused",
      "start_date": "2026-06-01",
      "end_date": "2026-07-15",
      "total_topics": 8,
      "completed_topics": 2
    }
  }
}
```

On resume (`status: "active"`), response may include optional `rebuild` from AI schedule rebase.

### Success `200` — cancel (`status: "cancelled"`)

```json
{
  "status": "success",
  "message": "Learning goal removed",
  "data": {
    "timezone": "Asia/Karachi",
    "goal": {
      "_id": "674a1b2c3d4e5f6789012301",
      "title": "Python basics",
      "status": "cancelled",
      "is_deleted": true
    },
    "notifications": {
      "requested": 1,
      "inserted": 1,
      "dispatched_push": 1,
      "dispatched_email": 0,
      "failed": 0,
      "results": []
    }
  }
}
```

### Errors


| Status | When                                                              |
| ------ | ----------------------------------------------------------------- |
| `400`  | Invalid status, wrong current status (e.g. pause when not active) |
| `401`  | Auth failure                                                      |
| `404`  | Goal not found                                                    |


---

## Frontend cheat sheet


| Screen action          | API | Example body |
| ---------------------- | --- | ------------ |
| Load all user plans | `GET /api/roadmaps/plans` | — |
| Open roadmap (sessions) | `GET /api/roadmaps/:goalId` | — |
| Open session popup     | `GET /api/learning/:goalId/sessions/:sessionId` | — |
| Show session detail    | Use `data.session` (or `roadmap.sessions[]` from list) | — |
| Change session date    | `PATCH /api/learning/:goalId/sessions/:sessionId` | `{ "scheduled_date": "2026-06-15" }` |
| Complete session       | `PATCH /api/learning/:goalId/sessions/:sessionId` | `{ "status": "completed" }` |
| Skip session           | `PATCH /api/learning/:goalId/sessions/:sessionId` | `{ "status": "skipped" }` |
| Pause plan             | `PATCH /api/learning/:goalId/status` | `{ "status": "paused" }` |
| Resume plan            | `PATCH /api/learning/:goalId/status` | `{ "status": "active" }` |
| Cancel / remove plan   | `PATCH /api/learning/:goalId/status` | `{ "status": "cancelled" }` |
| After mutation         | Refresh from `data.roadmap` + `data.session` | — |


---

## Session locking & unlocking (complete reference)

This section documents how **`status`**, **`is_current`**, **`unlock_at`**, and **`session_state`** work together on every `GET /api/roadmaps` response and after session mutations.

**Implementation (Node):** `Eva_Backend_Server/utils/learningSessionState.js`  
**Implementation (AI / chat):** `Eva_AI_Server/utils/learning_utils.py` (`compute_session_state`)  
Rules are aligned between REST API and chat.

### Stored vs computed


| Property        | Stored in MongoDB? | Collection        | Notes |
| --------------- | ------------------ | ----------------- | ----- |
| `status`        | **Yes**            | `roadmap_topics`  | Persisted session lifecycle value |
| `is_current`    | **No**             | —                 | Computed on every API read |
| `unlock_at`     | **No**             | —                 | Computed on every API read |
| `session_state` | **No**             | —                 | Computed on every API read |


`unlock_at` is returned in the user's timezone (ISO with offset), same as `scheduled_date`.

---

### `status` (persisted)

Written to `roadmap_topics.status` when a session is created or updated.


| `status` value | Meaning | How it is set |
| -------------- | ------- | ------------- |
| `pending`      | Not finished yet; may become the current session | Default when plan is created |
| `ongoing`      | Legacy / optional DB value | Rarely written in normal learning flow; API still treats `pending` + time window as **ongoing** via `session_state` |
| `completed`    | User finished the session | `PATCH` with `{ "status": "completed" }`, chat complete, or push “mark done” |
| `skipped`      | User skipped without doing it | `PATCH` with `{ "status": "skipped" }` or chat skip |


**Important:** During a live session window, the DB row usually stays `status: "pending"` while the API exposes `session_state: "ongoing"`. Use **`session_state`** for UI lock/buttons, not `status` alone.

`completed_at` is set in DB when `status` becomes `completed` or `skipped`.

---

### `is_current` (computed)

Exactly **one** session per active roadmap can be current.


| Value   | When |
| ------- | ---- |
| `true`  | This row is the **lowest `order`** among sessions where `status === "pending"` |
| `false` | Every other session (completed, skipped, or higher-order pending) |


Rules:

- Completed/skipped sessions are never current.
- Future pending sessions (order 3, 4, …) are **`is_current: false`** even if session 2 is done — only the next pending row is current.
- When the current session is **completed** or **skipped**, the next pending session automatically becomes current on the next `GET`.
- If all sessions are terminal, **no** session has `is_current: true`.

Only the **current** session may be rescheduled, completed, or skipped (API + chat).

---

### `unlock_at` (computed)

Tells the UI **when a locked current session becomes actionable**.


| Value | When |
| ----- | ---- |
| ISO datetime | `is_current === true` **and** `session_state === "locked"` |
| `null`       | All other cases |


**Formula (default — sessions ≥ 24h apart):**

```
unlock_at = scheduled_date − 24 hours
```

**Short-gap rule** — if the gap between this session and the **previous** session’s `scheduled_date` is **&lt; 24 hours**:

```
unlock_at = previous session's completed_at (or updated_at if no completed_at)
            — OR scheduled_date if previous is not resolved yet
```

Intuition: you cannot work ahead on session N+1 until session N is done when sessions are back-to-back.

`unlock_at` is **informational** for countdown UI. The server re-evaluates `session_state` on every request using server time.

---

### `session_state` (computed)

Runtime lock state for the **current** pending session. Non-current sessions get a simpler label.


#### Non-current sessions


| DB `status` | `session_state` | `is_current` | `unlock_at` |
| ----------- | --------------- | ------------ | ----------- |
| `completed` | `completed`     | `false`      | `null`      |
| `skipped`   | `skipped`       | `false`      | `null`      |
| `pending`   | `upcoming`      | `false`      | `null`      |


`upcoming` = waiting in queue; not interactable yet.

#### Current session (`is_current: true`)

Evaluated in order below (first match wins):

```
1. If DB status is completed/skipped → session_state = that status (terminal)
2. If no scheduled_date → locked
3. If now < unlock_at → locked
4. If now < scheduled_date → unlocked_future
5. If now < scheduled_date + estimated_duration → ongoing
6. Else → overdue
```

Default `estimated_duration` = **90 minutes** if missing.


| `session_state`   | Time window (current session) | Reschedule | Skip | Complete |
| ----------------- | ------------------------------- | ---------- | ---- | -------- |
| `locked`          | Before `unlock_at`            | no         | no   | no       |
| `unlocked_future` | From `unlock_at` until `scheduled_date` | yes | yes  | no       |
| `ongoing`         | From `scheduled_date` until `scheduled_date + duration` | yes | no   | yes      |
| `overdue`         | After session window ends       | yes        | no   | yes      |
| `completed`       | Terminal                        | no         | no   | no       |
| `skipped`         | Terminal                        | no         | no   | no       |


**Timeline example** (session scheduled 18:00, 90 min, first session in plan):

```
        locked          unlocked_future      ongoing              overdue
|----------|----------------|------------------------|------------------->
      unlock_at      scheduled_date      window_end (19:30)
   (24h before)         (18:00)
```

---

### Case-by-case matrix (all session positions)

Assume sessions 1–4, server time = **now**.


| Session | DB `status` | Position | `is_current` | `session_state` | `unlock_at` |
| ------- | ----------- | -------- | ------------ | --------------- | ----------- |
| 1 | `completed` | Past, done | `false` | `completed` | `null` |
| 2 | `skipped` | Past, skipped | `false` | `skipped` | `null` |
| 3 | `pending` | **Current**, 3 days before schedule | `true` | `locked` | `scheduled − 24h` (or short-gap rule) |
| 3 | `pending` | **Current**, inside 24h before schedule | `true` | `unlocked_future` | `null` |
| 3 | `pending` | **Current**, during 18:00–19:30 window | `true` | `ongoing` | `null` |
| 3 | `pending` | **Current**, after 19:30 | `true` | `overdue` | `null` |
| 4 | `pending` | Future queue | `false` | `upcoming` | `null` |


---

### Short-gap examples

**Sessions 6h apart** (09:00 then 15:00), session 1 completed at 10:00:

| Moment | Session 2 `session_state` | Why |
| ------ | ------------------------- | --- |
| 10:30  | `unlocked_future` | `unlock_at` = 10:00 (when session 1 resolved), now past unlock |
| 09:30 (session 1 still pending) | `locked` | Previous not resolved → unlock stays at 15:00 schedule |

---

### What happens after user actions

#### Complete current session (`status → completed`)

1. DB: current topic `status = completed`, `completed_at` set.
2. Linked calendar task → `complete`.
3. Goal `completed_topics` incremented; if all done → goal `status = completed`.
4. Next lowest-order `pending` topic becomes **`is_current: true`**.
5. Its `session_state` recomputed (often `locked` or `unlocked_future` depending on schedule gap).

#### Skip current session (`status → skipped`)

Same as complete for “advance queue”, but topic is `skipped` (counts toward progress differently in `sessions_summary`).

#### Reschedule current session (`scheduled_date` change)

1. Only allowed when `session_state` is **`locked`**, **`unlocked_future`**, **`ongoing`**, or **`overdue`** (not terminal).
2. Blocked when `session_state === locked` → `409` / chat blocked message.
3. New date must be a learning day, not in the past, no overlaps/quiet hours.
4. May **rebase** later pending sessions and extend goal `end_date`.
5. `unlock_at` recalculated from new `scheduled_date`.

#### Pause / resume / cancel plan (`PATCH .../status`)

| Goal `status` | Effect on locking fields |
| ------------- | ------------------------ |
| `active` | Locking computed normally; mutations allowed per rules above |
| `paused` | `GET` still returns sessions + computed states; **session PATCH rejected** (`400`) |
| `cancelled` | Plan soft-deleted; roadmap may not appear in default fetch |
| `completed` | All sessions terminal or plan finished; no current interactable session |


---

### API errors tied to lock state


| Action | Blocked when | HTTP |
| ------ | ------------ | ---- |
| Reschedule | Not current, or `locked`, or goal not `active` | `409` / `400` |
| Skip | Not current, or `locked` / `ongoing` / `overdue` | `409` |
| Complete | Not current, or `locked` / `unlocked_future` | `409` |
| Any change | `status` already `completed` / `skipped` | `400` |


Representative messages:

- *"That session is still locked. It unlocks within 24 hours of its scheduled time."*
- *"That session has not started yet. Reschedule or skip it instead of marking it complete."*
- *"Only the current session can be …"*

---

### Frontend guidance


| UI need | Use this field |
| ------- | -------------- |
| Show lock icon / countdown | `session_state === "locked"` + `unlock_at` |
| Enable “Start / Complete” | `session_state` in `ongoing`, `overdue` |
| Enable “Skip” | `session_state === "unlocked_future"` |
| Enable “Reschedule” | `session_state` in `unlocked_future`, `ongoing`, `overdue` (not `locked`) |
| Highlight active row | `is_current === true` |
| Progress chips | DB `status` + `sessions_summary` |
| Read-only past sessions | `session_state` in `completed`, `skipped` |

Always refresh from `data.roadmap.sessions` after `PATCH` — `is_current`, `unlock_at`, and `session_state` all change together when the queue advances.


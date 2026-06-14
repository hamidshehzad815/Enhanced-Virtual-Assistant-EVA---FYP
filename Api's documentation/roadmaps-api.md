# Roadmaps API

User learning roadmaps (goals + sessions).

See [README.md](./README.md) for auth and error envelopes.

---

## Available endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/roadmaps/languages` | Language dropdown |
| `GET` | `/api/roadmaps?language=<key>` | Roadmap + sessions for one language |
| `PATCH` | `/api/learning/:goalId/sessions/:sessionId` | Reschedule, complete, or skip a session |
| `PATCH` | `/api/learning/:goalId/status` | Pause, resume, or cancel a plan |

---

## UX flow (Approach B)

1. Open Roadmap screen → show **“Select language”** placeholder (no roadmap fetch yet).
2. `GET /api/roadmaps/languages` → populate dropdown.
3. User picks language → `GET /api/roadmaps?language=<key>` → render roadmap + sessions.
4. Tap session → session detail (data from `roadmap.sessions[]`).
5. After any mutation → use response `data.roadmap` / `data.session` to refresh UI.

---

## Resolution rules


| Rule                         | Behavior                                                                                              |
| ---------------------------- | ----------------------------------------------------------------------------------------------------- |
| One language at a time in UI | API returns **one** `roadmap` object per language query                                               |
| Chat create (same language)  | Blocked while any **active** or **paused** plan exists; complete, cancel, or delete first           |
| Multiple goals same language | Prefer **active** → **paused** → **completed** → **cancelled** (newest `updated_at` within same tier) |
| Only completed exists        | Return that completed roadmap                                                                         |
| No roadmap for language      | `roadmap: null`                                                                                       |


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


Use `status` + `session_state` to decide what the session detail screen may offer. The frontend shows update options; the server enforces rules.

| `session_state`   | Reschedule | Skip | Complete |
| ----------------- | ---------- | ---- | -------- |
| `locked`          | no         | no   | no       |
| `unlocked_future` | yes        | yes  | no       |
| `ongoing`         | yes        | no   | yes      |
| `overdue`         | yes        | no   | yes      |

`ongoing` = from scheduled start through `estimated_duration` (default 90 min). `overdue` = after that window ends.

---

## `GET /api/roadmaps/languages`

Languages the user has at least one roadmap for.


|            |                           |
| ---------- | ------------------------- |
| **Auth**   | Required                  |
| **Method** | `GET`                     |
| **Path**   | `/api/roadmaps/languages` |
| **Body**   | None                      |


### Example request

```http
GET /api/roadmaps/languages HTTP/1.1
Authorization: Bearer <access_token>
```

### Success `200`

```json
{
  "status": "success",
  "data": {
    "languages": [
      { "key": "python", "label": "Python" },
      { "key": "javascript", "label": "JavaScript" }
    ]
  }
}
```

---

## `GET /api/roadmaps?language=<key>`

Load the roadmap for one language. **`language` is required** (Approach B).


|                      |                                                                          |
| -------------------- | ------------------------------------------------------------------------ |
| **Auth**             | Required                                                                 |
| **Method**           | `GET`                                                                    |
| **Path**             | `/api/roadmaps`                                                          |
| **Query**            | `language` (required) — also accepts `lang` or `subject` as alias        |
| **Query (optional)** | `status` — comma-separated: `active`, `paused`, `completed`, `cancelled` |
| **Body**             | None                                                                     |


### Example requests

```http
GET /api/roadmaps?language=python HTTP/1.1
Authorization: Bearer <access_token>
```

```http
GET /api/roadmaps?language=python&status=active,paused HTTP/1.1
Authorization: Bearer <access_token>
```

### Success `200` — roadmap found

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
          "completed_at": "2026-06-03T19:30:00+05:00"
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

### Success `200` — no roadmap for language

```json
{
  "status": "success",
  "data": {
    "timezone": "Asia/Karachi",
    "language": { "key": "python", "label": "Python" },
    "roadmap": null
  }
}
```

### Errors


| Status | When                                          |
| ------ | --------------------------------------------- |
| `400`  | Missing `language` or invalid `status` filter |
| `401`  | Auth failure                                  |


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
| Open roadmap tab       | — | — |
| Load language dropdown | `GET /api/roadmaps/languages` | — |
| User selects language  | `GET /api/roadmaps?language=python` | — |
| Show session detail    | Use `roadmap.sessions[]` (match `id`) | — |
| Change session date    | `PATCH /api/learning/:goalId/sessions/:sessionId` | `{ "scheduled_date": "2026-06-15" }` |
| Complete session       | `PATCH /api/learning/:goalId/sessions/:sessionId` | `{ "status": "completed" }` |
| Skip session           | `PATCH /api/learning/:goalId/sessions/:sessionId` | `{ "status": "skipped" }` |
| Pause plan             | `PATCH /api/learning/:goalId/status` | `{ "status": "paused" }` |
| Resume plan            | `PATCH /api/learning/:goalId/status` | `{ "status": "active" }` |
| Cancel / remove plan   | `PATCH /api/learning/:goalId/status` | `{ "status": "cancelled" }` |
| After mutation         | Refresh from `data.roadmap` + `data.session` | — |



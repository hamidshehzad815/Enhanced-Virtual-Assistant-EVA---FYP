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


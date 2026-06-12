# Roadmaps API

User learning roadmaps (goals + sessions). **Reads** live under `/api/roadmaps`. **Writes** (session/plan actions) live under `/api/learning`.

See [README.md](./README.md) for auth and error envelopes.

---

## UX flow (Approach B)

1. Open Roadmap screen → show **“Select language”** placeholder (no roadmap fetch yet).
2. `GET /api/roadmaps/languages` → populate dropdown.
3. User picks language → `GET /api/roadmaps?language=<key>` → render roadmap + sessions.
4. Tap session → session detail (data from `roadmap.sessions[]`).
5. After any mutation → use response `data.roadmap` / `data.session` to refresh UI.

---

## Resolution rules

| Rule | Behavior |
|------|----------|
| One language at a time in UI | API returns **one** `roadmap` object per language query |
| Multiple goals same language | Prefer **active** → **paused** → **completed** → **cancelled** (newest `updated_at` within same tier) |
| Only completed exists | Return that completed roadmap |
| No roadmap for language | `roadmap: null` |

---

## `GET /api/roadmaps/languages`

Languages the user has at least one roadmap for.

| | |
|---|---|
| **Auth** | Required |
| **Method** | `GET` |
| **Path** | `/api/roadmaps/languages` |

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

| | |
|---|---|
| **Auth** | Required |
| **Method** | `GET` |
| **Path** | `/api/roadmaps` |
| **Query** | `language` (required) — also accepts `lang` or `subject` as alias |
| **Query (optional)** | `status` — comma-separated: `active`, `paused`, `completed`, `cancelled` |

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

| Status | When |
|--------|------|
| `400` | Missing `language` or invalid `status` filter |
| `401` | Auth failure |

---

## Session object (`roadmap.sessions[]`)

| Field | Type | Notes |
|-------|------|-------|
| `id` | `string` | Session (topic) id |
| `order` | `number` | 1-based order in plan |
| `title` | `string` | Read-only |
| `status` | `string` | `pending`, `ongoing`, `completed`, `skipped` — **current value from server** |
| `scheduled_date` | `string \| null` | ISO datetime in user TZ |
| `estimated_duration` | `number` | Minutes — read-only |
| `resources` | `array` | `{ title, url, thumbnail?, channel_name? }` — read-only |
| `session_state` | `string` | Computed: `locked`, `unlocked_future`, `overdue`, `completed`, `skipped`, `upcoming` |
| `is_current` | `boolean` | `true` for the current pending session |
| `unlock_at` | `string \| null` | When locked current session becomes actionable |
| `completed_at` | `string \| null` | Only when `status` is `completed` or `skipped` |

Use `status` + `session_state` to decide what the session detail screen may offer. The frontend shows update options; the server enforces rules.

---

## `PATCH /api/learning/:goalId/sessions/:sessionId`

Update session **date** and/or **status** (same rules as chat).

| | |
|---|---|
| **Auth** | Required |
| **Method** | `PATCH` |
| **Path** | `/api/learning/:goalId/sessions/:sessionId` |
| **Content-Type** | `application/json` |

### Allowed body fields only

| Field | Type | Values |
|-------|------|--------|
| `scheduled_date` | `string` | `YYYY-MM-DD` (local learning day) |
| `status` | `string` | `completed` or `skipped` |

Any other field → `400` `Invalid session fields: ...`

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
- `completed` → session must be **overdue**
- `skipped` → session must be **unlocked_future**
- Completed/skipped sessions cannot be edited → `400`

### Success `200`

```json
{
  "status": "success",
  "message": "Session updated",
  "data": {
    "timezone": "Asia/Karachi",
    "language": { "key": "python", "label": "Python" },
    "roadmap": { },
    "session": { },
    "sessions": [ ]
  }
}
```

Use `data.roadmap`, `data.session`, and `data.sessions` to refresh roadmap + detail screens.

### Errors

| Status | When |
|--------|------|
| `400` | Validation, terminal session, inactive plan |
| `401` | Auth failure |
| `404` | Goal or session not found |
| `409` | Locked, wrong session, overlap, quiet hours, etc. |

---

## Other learning write endpoints

These also return refreshed `roadmap` / `session` / `sessions` where applicable.

| Method | Path | Body | Purpose |
|--------|------|------|---------|
| `POST` | `/api/learning/:goalId/topics/:topicId/complete` | — | Mark current overdue session complete |
| `POST` | `/api/learning/:goalId/topics/:topicId/skip` | — | Skip current unlocked session |
| `PATCH` | `/api/learning/:goalId/status` | `{ "status": "active" \| "paused" \| "cancelled" }` | Pause / resume / cancel plan |
| `DELETE` | `/api/learning/:goalId` | — | Remove plan |

---

## Removed read endpoints (do not use)

| Old route | Replacement |
|-----------|-------------|
| `GET /api/learning` | `GET /api/roadmaps/languages` + `GET /api/roadmaps?language=` |
| `GET /api/learning/:id` | `GET /api/roadmaps?language=` |
| `GET /api/learning/:id/topics` | Sessions inside `roadmap.sessions` |

---

## Frontend cheat sheet

| Screen action | API |
|---------------|-----|
| Open roadmap tab | Show placeholder only |
| Load language dropdown | `GET /api/roadmaps/languages` |
| User selects language | `GET /api/roadmaps?language=python` |
| Show session detail | Use session from `roadmap.sessions` (match `id`) |
| Change session date | `PATCH .../sessions/:id` `{ "scheduled_date": "2026-06-15" }` |
| Complete / skip session | `PATCH` with `status` **or** legacy `POST .../complete` / `.../skip` |
| After mutation | Bind UI from response `data.roadmap` + `data.session` |

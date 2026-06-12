# EVA Backend API Documentation (Frontend)

Focused reference for **Dashboard**, **Settings**, and **Profile** APIs on the Node backend (`Eva_Backend_Server`).

## Base URL

```
http://<host>:<port>/api
```

Default port is from `BACKEND_PORT` in `.env` (commonly `3500` or `4500` in local dev).

## Authentication

All endpoints in this folder require a logged-in user.

| Header | Value |
|--------|--------|
| `Authorization` | `Bearer <access_token>` |
| `Content-Type` | `application/json` (for PATCH bodies). Avatar upload uses `multipart/form-data` — see [profile-api.md](./profile-api.md). |

Get `access_token` from `POST /api/auth/login` → `data.tokens.access_token`.

## Standard success envelope

```json
{
  "status": "success",
  "data": { }
}
```

Some endpoints also include `"message": "..."`.

## Standard error envelope

```json
{
  "status": "fail",
  "message": "Human-readable error"
}
```

Conflict responses (`409`) may include extra context:

```json
{
  "status": "fail",
  "message": "Learning schedule \"Morning\" conflicts with existing tasks",
  "data": {
    "timezone": "Asia/Karachi",
    "conflicts": [ ],
    "schedule_id": "s1",
    "schedule_label": "Morning"
  }
}
```

| HTTP | Meaning |
|------|---------|
| `400` | Bad request / validation |
| `401` | Missing or invalid token |
| `404` | Route or resource not found |
| `409` | Conflict (schedule in use, task overlap, quiet hours, etc.) |
| `422` | Mongoose validation (rare on these routes) |
| `429` | Rate limit (e.g. avatar uploads) |
| `502` | Upstream failure (e.g. Cloudinary) |
| `500` | Server error |

## Timezone convention

- API datetimes are returned as **ISO-8601 with offset** in the user's timezone (e.g. `2026-06-05T15:00:00+05:00`).
- Many payloads include a top-level `timezone` field (IANA string, e.g. `"Asia/Karachi"`).
- `day` / `time` strings on dashboard tasks are **pre-formatted for display** in the user's timezone (`"Thursday"`, `"3:00 PM"`).

## Files in this folder

| File | APIs covered |
|------|----------------|
| [dashboard-api.md](./dashboard-api.md) | `GET /api/dashboard` |
| [settings-api.md](./settings-api.md) | `GET /api/settings`, `PATCH /api/settings` |
| [settings-learning-schedules-api.md](./settings-learning-schedules-api.md) | Learning schedule CRUD under `/api/settings/learning-schedules` |
| [profile-api.md](./profile-api.md) | `GET` / `PATCH /api/profile`, `POST /api/profile/avatar` |

## Quick frontend map

| Screen | Read | Write |
|--------|------|-------|
| Home / Dashboard | `GET /api/dashboard` | — |
| Profile (name, username, photo, timezone) | `GET /api/profile` | `PATCH /api/profile`, `POST /api/profile/avatar` |
| Settings (toggles, quiet hours, reminders) | `GET /api/settings` | `PATCH /api/settings` |
| Learning schedules UI | `GET /api/settings` or `GET /api/settings/learning-schedules` | `POST` / `PATCH` / `DELETE` on `/api/settings/learning-schedules` |

**Do not** update `preferred_learning_schedules` via `PATCH /api/settings`. Use the learning-schedules CRUD routes only.

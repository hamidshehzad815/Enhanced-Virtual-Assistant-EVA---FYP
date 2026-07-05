# EVA Backend API Documentation (Frontend)

Focused reference for **Auth**, **Dashboard**, **Settings**, **Profile**, and **Roadmaps** APIs on the Node backend (`Eva_Backend_Server`).

## Base URL

```
http://<host>:<port>/api
```

Default port is from `BACKEND_PORT` in `.env` (commonly `3500` or `4500` in local dev).

## Authentication

Most endpoints in this folder require a logged-in user. **Auth routes** (`/api/auth/*`) are documented in [auth-api.md](./auth-api.md) — register, login, refresh, and password reset are public; logout and `me` require a token.

| Header | Value |
|--------|--------|
| `Authorization` | `Bearer <access_token>` |
| `Content-Type` | `application/json` (for PATCH bodies). Avatar upload uses `multipart/form-data` — see [profile-api.md](./profile-api.md). |

Get `access_token` from `POST /api/auth/login` or `POST /api/auth/google` → `data.tokens.access_token`. See [auth-api.md](./auth-api.md) and [google-auth-api.md](./google-auth-api.md) for full flows.

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
| [auth-api.md](./auth-api.md) | `POST /api/auth/register`, `login`, `google`, `refresh`, `logout`, `forgot-password`, `reset-password`, `resend-verification`; `GET /api/auth/me`, `verify-email` |
| [google-auth-api.md](./google-auth-api.md) | **`POST /api/auth/google`** — Google Sign-In flow, request/response, frontend integration notes |
| [dashboard-api.md](./dashboard-api.md) | `GET /api/dashboard` |
| [settings-api.md](./settings-api.md) | `GET /api/settings`, `PATCH /api/settings` |
| [settings-learning-schedules-api.md](./settings-learning-schedules-api.md) | Learning schedule CRUD under `/api/settings/learning-schedules` |
| [profile-api.md](./profile-api.md) | `GET` / `PATCH /api/profile`, `POST` / `DELETE /api/profile/avatar`, `DELETE /api/profile/account` |
| [roadmaps-api.md](./roadmaps-api.md) | `GET /api/roadmaps/*`, `GET /api/learning/:goalId/sessions/:sessionId`, `PATCH /api/learning/:goalId/sessions/:sessionId`, `PATCH /api/learning/:goalId/status` |
| [roadmaps-frontend-actions-guide.md](./roadmaps-frontend-actions-guide.md) | **UI tables:** plan/session actions, buttons by `session_state`, popup fields (frontend) |
| [tasks-api.md](./tasks-api.md) | `GET /api/tasks/calendar`, `GET /api/tasks/:id`, `PATCH /api/tasks/:id`, `DELETE /api/tasks/:id` |
| [friends-api.md](./friends-api.md) | `POST /api/friends/request`, `GET /api/friends`, `GET /api/friends/requests`, `GET /api/friends/search`, `PATCH /api/friends/:id/respond`, `DELETE /api/friends/:id` |
| [push-notifications-frontend-setup.md](./push-notifications-frontend-setup.md) | FCM / push token registration (Flutter setup guide) |

## Quick frontend map

| Screen | Read | Write |
|--------|------|-------|
| Sign up / Login / Forgot password | — | [auth-api.md](./auth-api.md): `register`, `login`, `refresh`, `forgot-password`, `reset-password`, `resend-verification` |
| Google Sign-In | — | [google-auth-api.md](./google-auth-api.md): `POST /api/auth/google` |
| App bootstrap (after login) | `GET /api/auth/me` | `POST /api/auth/logout` |
| Home / Dashboard | `GET /api/dashboard` | — |
| Profile (name, username, photo, timezone, delete account) | `GET /api/profile` | `PATCH /api/profile`, `POST` / `DELETE /api/profile/avatar`, `DELETE /api/profile/account` |
| Roadmap (plans list) | `GET /api/roadmaps/plans`, `GET /api/roadmaps/:goalId`, `GET /api/learning/:goalId/sessions/:sessionId` | `PATCH /api/learning/:goalId/sessions/:sessionId`, `PATCH /api/learning/:goalId/status` — see [roadmaps-frontend-actions-guide.md](./roadmaps-frontend-actions-guide.md) |
| Settings (toggles, quiet hours, reminders) | `GET /api/settings` | `PATCH /api/settings` |
| Push device token (after login) | — | `PATCH /api/settings` with `push_token` — see [push-notifications-frontend-setup.md](./push-notifications-frontend-setup.md) |
| Learning schedules UI | `GET /api/settings` or `GET /api/settings/learning-schedules` | `POST` / `PATCH` / `DELETE` on `/api/settings/learning-schedules` |
| Calendar | `GET /api/tasks/calendar`, `GET /api/tasks/:id` | `PATCH /api/tasks/:id`, `DELETE /api/tasks/:id` — see [tasks-api.md](./tasks-api.md) |
| Collaboration / Friends | `GET /api/friends`, `GET /api/friends/requests`, `GET /api/friends/search` | `POST /api/friends/request`, `PATCH /api/friends/:id/respond`, `DELETE /api/friends/:id` — see [friends-api.md](./friends-api.md) |

**Do not** update `preferred_learning_schedules` via `PATCH /api/settings`. Use the learning-schedules CRUD routes only.

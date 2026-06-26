# EVA Backend API Documentation

Last updated: 2026-05-20  
Source of truth: backend code in `Eva_Backend_Server` (routes/controllers/models/middleware)

## 1. Overview

- Runtime: Node.js + Express
- Default port: `3000` (`BACKEND_PORT`)
- Base route mount:
  - Root/health: `/`, `/health`
  - API base: `/api/*`
- Security middleware:
  - `helmet`
  - `cors` with `origin: true`, credentials enabled
  - Rate limiting on `/api`: **100 requests / 15 minutes / IP**
- Request size limits:
  - JSON: `10mb`
  - URL-encoded: `10mb`
- Response header:
  - `X-Request-ID` added for each request

## 2. Global Conventions

## 2.1 Authentication

- Protected endpoints require:
  - `Authorization: Bearer <access_token>`
- Access tokens are JWT signed with `JWT_ACCESS_SECRET`.
- Common auth failures:
  - Missing token -> `401 Access token required`
  - Expired token -> `401 Access token expired`
  - Invalid token -> `401 Invalid access token`
  - Inactive/non-existent user -> `401`

## 2.2 Standard Success/Error Shapes

Most JSON success responses use:

```json
{
  "status": "success",
  "message": "optional",
  "data": {}
}
```

Global error middleware returns:

```json
{
  "status": "fail|error",
  "message": "Error message",
  "data": {},
  "errors": [],
  "stack": "only in development"
}
```

Notes:
- `data` appears for conflict payloads and some structured errors.
- Some endpoints return **HTML** (email verification + collaboration link actions), not JSON.

## 2.3 Timezone and Date Rules

- User default timezone in model: `Asia/Karachi`.
- Local-day filters (example: task date filter, dashboard today) are converted from user timezone to UTC server queries.
- Date-only filters generally expect `YYYY-MM-DD`.

## 2.4 Status and Display Semantics

- Task DB status: `pending | complete` (legacy `ongoing` may still exist in old docs).
- API normalizes task status to `pending|complete`.
- UI display status is derived:
  - `pending | ongoing | overdue | complete`

## 2.5 Learning Schedule Day Mapping

- Learning schedule weekday values:
  - `0=Monday`, `1=Tuesday`, ..., `6=Sunday`

---

## 3. Endpoint Catalog (Quick List)

### Health
- `GET /`
- `GET /health`

### Auth
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout` (protected)
- `GET /api/auth/me` (protected)
- `GET /api/auth/verify-email`
- `POST /api/auth/resend-verification`
- `POST /api/auth/forgot-password`
- `POST /api/auth/reset-password`

### Profile
- `GET /api/profile` (protected)
- `PATCH /api/profile` (protected)
- `DELETE /api/profile/account` (protected)

### Chat
- `POST /api/chat/session` (protected)
- `POST /api/chat/process` (protected)

### Tasks
- `GET /api/tasks/collaboration/respond` (link-based HTML)
- `GET /api/tasks` (protected)
- `GET /api/tasks/:id` (protected)
- `PATCH /api/tasks/:id/status` (protected)
- `DELETE /api/tasks/:id` (protected)
- `POST /api/tasks/:id/collaborators/respond` (protected)

### Learning
- `GET /api/learning/collaboration/respond` (link-based HTML)
- `PATCH /api/learning/:goalId/sessions/:sessionId` (protected)
- `PATCH /api/learning/:goalId/status` (protected)
- `POST /api/learning/:goalId/collaborators/respond` (protected)

### Settings
- `GET /api/settings` (protected)
- `PATCH /api/settings` (protected)
- `GET /api/settings/learning-schedules` (protected)
- `POST /api/settings/learning-schedules` (protected)
- `PATCH /api/settings/learning-schedules/:scheduleId` (protected)
- `DELETE /api/settings/learning-schedules/:scheduleId` (protected)

### Integrations
- `POST /api/integrations/google/connect` (protected)
- `GET /api/integrations` (protected)

### Analytics
- `GET /api/analytics/dashboard` (protected) — unified payload (`?days=7|30|90`)

### Friends
- `POST /api/friends/request` (protected)
- `GET /api/friends` (protected)
- `GET /api/friends/requests` (protected)
- `GET /api/friends/blocked` (protected)
- `GET /api/friends/search` (protected)
- `PATCH /api/friends/:id/respond` (protected)
- `POST /api/friends/block/:userId` (protected)
- `POST /api/friends/unblock/:userId` (protected)
- `DELETE /api/friends/:id` (protected)

### Dashboard
- `GET /api/dashboard` (protected)

---

## 4. Detailed API Reference

## 4.1 Health APIs

### `GET /`
- Auth: No
- Purpose: root sanity endpoint.
- Response:
  - `200`:
```json
{
  "service": "EVA Backend Server",
  "version": "1.0.0",
  "status": "running"
}
```

### `GET /health`
- Auth: No
- Purpose: checks MongoDB + AI server health.
- Response:
  - `200` when both healthy, else `503`.
```json
{
  "status": "ok|degraded",
  "service": "eva-backend",
  "timestamp": "ISO_DATE",
  "connections": {
    "mongodb": "connected|disconnected",
    "ai_server": "connected|disconnected"
  }
}
```

---

## 4.2 Auth APIs

### `POST /api/auth/register`
- Auth: No
- Body:
```json
{
  "name": "string (required)",
  "username": "string (required, lowercase/unique)",
  "email": "string (required, unique)",
  "password": "string (required, min 6)",
  "timezone": "string (optional, normalized)"
}
```
- Behavior:
  - Creates `User`
  - Creates default `UserSetting`
  - Sends verification email token (24h expiry)
- Success:
  - `201`
```json
{
  "status": "success",
  "message": "Registration successful...",
  "data": {
    "user": {
      "_id": "...",
      "name": "...",
      "username": "...",
      "email": "...",
      "is_verified": false
    },
    "email_sent": true
  }
}
```
- Common errors:
  - `400` missing required fields
  - `409` email already registered / username already taken

### `POST /api/auth/login`
- Auth: No
- Body:
```json
{
  "email": "string",
  "password": "string"
}
```
- Success:
  - `200` with `access_token` + `refresh_token`
- Common errors:
  - `401` invalid credentials
  - `401` account deactivated
  - `401` email not verified
  - `401` local password missing (google-only account)

### `POST /api/auth/refresh`
- Auth: No
- Body:
```json
{
  "refresh_token": "string"
}
```
- Behavior:
  - Verifies refresh JWT
  - Checks stored refresh hash
  - Rotates refresh token
- Success: `200` with new access/refresh tokens
- Common errors:
  - `400` missing token
  - `401` invalid/expired/invalidated token

### `POST /api/auth/logout`
- Auth: Yes
- Behavior: clears user refresh token hash.
- Success: `200 { status: "success", message: "Logged out successfully" }`

### `GET /api/auth/me`
- Auth: Yes
- Response:
  - current user + selected settings fields.

### `GET /api/auth/verify-email?token=<token>`
- Auth: No
- Response type: **HTML**
- Behavior:
  - Validates hashed token + expiry
  - Marks `is_verified=true`
  - Clears verification token fields
- Status:
  - `200` verified page
  - `400` invalid/expired/missing token page
  - `500` failure page

### `POST /api/auth/resend-verification`
- Auth: No
- Body: `{ "email": "string" }`
- Behavior:
  - Generic success message if account missing (anti-enumeration)
  - Regenerates token if account exists and not verified
- Errors:
  - `400` email required
  - `400` already verified

### `POST /api/auth/forgot-password`
- Auth: No
- Body: `{ "email": "string" }`
- Behavior:
  - Always returns generic success text
  - For active local-auth account: creates reset token (1h) and emails link
- Error:
  - `400` email required

### `POST /api/auth/reset-password`
- Auth: No
- Body:
```json
{
  "token": "string",
  "new_password": "string",
  "confirm_password": "string"
}
```
- Rules:
  - all fields required
  - min 6 chars
  - passwords must match
- Behavior:
  - validates hashed token + expiry + active user
  - updates password
  - clears reset token
  - clears refresh token hash (forces fresh login)
- Errors:
  - `400` validation failure / invalid or expired token

---

## 4.3 Profile APIs

### `GET /api/profile`
- Auth: Yes
- Returns user public profile (`toPublicProfile()`).

### `PATCH /api/profile`
- Auth: Yes
- Allowed fields only:
  - `name`, `username`, `bio`, `university`, `department`, `semester`, `timezone`
- Notes:
  - Invalid fields rejected
  - Username uniqueness enforced
  - Profile pictures are **not** updated here — use `POST /api/profile/avatar`
- Success:
  - `200` with updated public profile
- Common errors:
  - `400` invalid fields / empty required field
  - `409` username already taken

### `POST /api/profile/avatar`
- Auth: Yes
- Content-Type: `multipart/form-data`
- Form field: `avatar` (single image file)
- Allowed types: JPEG, PNG, WebP (max 2 MB by default)
- Success:
  - `200` with updated public profile (`profile_picture` URL)
- Notes:
  - First upload and replace use the same endpoint
  - Previous Cloudinary image is deleted on replace
- Env required:
  - `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`
  - Optional: `CLOUDINARY_PROFILE_FOLDER` (default `eva/profile-pictures`)
  - Optional: `AVATAR_MAX_SIZE_MB` (default `2`)
- Common errors:
  - `400` missing/invalid file
  - `401` unauthorized
  - `502` Cloudinary upload failed
  - `503` Cloudinary not configured
  - `429` too many uploads (10/hour per IP)

### `DELETE /api/profile/account`
- Auth: Yes
- Body (local accounts): `{ "password": "string" }` (required)
- Body (Google-only): none required
- Behavior:
  - Soft-deletes account (`is_active=false`), anonymizes email/username
  - Clears refresh token, password, push tokens, avatar (Cloudinary)
  - Soft-deletes owned tasks, learning plans, chat sessions; removes friendships
- Success: `200 { status: "success", message: "Account deleted successfully" }`
- Common errors:
  - `400` password required (local)
  - `401` invalid password / token
  - `429` rate limit (5/hour per IP)

---

## 4.4 Chat APIs

### `POST /api/chat/session`
- Auth: Yes
- Body:
```json
{
  "title": "string (optional)"
}
```
- Success:
  - `201`
  - Creates `ChatSession` for current user.

### `POST /api/chat/process`
- Auth: Yes
- Body:
```json
{
  "message": "string (required)",
  "session_id": "ObjectId string (required)",
  "input_type": "text|voice (optional, default text)"
}
```
- Behavior:
  - validates session ownership
  - forwards payload to AI server `/process`
  - inserts/dispatches notifications returned by AI
- Success:
```json
{
  "status": "success",
  "response_text": "...",
  "session_id": "...",
  "intent": "route intent or null",
  "ai_status": "handler_status or status from AI",
  "notifications": {
    "requested": 0,
    "inserted": 0,
    "dispatched_push": 0,
    "dispatched_email": 0,
    "failed": 0,
    "results": []
  },
  "data": {}
}
```
- Errors:
  - `400` invalid input/session id/input_type
  - `404` chat session not found
  - `500` AI unavailable / notification dispatch failure

---

## 4.5 Task APIs

### `GET /api/tasks`
- Auth: Yes
- Query params:
  - `page` (default 1)
  - `limit` (default 20, max 100)
  - `status` aliases accepted; normalized to:
    - `pending` group = `pending|ongoing`
    - `complete` group = `complete`
  - `priority` aliases accepted; normalized to `low|medium|high`
  - `date` (`YYYY-MM-DD`, interpreted in user timezone)
  - `subject` (regex search against title, case-insensitive)
- Important behavior:
  - Only tasks where current user is `owner_id`.
  - If `date` not provided and status filter is not `complete`, query auto-filters to future tasks (`due_datetime >= now`).
- Response:
```json
{
  "status": "success",
  "data": {
    "tasks": [
      {
        "...task fields": "...",
        "status": "pending|complete",
        "display_status": "pending|ongoing|overdue|complete"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 0,
      "total_pages": 1
    },
    "filters": {
      "date": null,
      "priority": null,
      "status": null,
      "subject": null
    }
  }
}
```

### `GET /api/tasks/:id`
- Auth: Yes
- Owner-only read.
- Returns one enriched task (`status` normalized + `display_status`).

### `PATCH /api/tasks/:id/status`
- Auth: Yes
- Body:
```json
{
  "status": "pending|complete"
}
```
- Behavior:
  - Owner-only.
  - Sets/clears `completed_at`.
  - When transitioning to complete, inserts `ActivityLog` (`task_completed`) for analytics.

### `DELETE /api/tasks/:id`
- Auth: Yes
- Owner-only soft delete (`is_deleted=true`, `deleted_at` set).

### `POST /api/tasks/:id/collaborators/respond`
- Auth: Yes
- Body:
```json
{
  "action": "accept|reject"
}
```
- Behavior:
  - Works for invited collaborator user row in `task.collaborators`.
  - Handles pending -> accepted/rejected transition.
  - Marks related notification handled.
  - Sends response notification to task owner.

### `GET /api/tasks/collaboration/respond?token=<jwt>`
- Auth: No
- Response type: **HTML**
- Purpose:
  - Email/web action link for collaborator accept/reject.
- Behavior:
  - Validates signed token (`COLLAB_ACTION_SECRET` or JWT access secret fallback)
  - Applies task collaboration action
  - If token indicates learning goal (or task not found), can fallback to learning collaboration handler

---

## 4.6 Learning APIs

### `GET /api/learning`
- Auth: Yes
- Returns current user goals where `status in [active, paused]` and `is_deleted=false`.

### `GET /api/learning/:id`
- Auth: Yes
- Owner-only.
- Returns goal + `progress_percent`.

### `GET /api/learning/:id/topics`
- Auth: Yes
- Owner-only.
- Returns roadmap topics ordered by `order`.

### `GET /api/roadmaps/plans` and `GET /api/roadmaps/:goalId`
- Auth: Yes
- Returns user learning goals (not static catalog).
- `GET /api/roadmaps/plans` — all plans (metadata only, no `sessions[]`).
- `GET /api/roadmaps/:goalId` — one roadmap with full `sessions[]`.

**Roadmap shape** (`data.roadmaps[]`):
- `id`, `title`, `language`, `track_label`, `status`
- `start_date`, `end_date` (local date strings)
- `completed_topics`, `total_topics`, `progress_percent`
- `session_count`, `sessions_summary`, `sessions`

**Session shape** (`sessions[]`):
- `id`, `order`, `title`, `status`, `scheduled_date`, `estimated_duration`, `resources`
- `session_state`: `locked` | `unlocked_future` | `ongoing` | `overdue` | `completed` | `skipped` | `upcoming`
- `is_current`: `true` only for the lowest-order `pending` session
- `unlock_at`: ISO datetime when `session_state` is `locked` and `is_current` (else `null`)
- `completed_at`: only when `status` is `completed` or `skipped`

`resources[]`: `{ title, url, thumbnail?, channel_name? }` for session study links.

### `PATCH /api/learning/:goalId/sessions/:sessionId`
- Auth: Yes
- Body (one or both):
```json
{ "scheduled_date": "YYYY-MM-DD" }
```
```json
{ "status": "completed" }
```
```json
{ "status": "skipped" }
```
- Owner-only; goal must be `active` for changes.
- **Reschedule** (`scheduled_date`): current session only; learning day; no past dates; no quiet-hour or task overlap; may rebase later sessions.
- **Complete** (`status: "completed"`): current session only; `session_state` must be `ongoing` or `overdue`.
- **Skip** (`status: "skipped"`): current session only; `session_state` must be `unlocked_future`.
- **Chat create** (AI): one roadmap per language while any plan is **active** or **paused**; complete, cancel, or delete before creating another for that language.
- Returns refreshed `roadmap`, `session`, and `sessions` in `data`.

### `PATCH /api/learning/:goalId/status`
- Auth: Yes
- Body:
```json
{
  "status": "active|paused|cancelled"
}
```
- Transition rules:
  - Completed goals cannot be changed here.
  - Resume (`active`) only from `paused`.
  - Pause only from `active`.
- Cancel behavior:
  - Soft deletes all related user tasks (`learning_plan_id`).

### `POST /api/learning/:id/collaborators/respond`
- Auth: Yes
- Body:
```json
{
  "action": "accept|reject"
}
```
- Behavior:
  - Handles pending invite row on owner’s learning goal.
  - On accept: clones learning goal + topics (+ mapped tasks) into collaborator account.
  - Marks invite notification handled.
  - Notifies owner.

### `GET /api/learning/collaboration/respond?token=<jwt>`
- Auth: No
- Response type: **HTML**
- Purpose: email/web collaboration action link for learning plans.

---

## 4.7 Settings APIs

### `GET /api/settings`
- Auth: Yes
- Returns full settings doc in `data.settings`.
- `settings.preferred_learning_schedules` is normalized on read (legacy flat slots migrated when needed).

### `PATCH /api/settings`
- Auth: Yes
- Supported fields:
  - `notifications_enabled`, `push_notifications_enabled`, `email_notifications_enabled`
  - `quiet_hours_enabled`, `quiet_hours`
  - `push_token`, `remove_push_token`
  - `theme` (`"dark"`, `"light"`, or `"system"`; default `"system"`)
  - `default_reminder_minutes` (tasks), `default_learning_reminder_minutes` (learning sessions)
  - `default_task_duration`
  - `behavioral_analytics_enabled`
  - `google_calendar_sync_enabled`
  - `allow_friend_requests` (boolean)
- Not accepted on this route:
  - `preferred_learning_schedules` — use `/api/settings/learning-schedules` CRUD instead
  - Removed: `default_topic_reminder_minutes`, `language`, `show_last_active`
  - Internal/system-only: `default_task_priority`, `analytics_min_tasks_threshold`, `analytics_min_tasks_per_day`, `preferred_learning_duration`
- Notes:
  - If no valid fields: `400`.
  - `quiet_hours` blocks: array of `{label,start,end,enabled}` with `HH:mm`.
  - Sending `quiet_hours: []` auto-disables `quiet_hours_enabled` unless you also send `quiet_hours_enabled: true`.
  - Push token fields mutate `User.push_tokens` (not returned on GET settings).

### Learning schedule CRUD (only way to change schedules)
- Auth: Yes
- Returns only `preferred_learning_schedules`.

### `POST /api/settings/learning-schedules`
- Auth: Yes
- Body:
```json
{
  "id": "optional",
  "label": "required",
  "slots": [
    { "day": 0, "time": "19:00", "duration_minutes": 60 }
  ]
}
```
- Rules:
  - Max 20 schedules
  - Unique `id`, unique `label`
  - Same slot and conflict checks as above
- Success: `201`

### `PATCH /api/settings/learning-schedules/:scheduleId`
- Auth: Yes
- Body (partial allowed):
```json
{
  "label": "optional",
  "slots": "optional"
}
```
- Rules:
  - Schedule must exist
  - Label uniqueness preserved
  - Conflict checks run against current tasks

### `DELETE /api/settings/learning-schedules/:scheduleId`
- Auth: Yes
- Rules:
  - Blocked if any active or paused `LearningGoal` references schedule id (`409`)
  - Allowed when no plan uses the schedule, or linked plan(s) are completed/cancelled/soft-deleted
- Success: updated schedule list.

---

## 4.8 Integrations APIs

### `POST /api/integrations/google/connect`
- Auth: Yes
- Body:
```json
{
  "access_token": "required",
  "refresh_token": "optional",
  "token_expires": "optional datetime",
  "calendar_id": "optional, default primary",
  "scope": "optional"
}
```
- Behavior:
  - Upsert user integration for provider `google_calendar`.
  - Stores tokens and metadata.

### `GET /api/integrations`
- Auth: Yes
- Returns active integrations (safe fields only, no token secrets).

---

## 4.9 Analytics APIs

The analytics page uses a **single endpoint**. Full field reference: [`docs/ANALYTICS_DASHBOARD_API.md`](docs/ANALYTICS_DASHBOARD_API.md).

### `GET /api/analytics/dashboard`
- Auth: Yes
- Query:
  - `days` optional: `7`, `30` (default), or `90`
- Behavior:
  - Unified payload for the web analytics page.
  - Heatmap uses `days` lookback; completion trend is always last **3 weeks**.
  - `behavioral` and `best_slots` require AI server (`/analytics?type=full`).
- Response sections:

| Key | Source | Notes |
|-----|--------|-------|
| `hero` | `activity_logs`, `tasks` | Week stats, streak, on-time % |
| `behavioral` | AI server + backend | `top_days`, `hour_windows`, `strength_summary` |
| `heatmap` | `activity_logs` | 6AM–11PM grid; `peak`, `weakest` |
| `tasks` | `tasks` | Counts + `due_within_48h` (max 10) |
| `completion_trend` | `activity_logs` | `{ weeks: 3, trend: [...] }` |
| `best_slots` | AI hours data | Top 3 scored slots |

- Errors:
  - `400` — invalid `days` value
  - `401` — missing/invalid token

---

## 4.10 Friends APIs

### `POST /api/friends/request`
- Auth: Yes
- Body:
```json
{
  "username": "optional",
  "email": "optional"
}
```
- Rules:
  - At least one of username/email required.
  - Cannot request self.
  - Respects target user setting `allow_friend_requests`.
  - Uses pair-key to enforce one relationship per user pair.

### `GET /api/friends`
- Auth: Yes
- Returns accepted friendships as simplified `friend` list.

### `GET /api/friends/requests`
- Auth: Yes
- Query:
  - `type=incoming|outgoing|all` (default incoming)
- Returns pending relationships with direction metadata.

### `GET /api/friends/blocked`
- Auth: Yes
- Returns users blocked by current user.

### `GET /api/friends/search`
- Auth: Yes
- Query:
  - `q` required, min 2 chars
  - `limit` optional, default 10, range 1..50
- Behavior:
  - Username regex search
  - Excludes blocked users
  - Includes `relationship_status`: `none|pending|accepted|rejected|blocked`

### `PATCH /api/friends/:id/respond`
- Auth: Yes
- Body:
```json
{
  "action": "accept|reject"
}
```
- Rules:
  - Only recipient can respond.
  - Request must still be pending.

### `POST /api/friends/block/:userId`
- Auth: Yes
- Behavior:
  - Blocks target user by relationship pair.
  - Creates or updates relationship to `blocked`.

### `POST /api/friends/unblock/:userId`
- Auth: Yes
- Rules:
  - Relationship must exist and be blocked.
  - Only user who blocked can unblock.
- Behavior:
  - Sets relationship status to `rejected`.

### `DELETE /api/friends/:id`
- Auth: Yes
- Behavior:
  - Only participants can remove.
  - Only accepted friendships can be unfriended.

---

## 4.11 Dashboard API

### `GET /api/dashboard`
- Auth: Yes
- Purpose: home screen aggregate payload.
- Data returned:
  - `up_next`: next non-complete task for today (local timezone)
  - `daily_progress`: completed/total/percentage for today
  - `learning`: active/paused goals with `next_topic`
  - `today_schedule`: today tasks
- Task source includes:
  - owned tasks
  - collaborator tasks where current user is `accepted`
- Response shape:
```json
{
  "status": "success",
  "data": {
    "up_next": {},
    "daily_progress": {
      "date": "YYYY-MM-DD",
      "timezone": "IANA",
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

## 5. Notification Types Used by APIs/Flows

`Notification.type` enum currently allows:

- `task_scheduled`
- `task_deleted`
- `task_reminder`
- `topic_reminder`
- `overdue_alert`
- `collaboration_invite`
- `collaboration_response`
- `learning_collaboration_invite`
- `learning_collaboration_response`
- `learning_plan_created`
- `friend_request`
- `friend_accepted`
- `behavioral_suggestion`
- `goal_progress`

Reference type enum:
- `task | learning_goal | topic | friend`

Delivery channels:
- `push | in_app | email`

---

## 6. Useful Environment Variables (API-Relevant)

- `BACKEND_PORT`
- `MONGODB_URI`
- `JWT_ACCESS_SECRET`
- `JWT_REFRESH_SECRET`
- `JWT_ACCESS_EXPIRES` (default `15m`)
- `JWT_REFRESH_EXPIRES` (default `7d`)
- `AI_SERVER_URL`
- `AI_SERVER_TIMEOUT_MS` (default `15000`)
- `BACKEND_PUBLIC_URL` or (`BACKEND_SCHEME` + `BACKEND_HOST` + `BACKEND_PORT`)
- `VERIFY_EMAIL_URL` (optional template override)
- `RESET_PASSWORD_URL` (optional template override)
- `COLLAB_ACTION_SECRET` (for collaboration action links)
- Email SMTP vars (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USER`, `EMAIL_PASS`)

---

## 7. Implementation Notes for Frontend/QA

- Some routes are intentionally HTML:
  - `/api/auth/verify-email`
  - `/api/tasks/collaboration/respond`
  - `/api/learning/collaboration/respond`
- Task list (`GET /api/tasks`) is owner-only; collaboration visibility is exposed in dashboard today schedule and through invite response workflows.
- Alias normalization exists for task status/priority (e.g., `done` -> `complete`, `urgent` -> `high`).
- API rate limit applies to all `/api/*` routes.


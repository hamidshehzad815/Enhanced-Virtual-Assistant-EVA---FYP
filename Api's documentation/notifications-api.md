# Notifications API

In-app notification inbox for the signed-in user: list notifications, get the unread badge count, and mark notifications as read. Powers the **dashboard bell icon** (badge + panel).

> **No push/FCM required for the bell.** The app can simply **poll** `GET /api/notifications/unread-count` on a timer (e.g. every 30–60s while the app is in the foreground) to keep the badge fresh, and load the full list when the user opens the panel.

**Base path:** `/api/notifications`
See [README.md](./README.md) for base URL, auth headers, and error envelopes.

---

## Available endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/api/notifications` | **Yes** | List the user's notifications (newest first, paginated) + unread count |
| `GET` | `/api/notifications/unread-count` | **Yes** | Just the unread count (cheap — poll this for the badge) |
| `PATCH` | `/api/notifications/:id/read` | **Yes** | Mark one notification as read |
| `PATCH` | `/api/notifications/read-all` | **Yes** | Mark all of the user's notifications as read |

All routes require:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

Every endpoint is **scoped to the authenticated user** — you can only read or modify your own notifications. Acting on an id that isn't yours returns `404`.

---

## The Notification object

```jsonc
{
  "_id": "665f0c...",
  "type": "collaboration_invite",      // see "Notification types" below
  "title": "Collaboration invite",
  "message": "Hamid added you to Study DSA",
  "reference_type": "task",            // "task" | "friend" | ... | null
  "reference_id": "665e9a...",         // id of the related entity (e.g. the task) | null
  "is_read": false,
  "action_required": true,             // true => show Accept/Reject (see below)
  "action_taken": null,                // "accepted" | "rejected" | null
  "delivery_channel": ["push", "in_app", "email"],
  "sent_at": "2026-07-14T09:00:00.000Z",  // null if not dispatched
  "created_at": "2026-07-14T09:00:00.000Z",
  "sender": {                          // who triggered it, or null (system)
    "_id": "665e00...",
    "name": "Hamid Shehzad",
    "username": "hamid",
    "profile_picture": null
  }
}
```

---

## `GET /api/notifications`

List the user's notifications, newest first.

**Query params (all optional):**

| Param | Default | Notes |
|-------|---------|-------|
| `limit` | `20` | 1–100 (clamped) |
| `skip` | `0` | offset for pagination |
| `unread_only` | `false` | `true` returns only unread notifications |

**Response `200`:**

```jsonc
{
  "status": "success",
  "data": {
    "notifications": [ /* Notification objects, newest first */ ],
    "pagination": {
      "limit": 20,
      "skip": 0,
      "total": 42,
      "has_more": true
    },
    "unread_count": 5
  }
}
```

---

## `GET /api/notifications/unread-count`

Cheap endpoint for the badge — **poll this**, not the full list.

**Response `200`:**

```jsonc
{
  "status": "success",
  "data": { "unread_count": 5 }
}
```

---

## `PATCH /api/notifications/:id/read`

Mark a single notification as read (e.g. when the user taps it).

**Response `200`:**

```jsonc
{
  "status": "success",
  "data": { "notification": { /* the updated Notification object */ } }
}
```

**Errors:**

| Status | When |
|--------|------|
| `400` | `:id` is not a valid id |
| `404` | notification not found **or not owned by the user** |

---

## `PATCH /api/notifications/read-all`

Mark every unread notification for the user as read (clears the badge).

**Response `200`:**

```jsonc
{
  "status": "success",
  "data": { "marked_read": 5 }   // how many were flipped to read
}
```

---

## Notification types

| `type` | Meaning | `action_required` |
|--------|---------|-------------------|
| `task_scheduled` | A task was created/scheduled | no |
| `task_reminder` | Reminder before a task's due time | no |
| `collaboration_invite` | You were added as a collaborator on a task | **yes** |
| `collaboration_response` | A collaborator accepted/rejected your invite | no |
| `learning_collaboration_invite` | Collaborator invite on a learning goal | **yes** |
| `learning_collaboration_response` | Response to a learning collaboration invite | no |
| `friend_request` / `friend_accepted` | Friend request activity | varies |

*(Exact set may grow; treat unknown types as plain notifications.)*

---

## Handling `action_required` notifications (Accept / Reject)

When `action_required == true` (a **collaboration invite**), render **Accept** and **Reject** buttons in the panel. These are **not** handled by this API — they call the **Tasks** collaboration endpoint, using the invite's `reference_id` (the task id):

```http
POST /api/tasks/{reference_id}/collaborators/respond
Authorization: Bearer <access_token>
Content-Type: application/json

{ "action": "accept" }     // or "reject"
```

**Response `200`:**

```jsonc
{
  "status": "success",
  "message": "Collaboration invite accepted.",
  "data": {
    "task_id": "665e9a...",
    "collaboration_status": "accepted",   // or "rejected"
    "already_responded": false            // true if it was handled before
  }
}
```

After a successful accept/reject, mark the invite notification read (`PATCH /:id/read`) and refresh the badge. If `already_responded == true`, just show a friendly "already handled" state — don't error.

---

## Suggested polling behavior (dashboard bell)

1. On app foreground (and every ~30–60s while foregrounded): `GET /unread-count` → update the badge.
2. Pause polling when the app is backgrounded; refresh once on resume.
3. When the user opens the bell panel: `GET /api/notifications` (page 1).
4. Tapping a notification → `PATCH /:id/read`, then navigate using `reference_type` / `reference_id`.
5. "Mark all read" → `PATCH /read-all`.

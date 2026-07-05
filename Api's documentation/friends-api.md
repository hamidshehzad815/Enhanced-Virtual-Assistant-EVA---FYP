# Friends API

Friend-request and relationship management for the **Collaboration** screen. The friend graph is also the **access gate for collaboration**: a user can only be added as a collaborator on a task or learning plan if they are an **accepted friend** (enforced in the AI server).

Base path: `/api/friends`

All routes require authentication (`Authorization: Bearer <access_token>`).

> **Note:** Blocking was removed. There is no `block` / `unblock` / `blocked` endpoint, and `blocked` is no longer a relationship status.

---

## Relationship model

One `Friend` document exists per **pair** of users (a unique `pair_key` = the two user ids sorted and joined, so direction never creates duplicates).

| Field | Meaning |
|-------|---------|
| `requester_id` | user who sent the request |
| `recipient_id` | user who received it |
| `status` | `pending` · `accepted` · `rejected` |
| `responded_at` | when the recipient accepted/rejected |

**`friend` / `requester` / `recipient` user shape** (returned throughout):

```json
{
  "_id": "507f1f77bcf86cd799439011",
  "name": "Alice Wonder",
  "username": "alice",
  "email": "alice@example.com",
  "profile_picture": null
}
```

**`friendship` shape** (returned by `request` and `respond`):

```json
{
  "_id": "665...",
  "status": "pending",
  "responded_at": null,
  "created_at": "2026-07-05T15:00:00+05:00",
  "updated_at": "2026-07-05T15:00:00+05:00",
  "requester": { "_id": "...", "name": "...", "username": "...", "email": "...", "profile_picture": null },
  "recipient": { "_id": "...", "name": "...", "username": "...", "email": "...", "profile_picture": null },
  "direction": "outgoing",
  "friend": { "_id": "...", "name": "...", "username": "...", "email": "...", "profile_picture": null }
}
```

- `direction` is relative to the **current user**: `outgoing` if they sent it, `incoming` if they received it.
- `friend` is the **other** participant (the counterpart of the current user).

---

## Endpoint quick list

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/friends/request` | Send a friend request by username or email |
| `GET` | `/api/friends` | List accepted friends |
| `GET` | `/api/friends/requests` | List pending requests (incoming/outgoing/all) |
| `GET` | `/api/friends/search` | Search users to add (live/typeahead) |
| `PATCH` | `/api/friends/:id/respond` | Accept or reject an incoming request |
| `DELETE` | `/api/friends/:id` | Unfriend (remove an accepted relationship) |

---

## `POST /api/friends/request`

Send a friend request. Identify the target by **`username` or `email`** (at least one).

| | |
|---|---|
| **Auth** | Required |
| **Method** | `POST` |

### Body

```json
{
  "username": "alice",
  "email": "alice@example.com"
}
```

`username` and `email` are both optional individually, but **at least one is required**. `username` takes precedence when both are given.

### Rules

- Cannot send a request to yourself.
- Target must exist and be active.
- Respects the target's `allow_friend_requests` privacy setting.
- Uses the pair-key so there is only ever one relationship per user pair. A previously **rejected** relationship is re-opened as `pending`.

### Success

- `201 Created` — new request created.
- `200 OK` — a previously rejected relationship was re-opened.

```json
{
  "status": "success",
  "message": "Friend request sent",
  "data": { "friendship": { "...": "friendship shape (see above)" } }
}
```

**Side effect:** a `friend_request` notification (push + in-app, `action_required: true`) is dispatched to the recipient.

### Errors

| HTTP | When |
|------|------|
| `400` | Neither `username` nor `email` provided |
| `400` | Target is yourself |
| `403` | Target is not accepting friend requests |
| `404` | Target user not found / inactive |
| `409` | Already friends |
| `409` | Request already sent (you are the requester) |
| `409` | The other user already sent you a request |

---

## `GET /api/friends`

List the current user's **accepted** friends, most recently updated first.

### Success `200`

```json
{
  "status": "success",
  "data": {
    "friends": [
      {
        "friendship_id": "665...",
        "since": "2026-07-01T09:12:00+05:00",
        "friend": { "_id": "...", "name": "...", "username": "...", "email": "...", "profile_picture": null }
      }
    ]
  }
}
```

- `since` is `responded_at` (or `created_at` as fallback).

---

## `GET /api/friends/requests`

List **pending** requests.

### Query params

| Param | Values | Default |
|-------|--------|---------|
| `type` | `incoming` · `outgoing` · `all` | `incoming` |

### Success `200`

```json
{
  "status": "success",
  "data": {
    "requests": [
      { "...": "friendship shape — includes direction, friend, requester, recipient" }
    ]
  }
}
```

Use `direction` on each row to render "wants to be your friend" (incoming) vs. "request sent" (outgoing).

### Errors

| HTTP | When |
|------|------|
| `400` | `type` is not one of `incoming` / `outgoing` / `all` |

---

## `GET /api/friends/search`

Search users to add as friends. Designed for **typeahead / live search** (call it as the user types).

### Query params

| Param | Description |
|-------|-------------|
| `q` | **Required.** Min 2 characters. Case-insensitive username match (regex/partial). |
| `limit` | Optional. Default `10`, range `1..50`. |

### Behavior

- Excludes the current user and inactive users.
- Hides users who are **not accepting requests** (`allow_friend_requests = false`) **unless** a relationship already exists between them and the current user.
- Each result includes a `relationship_status` so the UI can pick the right button state.

### Success `200`

```json
{
  "status": "success",
  "data": {
    "users": [
      {
        "_id": "...",
        "name": "Alice Wonder",
        "username": "alice",
        "email": "alice@example.com",
        "profile_picture": null,
        "relationship_status": "none"
      }
    ]
  }
}
```

`relationship_status`: `none` · `pending` · `accepted` · `rejected`.

### Frontend usage (live search)

Call this repeatedly **as the user types, but debounced** — do not fire one request per keystroke:

1. On each change, reset a debounce timer (~300–500ms). Only send a request when typing pauses.
2. Skip the call while `q` has fewer than 2 characters.
3. Ignore/cancel responses from stale in-flight requests so a slow earlier reply can't overwrite a newer one (track the latest query).
4. Render the returned `users` list in a dropdown, using `relationship_status` to choose each row's button state (`none` → "Add", `pending` → "Requested", `accepted` → "Friends").

So typing "alice" results in ~1 request (after the pause), not 5.

### Errors

| HTTP | When |
|------|------|
| `400` | `q` shorter than 2 characters |

---

## `PATCH /api/friends/:id/respond`

Accept or reject an **incoming** pending request. `:id` is the `friendship_id`.

### Body

```json
{ "action": "accept" }
```

`action`: `accept` or `reject`.

### Rules

- Only the **recipient** of the request may respond.
- The request must still be `pending`.

### Success `200`

```json
{
  "status": "success",
  "message": "Friend request accepted",
  "data": { "friendship": { "...": "friendship shape, status now accepted/rejected" } }
}
```

**Side effect:** on `accept`, a `friend_accepted` notification is sent to the original requester.

### Errors

| HTTP | When |
|------|------|
| `400` | `action` not `accept`/`reject`, or invalid `:id` |
| `403` | Current user is not the recipient |
| `404` | Friendship not found |
| `409` | Request is no longer pending |

---

## `DELETE /api/friends/:id`

Unfriend — remove an **accepted** relationship. `:id` is the `friendship_id`.

### Rules

- Only a participant of the relationship may remove it.
- Only `accepted` friendships can be unfriended.

### Success `200`

```json
{
  "status": "success",
  "message": "Friend removed",
  "data": { "friendship_id": "665..." }
}
```

### Errors

| HTTP | When |
|------|------|
| `400` | Invalid `:id` |
| `403` | Current user is not a participant |
| `404` | Friendship not found |
| `409` | Relationship is not `accepted` |

---

## Why friends exist (collaboration gate)

When a user adds a collaborator to a **task** or **learning plan** (via the AI server), the collaborator is looked up by username/name and must have an **`accepted`** friendship with the owner — otherwise the request is rejected with *"… is not in your friends list. Add them as a friend first."* Up to **2 collaborators** are allowed per item. Collaborators are stored on the task/goal with their own `pending` → `accepted`/`rejected` status, independent of the friendship.

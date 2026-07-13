# Chat API

EVA conversational chat: list past conversations, load message history, and send new messages to the AI pipeline (scheduling, learning, behavioral, general chat).

> **Lazy session design:** A chat is **not stored** until the user sends at least one message. The frontend should keep a local “draft” new-chat screen (`session_id = null`) and only call the API on send. Empty drafts that the user abandons never hit the backend.

**Base path:** `/api/chat`  
See [README.md](./README.md) for base URL, auth headers, and error envelopes.

---

## Available endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/api/chat/sessions` | **Yes** | List conversations with at least one message (sidebar) |
| `GET` | `/api/chat/sessions/:sessionId/messages` | **Yes** | Load message history for one conversation |
| `DELETE` | `/api/chat/sessions/:sessionId` | **Yes** | Soft-delete a conversation and its messages |
| `POST` | `/api/chat/process` | **Yes** | Send a message to EVA (**creates session on first message** if `session_id` omitted) |

All routes require:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

---

## Recommended UX flow (ChatGPT-style)

```mermaid
sequenceDiagram
  participant UI
  participant API
  participant AI

  Note over UI: User taps "New Chat"
  UI->>UI: Show empty thread (session_id = null, no API)

  alt User switches away without sending
    UI->>UI: Discard draft — nothing stored
  else User sends first message
    UI->>API: POST /api/chat/process { message }
    API->>API: Create ChatSession
    API->>AI: POST /process
    AI-->>API: response_text, intent, ...
    API-->>UI: session_id, session_created: true, response_text
    UI->>UI: Save session_id; refresh sidebar
  end

  Note over UI: User opens existing chat from sidebar
  UI->>API: GET /api/chat/sessions/:id/messages
  API-->>UI: messages[]

  Note over UI: User sends follow-up
  UI->>API: POST /api/chat/process { message, session_id }
  API->>AI: POST /process
  API-->>UI: response_text, session_created: false
```

| User action | Frontend | Backend |
|-------------|----------|---------|
| Tap **New Chat** | Clear UI, `sessionId = null` | **No API call** |
| Switch to another chat without sending | Discard local draft | **No API call** |
| Send **first** message | `POST /process` without `session_id` | Creates session + processes message |
| Send **follow-up** | `POST /process` with `session_id` | Continues existing session |
| Open sidebar | `GET /sessions` | Returns only chats with messages |
| Open a past chat | `GET /sessions/:id/messages` | Loads `conversation_history` |

---

## `GET /api/chat/sessions`

| | |
|---|---|
| **Auth** | Required |
| **Method** | `GET` |
| **Path** | `/api/chat/sessions` |
| **Request body** | None |

### Query params

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | `number` | `50` | Max sessions to return (max `100`) |

Invalid `limit` → `400`.

### Behavior

- Returns sessions owned by the current user where `is_deleted` is `false` **and** `last_message_at` is set.
- Sorted by `last_message_at` descending (most recent first).

### Success `200`

```json
{
  "status": "success",
  "data": {
    "timezone": "Asia/Karachi",
    "sessions": [
      {
        "id": "674a1b2c3d4e5f6789012345",
        "title": "add physics quiz tomorrow 5pm",
        "last_message_preview": "Sure! I've added your physics quiz for tomorrow at 5pm.",
        "last_message_at": "2026-07-10T15:30:00+05:00",
        "created_at": "2026-07-10T15:29:50+05:00",
        "updated_at": "2026-07-10T15:30:00+05:00"
      }
    ]
  }
}
```

### Type reference — `SessionSummary`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Chat session MongoDB id |
| `title` | `string` | Auto-derived from first user message (max 60 chars) unless custom title was set |
| `last_message_preview` | `string` | Truncated EVA reply (or user message fallback), max 200 chars |
| `last_message_at` | `string \| null` | ISO datetime of last activity (user timezone) |
| `created_at` | `string` | ISO datetime |
| `updated_at` | `string` | ISO datetime |

---

## `GET /api/chat/sessions/:sessionId/messages`

| | |
|---|---|
| **Auth** | Required |
| **Method** | `GET` |
| **Path** | `/api/chat/sessions/:sessionId/messages` |
| **Request body** | None |

### Path params

| Param | Type | Description |
|-------|------|-------------|
| `sessionId` | `string` | MongoDB ObjectId of the chat session |

### Query params

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | `number` | `100` | Max messages to return (max `200`) |

Invalid `sessionId` or `limit` → `400`.  
Session not found or not owned → `404`.

### Behavior

- Loads messages from `conversation_history` for the session.
- Matches messages saved by the **AI server** (`session_id` as string, no `is_deleted` field) and by Node (`ObjectId`, `is_deleted: false`).
- Only non-deleted messages (`is_deleted` is not `true`).
- Ordered **oldest → newest** (`created_at` ascending).
- Messages are written to `conversation_history` when you **`POST /api/chat/process`** (Node backend).
- The AI server may also write turns; duplicates are collapsed on read when identical.

### Success `200`

```json
{
  "status": "success",
  "data": {
    "timezone": "Asia/Karachi",
    "session_id": "674a1b2c3d4e5f6789012345",
    "title": "add physics quiz tomorrow 5pm",
    "messages": [
      {
        "id": "674a1b2c3d4e5f6789012346",
        "role": "user",
        "content": "add physics quiz tomorrow 5pm",
        "input_type": "text",
        "intent": "scheduling_add",
        "status": "processed",
        "created_at": "2026-07-10T15:29:55+05:00"
      },
      {
        "id": "674a1b2c3d4e5f6789012347",
        "role": "eva",
        "content": "Sure! I've added your physics quiz for tomorrow at 5pm.",
        "input_type": "text",
        "intent": "scheduling_add",
        "status": "processed",
        "created_at": "2026-07-10T15:30:00+05:00"
      }
    ]
  }
}
```

### Type reference — `ChatMessage`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Message MongoDB id |
| `role` | `"user" \| "eva"` | Who sent the message |
| `content` | `string` | Message text |
| `input_type` | `"text" \| "voice"` | How the user input was sent |
| `intent` | `string \| null` | Detected intent for this turn (e.g. `scheduling_add`, `behavioral`) |
| `status` | `"processed" \| "failed" \| "pending"` | Processing status |
| `created_at` | `string` | ISO datetime |

---

## `POST /api/chat/process`

Primary endpoint for sending messages to EVA.

| | |
|---|---|
| **Auth** | Required |
| **Method** | `POST` |
| **Path** | `/api/chat/process` |

### Request body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | `string` | **Yes** | User message (non-empty after trim) |
| `session_id` | `string` | No | Existing session id. **Omit on first message** to create a session lazily |
| `input_type` | `"text" \| "voice"` | No | Default `"text"` |

### Behavior

1. Validates `message` and optional `input_type`.
2. **If `session_id` provided:** verifies session exists and belongs to current user.
3. **If `session_id` omitted:** creates a new `ChatSession` (`session_created: true`).
4. Forwards to Eva AI Server `POST /process` with:
   - `message`, `user_id`, `session_id`, `input_type`, `timestamp`
5. Dispatches any notifications returned by the AI server.
6. Updates session `last_message_preview`, `last_message_at`, and `title` (from first user message if still `"New chat"`).
7. Returns a **slim** response (no full AI pipeline dump).

**Failure rollback:** If the AI server fails on a **newly created** session, that session is soft-deleted so it does not appear in the sidebar.

### Success `200`

```json
{
  "status": "success",
  "session_id": "674a1b2c3d4e5f6789012345",
  "session_created": true,
  "title": "add physics quiz tomorrow 5pm",
  "response_text": "Sure! I've added your physics quiz for tomorrow at 5pm.",
  "intent": "scheduling_add",
  "ai_status": "success",
  "notifications": {
    "requested": 0,
    "inserted": 0,
    "dispatched_push": 0,
    "dispatched_email": 0,
    "failed": 0,
    "results": []
  }
}
```

### Response fields

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | `string` | Use for all follow-up messages in this conversation |
| `session_created` | `boolean` | `true` when this request created a new session (first message) |
| `title` | `string` | Updated session title (auto from first message) |
| `response_text` | `string` | EVA's natural-language reply — **render this in the chat bubble** |
| `intent` | `string \| null` | Routed intent (e.g. `scheduling_add`, `learning_create`, `behavioral`, `general`) |
| `ai_status` | `string \| null` | Handler status from AI server (e.g. `success`, `pending`) |
| `notifications` | `NotificationSummary` | Push/email dispatch summary |

**`NotificationSummary`**

| Field | Type | Description |
|-------|------|-------------|
| `requested` | `number` | Notifications AI asked to send |
| `inserted` | `number` | Saved to DB |
| `dispatched_push` | `number` | Push notifications sent |
| `dispatched_email` | `number` | Emails sent |
| `failed` | `number` | Failed dispatches |
| `results` | `array` | Per-notification detail |

### Example — first message (new chat)

```http
POST /api/chat/process
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Content-Type: application/json

{
  "message": "add physics quiz tomorrow 5pm",
  "input_type": "text"
}
```

### Example — follow-up message

```http
POST /api/chat/process
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Content-Type: application/json

{
  "message": "make it high priority",
  "session_id": "674a1b2c3d4e5f6789012345",
  "input_type": "text"
}
```

### Errors

| Status | When |
|--------|------|
| `400` | Missing/empty `message`, invalid `session_id`, invalid `input_type`, invalid `limit` on list routes |
| `401` | Missing or invalid JWT |
| `404` | `session_id` not found or not owned by user |
| `500` | AI server unavailable or notification dispatch failed |

---

## `DELETE /api/chat/sessions/:sessionId`

| | |
|---|---|
| **Auth** | Required |
| **Method** | `DELETE` |
| **Path** | `/api/chat/sessions/:sessionId` |
| **Request body** | None |

### Behavior

- Soft-deletes the session (`is_deleted: true`) for the current user.
- Soft-deletes all messages in that conversation.
- Deleted sessions no longer appear in `GET /api/chat/sessions`.

### Success `200`

```json
{
  "status": "success",
  "message": "Chat deleted successfully",
  "data": {
    "timezone": "Asia/Karachi",
    "session_id": "674a1b2c3d4e5f6789012345"
  }
}
```

### Errors

| Status | When |
|--------|------|
| `400` | Invalid `sessionId` |
| `401` | Missing or invalid JWT |
| `404` | Session not found or not owned by user |

---

## Frontend / Flutter integration notes

### State to keep locally

| State | Purpose |
|-------|---------|
| `sessionId` | `null` = draft new chat; set after first successful `/process` |
| `messages` | In-memory list for current thread |
| `sessions` | Sidebar list from `GET /sessions` |

### New chat screen

1. User taps **New Chat** → set `sessionId = null`, clear `messages`, **do not call API**.
2. User switches to another chat without sending → discard draft (no API).
3. User sends first message → `POST /process` with `{ message }` only.
4. On success: store `session_id`, append user + EVA bubbles from `response_text`, set `session_created` handled, refresh sidebar.

### Opening existing chat

1. `GET /api/chat/sessions/:sessionId/messages`
2. Map `messages[]` to UI bubbles (`role: "user"` → user side, `"eva"` → EVA side).
3. Set local `sessionId` from response.

### After each send

- Append user message to UI immediately (optimistic).
- Show typing indicator while `/process` is in flight.
- On success: append `response_text` as EVA message; update `sessionId` if it was first message.
- On error: show error; remove optimistic bubble or mark failed.

### Voice input

Pass `input_type: "voice"` when the message came from speech-to-text. Backend and AI server both accept `text` and `voice`.

### What you do **not** need from the response

Older versions returned a full `data` object with the entire AI pipeline (classifications, entities, route debug). That was removed. The client only needs:

- `response_text` — display
- `session_id` / `session_created` — session management
- `intent` / `ai_status` — optional UI hints (debug, loading states)
- `notifications` — optional; usually empty for chat commands

### Sidebar refresh

Call `GET /api/chat/sessions` after:

- First message in a new chat (`session_created: true`)
- App open / chat screen focus
- Pull-to-refresh on history drawer

---

## Architecture (backend)

```text
Flutter / Web
    → Node.js  POST /api/chat/process
        → Eva AI Server  POST /process
            → NLP models + handlers + Gemini
            → MongoDB: conversation_history, chat_sessions (preview)
        → Node updates chat_sessions title/preview
    ← slim JSON response
```

- **Node** owns session lifecycle (create, list, title/preview updates).
- **AI server** owns message persistence in `conversation_history` and may also update `chat_sessions.last_message_preview` from handlers.
- **No AI server changes** were required for the lazy-session design.

---

## Related APIs

| Need | API |
|------|-----|
| Auth token | [auth-api.md](./auth-api.md): `POST /api/auth/login` |
| User timezone (datetime display) | `GET /api/auth/me` or [profile-api.md](./profile-api.md) |
| Tasks created via chat | [tasks-api.md](./tasks-api.md) |
| Roadmaps created via chat | [roadmaps-api.md](./roadmaps-api.md) |
| Push from chat notifications | [push-notifications-frontend-setup.md](./push-notifications-frontend-setup.md) |

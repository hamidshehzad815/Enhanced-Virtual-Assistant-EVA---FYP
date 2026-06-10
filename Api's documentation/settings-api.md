# Settings API

User preferences: notifications, quiet hours, reminders, theme, analytics toggle, Google Calendar sync, friend requests.

Learning schedules are **read** here but **updated** only via [settings-learning-schedules-api.md](./settings-learning-schedules-api.md).

---

## Settings object (what you get in `data.settings`)

Fields returned by `GET /api/settings` and `PATCH /api/settings` (after update).

| Field | Type | Default | UI editable? | Notes |
|-------|------|---------|--------------|-------|
| `_id` | `string` | auto | No | Mongo id |
| `user_id` | `string` | auto | No | Owner |
| `theme` | `"light" \| "dark"` | `"light"` | Yes | |
| `notifications_enabled` | `boolean` | `true` | Yes | Master notifications |
| `push_notifications_enabled` | `boolean` | `true` | Yes | |
| `email_notifications_enabled` | `boolean` | `false` | Yes | |
| `quiet_hours_enabled` | `boolean` | `false` | Yes | Master quiet-hours toggle |
| `quiet_hours` | `QuietHourBlock[]` | `[]` | Yes | Only meaningful when toggle ON |
| `default_reminder_minutes` | `number` | `30` | Yes | Task reminders; range 5–1440 |
| `default_learning_reminder_minutes` | `number` | `15` | Yes | Learning reminders; range 5–1440 |
| `default_task_duration` | `number` | `120` | Yes | Minutes; range 5–480 |
| `behavioral_analytics_enabled` | `boolean` | `true` | Yes | Gates behavioral tracking |
| `preferred_learning_schedules` | `LearningSchedule[]` | `[]` | **Read only here** | Update via schedule CRUD routes |
| `google_calendar_sync_enabled` | `boolean` | `false` | Yes | Requires Google integration connected |
| `allow_friend_requests` | `boolean` | `true` | Yes | `true` = accept requests |
| `created_at` | `string` | auto | No | ISO datetime |
| `updated_at` | `string` | auto | No | ISO datetime |

### `QuietHourBlock`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `label` | `string` | Yes | Max 50 chars |
| `start` | `string` | Yes | `"HH:mm"` 24h |
| `end` | `string` | Yes | `"HH:mm"` 24h |
| `enabled` | `boolean` | No | Default `true` per block |

### `LearningSchedule` (read shape)

| Field | Type | Notes |
|-------|------|-------|
| `id` | `string` | Stable schedule id |
| `label` | `string` | Unique per user |
| `slots` | `ScheduleSlot[]` | At least one slot |

### `ScheduleSlot`

| Field | Type | Notes |
|-------|------|-------|
| `day` | `number` | `0` = Monday … `6` = Sunday |
| `time` | `string` | `"HH:mm"` |
| `duration_minutes` | `number` | 15–240 |

### Fields NOT returned (internal / removed)

Never show or send these from the app:

| Field | Reason |
|-------|--------|
| `default_task_priority` | Internal; used by AI when creating tasks |
| `analytics_min_tasks_threshold` | System constant (20), not user setting |
| `analytics_min_tasks_per_day` | System constant (5), not user setting |
| `preferred_learning_duration` | Removed; use per-slot `duration_minutes` |
| `default_topic_reminder_minutes` | Removed; use `default_learning_reminder_minutes` |
| `language` | Removed from settings |
| `show_last_active` | Removed from settings |

---

## `GET /api/settings`

| | |
|---|---|
| **Auth** | Required |
| **Method** | `GET` |
| **Path** | `/api/settings` |

### Success `200`

```json
{
  "status": "success",
  "data": {
    "timezone": "Asia/Karachi",
    "settings": {
      "_id": "674a1b2c3d4e5f6789012300",
      "user_id": "674a1b2c3d4e5f6789012301",
      "theme": "light",
      "notifications_enabled": true,
      "push_notifications_enabled": true,
      "email_notifications_enabled": false,
      "quiet_hours_enabled": false,
      "quiet_hours": [],
      "default_reminder_minutes": 30,
      "default_learning_reminder_minutes": 15,
      "default_task_duration": 120,
      "behavioral_analytics_enabled": true,
      "preferred_learning_schedules": [],
      "google_calendar_sync_enabled": false,
      "allow_friend_requests": true,
      "created_at": "2026-01-15T10:00:00+05:00",
      "updated_at": "2026-06-05T14:30:00+05:00"
    }
  }
}
```

**Note:** `preferred_learning_schedules` appears only under `data.settings`, not as a duplicate top-level key.

If `allow_friend_requests` is missing in DB, API still returns `true`.

---

## `PATCH /api/settings`

Partial update — send **only fields you change**.

| | |
|---|---|
| **Auth** | Required |
| **Method** | `PATCH` |
| **Path** | `/api/settings` |

### Accepted body fields

| Field | Type | Validation |
|-------|------|------------|
| `theme` | `string` | `"light"` or `"dark"` |
| `notifications_enabled` | `boolean` | |
| `push_notifications_enabled` | `boolean` | |
| `email_notifications_enabled` | `boolean` | |
| `quiet_hours_enabled` | `boolean` | |
| `quiet_hours` | `QuietHourBlock[]` | Full array replace |
| `default_reminder_minutes` | `number` | Integer 5–1440 |
| `default_learning_reminder_minutes` | `number` | Integer 5–1440 |
| `default_task_duration` | `number` | Integer 5–480 |
| `behavioral_analytics_enabled` | `boolean` | |
| `google_calendar_sync_enabled` | `boolean` | |
| `allow_friend_requests` | `boolean` | Must be `true` or `false` |
| `push_token` | `string` | Registers device for push (stored on User) |
| `remove_push_token` | `string` | Removes device token from User |

### Rejected body fields (`400`)

| Field | Message |
|-------|---------|
| `preferred_learning_schedules` | Use `/api/settings/learning-schedules` instead |
| `default_topic_reminder_minutes` | no longer supported |
| `language` | no longer supported |
| `show_last_active` | no longer supported |
| `default_task_priority` | system setting |
| `analytics_min_tasks_threshold` | system setting |
| `analytics_min_tasks_per_day` | system setting |
| `preferred_learning_duration` | system setting |

### Quiet hours behavior

| Frontend action | PATCH body |
|-----------------|------------|
| Toggle ON | `{ "quiet_hours_enabled": true }` |
| Toggle OFF | `{ "quiet_hours_enabled": false }` |
| Save blocks | `{ "quiet_hours": [ { "label": "Sleep", "start": "22:00", "end": "07:00", "enabled": true } ] }` |
| Toggle ON + first block | Both fields in one request |

**Edge case:** `{ "quiet_hours": [] }` without `quiet_hours_enabled` auto-sets `quiet_hours_enabled: false`.

### Example requests

**Allow friend requests off:**
```json
{ "allow_friend_requests": false }
```

**Quiet hours on:**
```json
{ "quiet_hours_enabled": true }
```

**Update task reminder:**
```json
{ "default_reminder_minutes": 45 }
```

**Multiple toggles:**
```json
{
  "notifications_enabled": true,
  "push_notifications_enabled": true,
  "email_notifications_enabled": false
}
```

### Success `200`

```json
{
  "status": "success",
  "message": "Settings updated",
  "data": {
    "timezone": "Asia/Karachi",
    "settings": { }
  }
}
```

`data.settings` has the same shape as `GET /api/settings`.

### Errors

| Status | When |
|--------|------|
| `400` | Invalid field, empty body, boolean/type error |
| `401` | Auth failure |
| `409` | Quiet hours overlap with learning schedule slots |

---

## Push tokens (`push_token` / `remove_push_token`)

Optional — for **mobile push notifications** only.

| Field | Stored on | Returned in GET settings? |
|-------|-----------|---------------------------|
| `push_token` | `User.push_tokens[]` | **No** |
| `remove_push_token` | removes from same array | **No** |

Register when user enables push on device; remove on logout.

**Nothing is wrong** — these are intentional side-effect fields, not part of the settings document.

---

## Frontend screen mapping

| UI control | GET field | PATCH field |
|------------|-----------|-------------|
| Dark mode | `settings.theme` | `theme` |
| Notifications master | `settings.notifications_enabled` | `notifications_enabled` |
| Push toggle | `settings.push_notifications_enabled` | `push_notifications_enabled` |
| Email toggle | `settings.email_notifications_enabled` | `email_notifications_enabled` |
| Quiet hours toggle | `settings.quiet_hours_enabled` | `quiet_hours_enabled` |
| Quiet hours list | `settings.quiet_hours` | `quiet_hours` |
| Task reminder mins | `settings.default_reminder_minutes` | `default_reminder_minutes` |
| Learning reminder mins | `settings.default_learning_reminder_minutes` | `default_learning_reminder_minutes` |
| Default task duration | `settings.default_task_duration` | `default_task_duration` |
| Analytics toggle | `settings.behavioral_analytics_enabled` | `behavioral_analytics_enabled` |
| Google Calendar sync | `settings.google_calendar_sync_enabled` | `google_calendar_sync_enabled` |
| Allow friend requests | `settings.allow_friend_requests` | `allow_friend_requests` |
| Learning schedules list | `settings.preferred_learning_schedules` | Use schedule CRUD doc |

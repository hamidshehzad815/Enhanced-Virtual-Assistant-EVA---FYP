# Learning Schedules API

CRUD for labeled weekly learning slots (`preferred_learning_schedules`).

**This is the only way to create, update, or delete schedules.**  
Do not send `preferred_learning_schedules` on `PATCH /api/settings` (returns `400`).

Schedules are still **visible** on `GET /api/settings` under `data.settings.preferred_learning_schedules`.

---

## Data model

### `LearningSchedule`

| Field | Type | Required on create | Rules |
|-------|------|-------------------|-------|
| `id` | `string` | No | Auto-generated UUID if omitted; max 64 chars; unique |
| `label` | `string` | Yes | Max 80 chars; unique per user (case-insensitive) |
| `slots` | `ScheduleSlot[]` | Yes | Min 1 slot; max 20 schedules per user |

### `ScheduleSlot`

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `day` | `number` | Yes | `0` = Monday, `1` = Tuesday, … `6` = Sunday |
| `time` | `string` | Yes | `"HH:mm"` 24-hour |
| `duration_minutes` | `number` | Yes | Integer `15`–`240` |

**Day reference:**

| `day` | Weekday |
|-------|---------|
| 0 | Monday |
| 1 | Tuesday |
| 2 | Wednesday |
| 3 | Thursday |
| 4 | Friday |
| 5 | Saturday |
| 6 | Sunday |

---

## `GET /api/settings/learning-schedules`

List all schedules (same data as in full settings GET).

| | |
|---|---|
| **Auth** | Required |
| **Method** | `GET` |
| **Path** | `/api/settings/learning-schedules` |

### Success `200`

```json
{
  "status": "success",
  "data": {
    "timezone": "Asia/Karachi",
    "preferred_learning_schedules": [
      {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "label": "Evening study",
        "slots": [
          { "day": 1, "time": "19:00", "duration_minutes": 60 },
          { "day": 3, "time": "19:00", "duration_minutes": 90 }
        ]
      }
    ]
  }
}
```

---

## `POST /api/settings/learning-schedules`

Create one new schedule.

| | |
|---|---|
| **Auth** | Required |
| **Method** | `POST` |
| **Path** | `/api/settings/learning-schedules` |

### Request body

```json
{
  "label": "Morning study",
  "slots": [
    { "day": 0, "time": "09:00", "duration_minutes": 45 }
  ]
}
```

Optional: `"id": "custom-id"` (must not already exist).

### Success `201`

```json
{
  "status": "success",
  "message": "Learning schedule created",
  "data": {
    "timezone": "Asia/Karachi",
    "schedule": {
      "id": "generated-or-custom-id",
      "label": "Morning study",
      "slots": [
        { "day": 0, "time": "09:00", "duration_minutes": 45 }
      ]
    },
    "preferred_learning_schedules": [ ]
  }
}
```

`preferred_learning_schedules` = full updated list including the new schedule.

### Errors

| Status | When |
|--------|------|
| `400` | Validation (duplicate label, invalid day/time, missing duration, max 20 schedules) |
| `409` | Slot conflicts with existing task at same weekday/time; quiet hours overlap; cross-schedule slot overlap |

---

## `PATCH /api/settings/learning-schedules/:scheduleId`

Update label and/or slots for one schedule.

| | |
|---|---|
| **Auth** | Required |
| **Method** | `PATCH` |
| **Path** | `/api/settings/learning-schedules/:scheduleId` |
| **URL param** | `scheduleId` — the schedule's `id` |

### Request body (partial)

```json
{
  "label": "Early morning"
}
```

```json
{
  "slots": [
    { "day": 0, "time": "08:00", "duration_minutes": 60 }
  ]
}
```

Both fields optional; omitted fields keep existing values.  
`id` in URL cannot be changed.

### Success `200`

```json
{
  "status": "success",
  "message": "Learning schedule updated",
  "data": {
    "timezone": "Asia/Karachi",
    "schedule": { },
    "preferred_learning_schedules": [ ]
  }
}
```

### Errors

| Status | When |
|--------|------|
| `400` | Validation error |
| `404` | `scheduleId` not found |
| `409` | Schedule linked to active/paused learning plan (when changing slots); task conflict; quiet hours conflict |

**Plan-linked message (slots change):**  
*"This schedule is linked to an active or paused learning plan. Pause, complete, or delete that plan before changing its times."*

---

## `DELETE /api/settings/learning-schedules/:scheduleId`

Remove one schedule.

| | |
|---|---|
| **Auth** | Required |
| **Method** | `DELETE` |
| **Path** | `/api/settings/learning-schedules/:scheduleId` |
| **Body** | None |

### Success `200`

```json
{
  "status": "success",
  "message": "Learning schedule deleted",
  "data": {
    "timezone": "Asia/Karachi",
    "preferred_learning_schedules": [ ]
  }
}
```

### Errors

| Status | When |
|--------|------|
| `404` | Schedule not found |
| `409` | Schedule linked to active or paused learning plan |

**Plan-linked message:**  
*"This schedule is linked to an active or paused learning plan. Complete or delete that plan before removing this schedule."*

---

## Validation rules (all write routes)

| Rule | Detail |
|------|--------|
| Max schedules | 20 per user |
| Unique labels | Case-insensitive |
| Unique ids | Per user |
| One slot per day | Within a single schedule |
| No duplicate day+time | Across different schedules (cross-schedule conflict) |
| Task conflict | Slot must not overlap existing non-complete task at same weekday/time |
| Quiet hours | Slots must not fall inside enabled quiet-hour blocks when quiet hours are ON |

---

## Removed / deprecated routes

| Route | Status |
|-------|--------|
| `PATCH /api/settings/learning-schedule` | **Removed** — returns `404` |
| `preferred_learning_schedules` on `PATCH /api/settings` | **Rejected** — returns `400` |

---

## Frontend workflow

```
Load settings screen     → GET /api/settings
Load schedules only      → GET /api/settings/learning-schedules  (optional)

Add schedule             → POST /api/settings/learning-schedules
Edit schedule            → PATCH /api/settings/learning-schedules/:id
Delete schedule          → DELETE /api/settings/learning-schedules/:id

Change quiet hours       → PATCH /api/settings  (see settings-api.md)
Change toggles/reminders → PATCH /api/settings
```

After any schedule write, refresh UI from `data.preferred_learning_schedules` in the response (or re-fetch `GET /api/settings`).

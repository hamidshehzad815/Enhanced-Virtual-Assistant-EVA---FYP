# Roadmaps — Frontend Actions Guide

Complete UI reference for **learning roadmaps (plans)** and **sessions**.  
Use this with [roadmaps-api.md](./roadmaps-api.md) for request/response shapes.

---

## 1. Two levels (do not mix them up)

| Level | API object | What it is | User-facing name |
|-------|------------|------------|------------------|
| **Plan** | `data.roadmap` | Whole learning goal for one language | “Python basics plan” |
| **Session** | `data.session` or `roadmap.sessions[]` | One lesson in that plan | “Session 3: Control flow” |

**Plan status** (`roadmap.status`) controls whether **any** session can be edited.  
**Session state** (`session_state`) controls **which buttons** appear on the current session.

---

## 2. Stored vs computed fields (sessions)

| Field | Stored in DB? | Who sets it | Use in UI for |
|-------|---------------|-------------|---------------|
| `status` | Yes | Server on complete/skip | Progress chips, history |
| `session_state` | **No** (computed) | Server on every GET | **Buttons & lock UI** |
| `is_current` | **No** (computed) | Server on every GET | Highlight active row |
| `unlock_at` | **No** (computed) | Server on every GET | Countdown when locked |

**Rule:** Never build action buttons from `status` alone. Always use **`session_state`** + **`roadmap.status`**.

---

## 3. API endpoints (frontend map)

| Screen action | Method | Endpoint | Response to use |
|---------------|--------|----------|-----------------|
| Roadmap list (all plans) | `GET` | `/api/roadmaps/plans` | `data.roadmaps` |
| Roadmap + sessions | `GET` | `/api/roadmaps/:goalId` | `data.roadmap.sessions` |
| Session popup / detail | `GET` | `/api/learning/:goalId/sessions/:sessionId` | **`data.session`** |
| Reschedule session | `PATCH` | `/api/learning/:goalId/sessions/:sessionId` | `{ "scheduled_date": "YYYY-MM-DD" }` |
| Complete session | `PATCH` | same | `{ "status": "completed" }` |
| Skip session | `PATCH` | same | `{ "status": "skipped" }` |
| Pause plan | `PATCH` | `/api/learning/:goalId/status` | `{ "status": "paused" }` |
| Resume plan | `PATCH` | same | `{ "status": "active" }` |
| Cancel / remove plan | `PATCH` | same | `{ "status": "cancelled" }` |

**IDs:** `goalId` = `roadmap.id`, `sessionId` = `sessions[].id`.

After any **PATCH**, refresh from `data.roadmap` + `data.session` in the response.

---

## 4. Plan (`roadmap`) — fields & editability

| Field | Editable? | Notes |
|-------|-----------|-------|
| `id` | No | Use as `goalId` in URLs |
| `title` | No | Display only |
| `language` / `language_key` | No | Display only |
| `track_label` | No | e.g. “Basics”, “Intermediate” |
| `start_date` / `end_date` | No | Display only |
| `total_topics` / `completed_topics` / `progress_percent` | No | Progress bar |
| `sessions_summary` | No | Counts: completed, skipped, pending, ongoing |
| `sessions[]` | No | List on roadmap screen |
| **`status`** | **Yes** | Only via `PATCH .../status` |

### Plan `status` values

| `roadmap.status` | Meaning | Can edit sessions? | Plan-level buttons |
|------------------|---------|--------------------|--------------------|
| `active` | Learning in progress | **Yes** (if session rules allow) | **Pause**, **Cancel** |
| `paused` | Temporarily stopped | **No** | **Resume**, **Cancel** |
| `completed` | All sessions done | **No** | None (read-only) |
| `cancelled` | Removed | **No** | Hidden / not returned |

---

## 5. Plan actions — full table

**Endpoint:** `PATCH /api/learning/:goalId/status`

| Current plan status | Action | Request body | New status | Allowed? | HTTP if blocked |
|---------------------|--------|--------------|------------|----------|-----------------|
| `active` | Pause | `{ "status": "paused" }` | `paused` | Yes | — |
| `active` | Cancel | `{ "status": "cancelled" }` | `cancelled` | Yes | — |
| `active` | Resume | `{ "status": "active" }` | — | **No** | `400` |
| `paused` | Resume | `{ "status": "active" }` | `active` | Yes | — |
| `paused` | Cancel | `{ "status": "cancelled" }` | `cancelled` | Yes | — |
| `paused` | Pause | `{ "status": "paused" }` | — | **No** | `400` |
| `completed` | Any | any | — | **No** | `400` |
| `cancelled` | Any | any | — | **No** | `404` |

**On resume:** backend may rebase future session dates (optional `rebuild` in response).

**On cancel:** plan soft-deleted; remove from roadmap UI.

---

## 6. Session — fields to show in popup

| Field | Always show? | When |
|-------|--------------|------|
| `title` | Yes | — |
| `order` | Yes | e.g. “Session 2 of 8” with `roadmap.total_topics` |
| `scheduled_date` | Yes | Date & time in user TZ |
| `estimated_duration` | Yes | e.g. “90 min” |
| `resources[]` | Yes | YouTube links, thumbnails |
| `session_state` | Yes | Badge: Locked / Upcoming / In progress / Overdue / Done |
| `unlock_at` | If `session_state === "locked"` | Countdown timer |
| `completed_at` | If done or skipped | — |
| `is_current` | Optional | Highlight row on list |

### Read-only in popup (never editable)

`title`, `order`, `resources`, `estimated_duration`, `is_current`, `unlock_at`, `session_state`, `completed_at`.

### User-editable (via PATCH only)

| User action | PATCH field | Value |
|-------------|-------------|-------|
| Pick new date | `scheduled_date` | `"YYYY-MM-DD"` (learning day) |
| Mark done | `status` | `"completed"` |
| Skip | `status` | `"skipped"` |

---

## 7. Session `session_state` — meanings

Only the **current** session (`is_current: true`) goes through the lock timeline.  
Other sessions use simpler states.

| `session_state` | `is_current` | Meaning |
|-----------------|--------------|---------|
| `locked` | `true` | Too early; wait until `unlock_at` |
| `unlocked_future` | `true` | Unlocked but before scheduled start |
| `ongoing` | `true` | Inside session window (start → start + duration) |
| `overdue` | `true` | Window ended, not completed |
| `completed` | any | Finished |
| `skipped` | any | Skipped |
| `upcoming` | `false` | Not current; waiting in queue |

**Timeline (current session):**

```
locked  →  unlocked_future  →  ongoing  →  overdue
         (before start)      (during)     (after window)
```

Default session window = **`estimated_duration`** minutes (usually **90**).

---

## 8. Session buttons — by `session_state`

**Requires:** `roadmap.status === "active"` **and** `is_current === true`.

| `session_state` | Reschedule | Skip | Complete | UI notes |
|-----------------|------------|------|----------|----------|
| `locked` | No | No | No | Show countdown from `unlock_at` |
| `unlocked_future` | **Yes** | **Yes** | No | “Not started yet” |
| `ongoing` | **Yes** | No | **Yes** | “In progress” |
| `overdue` | **Yes** | No | **Yes** | “Overdue” warning |
| `completed` | No | No | No | Read-only |
| `skipped` | No | No | No | Read-only |

---

## 9. Non-current sessions (`is_current: false`)

User can **open** popup for context; **no** session PATCH actions.

| `session_state` | Typical case | Show in popup | Buttons |
|-----------------|--------------|---------------|---------|
| `completed` | Past session | Title, date, resources, `completed_at` | None |
| `skipped` | Past session | Title, date, `completed_at` | None |
| `upcoming` | Future in queue | Title, scheduled date (preview) | None |

---

## 10. Master matrix — plan status × session state

Use this single table to decide **everything** on the session popup.

| Plan `status` | `is_current` | `session_state` | Session actions | Plan actions to show |
|---------------|--------------|-----------------|-----------------|----------------------|
| `active` | `true` | `locked` | None | Pause, Cancel |
| `active` | `true` | `unlocked_future` | Reschedule, Skip | Pause, Cancel |
| `active` | `true` | `ongoing` | Reschedule, Complete | Pause, Cancel |
| `active` | `true` | `overdue` | Reschedule, Complete | Pause, Cancel |
| `active` | `false` | `completed` / `skipped` / `upcoming` | None | Pause, Cancel |
| `paused` | any | any | **None** | **Resume**, Cancel |
| `paused` | any | any | — | Banner: “Resume plan to continue” |
| `completed` | any | any | None | None |
| `cancelled` | — | — | — | Hide roadmap |

---

## 11. Reschedule rules (when button is shown)

| Rule | Detail |
|------|--------|
| Plan | Must be `active` |
| Session | Must be `is_current: true` |
| Lock | `session_state` must **not** be `locked` |
| Date format | `YYYY-MM-DD` |
| Date | Today or future (user timezone) |
| Weekday | Must be a **learning day** from user settings |
| Conflicts | No task overlap, no quiet hours → else `409` |
| Side effect | Later pending sessions may **rebase**; `end_date` may change |

---

## 12. Complete & skip rules

| Action | `session_state` must be | Blocked message (examples) |
|--------|-------------------------|----------------------------|
| **Complete** | `ongoing` or `overdue` | “has not started yet” / “still locked” |
| **Skip** | `unlocked_future` only | “in progress” / “overdue” / “still locked” |
| Either | Not `completed` / `skipped` | “cannot be changed” |
| Either | Must be current session | “Only the current session…” |

---

## 13. What happens after each action

| User action | Session changes | Plan changes | Next session |
|-------------|-----------------|----------------|--------------|
| **Complete** | `status → completed`, `completed_at` set | `completed_topics++`; may → `completed` if all done | Next `pending` → `is_current: true` |
| **Skip** | `status → skipped`, `completed_at` set | Progress updated | Next `pending` → current |
| **Reschedule** | New `scheduled_date` | `end_date` may update | Later sessions may shift |
| **Pause plan** | No change | `status → paused` | All session actions blocked |
| **Resume plan** | Dates may rebase | `status → active` | Re-fetch roadmap |
| **Cancel plan** | Soft-deleted | `cancelled` | Leave roadmap screen |

Always **re-fetch** or use PATCH response `data.roadmap` / `data.session` — `is_current`, `unlock_at`, and `session_state` all update together.

---

## 14. Suggested UI components

| Component | Data source | Behavior |
|-----------|-------------|----------|
| Plan picker / list | `GET /api/roadmaps/plans` | On select → `GET /api/roadmaps/:goalId` |
| Session list | `roadmap.sessions[]` | Highlight where `is_current` |
| Session popup | `GET .../sessions/:sessionId` | Show §6 fields |
| Action bar | `session_state` + `roadmap.status` | §8 + §10 |
| Plan menu | `roadmap.status` | §5 |
| Lock banner | `unlock_at` | Countdown until unlock |
| Progress header | `progress_percent`, `sessions_summary` | Top of roadmap screen |

---

## 15. Button visibility — pseudocode

```text
function sessionActions(session, roadmap):
  if roadmap.status != "active":
    return []   // show "Resume plan" on plan menu if paused

  if !session.is_current:
    return []

  switch session.session_state:
    case "locked":           return []
    case "unlocked_future":  return [RESCHEDULE, SKIP]
    case "ongoing":          return [RESCHEDULE, COMPLETE]
    case "overdue":          return [RESCHEDULE, COMPLETE]
    case "completed":
    case "skipped":          return []

function planActions(roadmap):
  switch roadmap.status:
    case "active":    return [PAUSE, CANCEL]
    case "paused":    return [RESUME, CANCEL]
    case "completed": return []
```

---

## 16. Common errors (show to user)

| HTTP | When | Example message |
|------|------|-----------------|
| `400` | Bad body, wrong plan state, terminal session | “Only active learning plans…” |
| `404` | Wrong id or not owner | “Session not found” |
| `409` | Locked, wrong session, overlap, quiet hours | “That session is still locked…” |

---

## 17. Related docs

| Doc | Purpose |
|-----|---------|
| [roadmaps-api.md](./roadmaps-api.md) | Full API request/response examples |
| [settings-learning-schedules-api.md](./settings-learning-schedules-api.md) | Learning days (required for reschedule) |

---

## 18. Quick checklist for frontend dev

- [ ] Use `session_state` for session buttons, not `status`
- [ ] Check `roadmap.status === "active"` before enabling session actions
- [ ] Only `is_current` session can be patched
- [ ] Show `unlock_at` countdown when `session_state === "locked"`
- [ ] `GET` session detail for popup; `GET` roadmap for list
- [ ] After PATCH, refresh from response `data.session` + `data.roadmap`
- [ ] Paused plan → show Resume on plan level, disable session buttons
- [ ] Completed/skipped sessions → read-only popup

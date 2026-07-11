# EVA — Complete Manual Testing Guide

**Purpose:** End-to-end manual verification of everything implemented so far.  
**Audience:** Developers / QA testing via Postman, curl, MongoDB Compass, Redis CLI, or `EVA_Test_Automation/manualLearningAddTesting/index.html`.  
**Companion docs:** `PROJECT_COMPLETION_REPORT.md` (what is built), `BACKEND_API_DOCUMENTATION.md` (REST reference), `*_command_flow.txt` (SYNC WITH CODE sections).

**How to use:** Work top to bottom once for a full regression, or jump to a section. Mark each row **PASS / FAIL / SKIP** and note bugs in the Notes column.

---

## Table of contents

1. [Prerequisites](#1-prerequisites)
2. [Test accounts and variables](#2-test-accounts-and-variables)
3. [Verification cheat sheet](#3-verification-cheat-sheet)
4. [15-minute smoke test](#4-15-minute-smoke-test)
5. [Settings and learning schedules](#5-settings-and-learning-schedules)
6. [Scheduling — Add](#6-scheduling--add)
7. [Scheduling — Delete](#7-scheduling--delete)
8. [Scheduling — Update](#8-scheduling--update)
9. [Scheduling — Show](#9-scheduling--show)
10. [Behavioral analytics](#10-behavioral-analytics)
11. [Learning — Add (create)](#11-learning--add-create)
12. [Learning — Lifecycle and APIs](#12-learning--lifecycle-and-apis)
13. [Collaboration (tasks and learning)](#13-collaboration-tasks-and-learning)
14. [Tasks page REST APIs](#14-tasks-page-rest-apis)
15. [Dashboard](#15-dashboard)
16. [Notifications and email](#16-notifications-and-email)
17. [Google Calendar integration](#17-google-calendar-integration)
18. [Friends (prerequisite for collaborators)](#18-friends-prerequisite-for-collaborators)
19. [Cross-command and edge cases](#19-cross-command-and-edge-cases)
20. [Automated regression (optional)](#20-automated-regression-optional)
21. [Sign-off checklist](#21-sign-off-checklist)

---

## 1. Prerequisites

### 1.1 Services (all must be healthy)


| Service      | How to check                                                | Default                            |
| ------------ | ----------------------------------------------------------- | ---------------------------------- |
| MongoDB      | Node logs “connected”; `GET /health` → `mongodb: connected` | `mongodb://localhost:27017/eva_db` |
| Node backend | `GET http://localhost:3000/health`                          | Port **3000**                      |
| AI server    | Health via Node or `GET http://localhost:8080/`             | Port **8080**                      |
| Redis        | AI pending flows work; `redis-cli ping` → PONG              | `localhost:6379`                   |
| Duckling     | Date parsing in add/show/update                             | `http://localhost:8000`            |


### 1.2 Optional but recommended for full coverage


| Item                 | Why                                    |
| -------------------- | -------------------------------------- |
| Roadmap seed         | Learning add needs `roadmap_resources` |
| YouTube fetch        | Topics show `resources[]` with links   |
| SMTP configured      | Email notifications                    |
| Firebase credentials | Push notifications                     |
| Google OAuth tokens  | Calendar sync on task/learning create  |


### 1.3 Data hygiene

- Prefer a **dedicated test user** (or wipe `tasks`, `learning_goals`, Redis `context:{userId}`) before a full run.
- Set user **timezone** explicitly (`PATCH /api/profile` or register flow) — e.g. `Asia/Karachi` — and use the same zone when validating displayed times.

---

## 2. Test accounts and variables

### 2.1 Minimum users


| User                | Role                                                  |
| ------------------- | ----------------------------------------------------- |
| **User A (owner)**  | Primary tester — JWT `accessToken`, `userId`          |
| **User B (friend)** | Collaborator tests — must be **accepted friend** of A |


### 2.2 Postman / environment variables


| Variable      | Example                 | Source                      |
| ------------- | ----------------------- | --------------------------- |
| `baseUrl`     | `http://localhost:3000` | Node                        |
| `accessToken` | JWT                     | `POST /api/auth/login`      |
| `userId`      | ObjectId string         | login / `GET /api/auth/me`  |
| `sessionId`   | ObjectId string         | First `POST /api/chat/process` response (`session_id`) |
| `goalId`      | ObjectId                | After learning create       |
| `scheduleId`  | UUID string             | From learning schedules API |
| `friendToken` | JWT                     | User B login                |


**Auth header (protected routes):**

```http
Authorization: Bearer {{accessToken}}
Content-Type: application/json
```

### 2.3 Chat request template (all command tests)

```http
POST {{baseUrl}}/api/chat/process
Authorization: Bearer {{accessToken}}

{
  "message": "YOUR_MESSAGE_HERE",
  "session_id": "{{sessionId}}",
  "input_type": "text"
}
```

**Inspect in response:**


| Field                | Meaning                                                                        |
| -------------------- | ------------------------------------------------------------------------------ |
| `response_text`      | EVA reply shown to user                                                        |
| `intent`             | Routed intent e.g. `scheduling_add`, `learning_create`                         |
| `ai_status`          | Handler status: `success`, `pending`, `conflict`, `not_found`, `blocked`, etc. |
| `data.route.pending` | Pending state when `ai_status` = `pending`                                     |
| `notifications`      | Insert/dispatch summary from Node                                              |


**Direct AI (debug only):**

```http
POST http://localhost:8080/process
{
  "message": "...",
  "user_id": "{{userId}}",
  "session_id": "{{sessionId}}",
  "input_type": "text",
  "timestamp": "2026-05-20T12:00:00Z"
}
```

---

## 3. Verification cheat sheet

### 3.1 Redis pending context

```bash
redis-cli GET "context:YOUR_USER_ID"
```


| Field                   | Values                                                                 |
| ----------------------- | ---------------------------------------------------------------------- |
| `expected_response`     | `free_text`, `yes_no`, `number`                                        |
| `pending_action.intent` | `add`, `delete`, `update`, `learning_create`, `behavioral`, …          |
| `pending_action.stage`  | update/learning only: e.g. `identify`, `schedule_choice`, `duration`   |
| `missing_entity`        | Often `task_name`, `date`, `time`, `day`                               |
| `pending_reason`        | add: `duplicate`, `quiet_hours`, `past_datetime`, `time_suggestion`, … |


TTL resets on each write (~300s). **Cancel** in chat should delete the key.

### 3.2 MongoDB collections


| Collection             | When to check                                   |
| ---------------------- | ----------------------------------------------- |
| `tasks`                | Add/update/delete/show/learning sessions        |
| `activity_logs`        | Add, update, delete, `goal_created`             |
| `learning_goals`       | Learning add, pause/cancel/complete             |
| `roadmap_topics`       | Learning plan topics, completion                |
| `user_settings`        | Schedules, quiet hours, notification flags      |
| `integrations`         | `provider: google_calendar`                     |
| `notifications`        | Invites, task_scheduled, collaboration_response |
| `conversation_history` | Chat turns saved                                |
| `friends`              | Collaborator eligibility                        |


### 3.3 Task fields to verify


| Field                                   | Notes                                                           |
| --------------------------------------- | --------------------------------------------------------------- |
| `status`                                | Stored: `pending` or `complete`                                 |
| `display_status`                        | Only in **Node API** response: pending/ongoing/overdue/complete |
| `google_calendar_event_id`              | Set if Calendar connected                                       |
| `learning_plan_id`, `learning_topic_id` | Learning session tasks                                          |
| `collaborators[].status`                | `pending`, `accepted`, `rejected`                               |
| `is_deleted`                            | `true` after delete                                             |


### 3.4 Weekday numbers (schedules and analytics)

`0` = Monday … `6` = Sunday (same in settings slots and analytics).

---

## 4. 15-minute smoke test

Run in order. If any step fails, fix environment before full regression.


| #   | Action                                                                                              | Pass?                                            |
| --- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| S1  | `GET /health` → Mongo + AI connected                                                                | ☐                                                |
| S2  | Login → save token                                                                                  | Pass                                             |
| S3  | `POST /api/chat/process` without `session_id` → save `session_id` from response                     | Pass                                             |
| S4  | Chat: `add team standup tomorrow 10am for 30 minutes` → success, task in DB                         | Pass                                             |
| S5  | Chat: `show my tasks tomorrow` → lists task                                                         | Fail on this input Pass on "show tomorrow tasks" |
| S6  | Chat: `when am i most productive` → reply (or not-enough-data if <20 logs)                          | pass                                             |
| S7  | `GET /api/settings/learning-schedules` → at least one schedule (or create in §5)                    | pass                                             |
| S8  | Chat: `learn Python basics in 2 weeks starting Monday` → schedule prompt → reply `1` → goal created | pass                                             |
| S9  | `GET /api/learning` → goal visible                                                                  | pass                                             |
| S10 | `GET /api/dashboard` → learning + today_schedule                                                    | pass                                             |


---

## 5. Settings and learning schedules

Test via **REST** (`/api/settings/learning-schedules`). Required before learning add.

### SCH-01 — List empty / populated

```http
GET {{baseUrl}}/api/settings/learning-schedules
```


| Pass criteria                               |
| ------------------------------------------- |
| `200`, `preferred_learning_schedules` array |


### SCH-02 — Create first schedule

```http
POST {{baseUrl}}/api/settings/learning-schedules

{
  "label": "Evening study",
  "slots": [
    { "day": 0, "time": "18:00", "duration_minutes": 60 },
    { "day": 2, "time": "19:00", "duration_minutes": 90 }
  ]
}
```


| Pass criteria                                                                          |
| -------------------------------------------------------------------------------------- |
| `201`, schedule has `id`, slots returned                                               |
| Same weekday+time not allowed **inside** one schedule (duplicate day in slots → `400`) |


### SCH-03 — Duplicate label rejected

POST same `label` again (different slots).


| Pass criteria                     |
| --------------------------------- |
| `400`, message about unique label |


### SCH-04 — Cross-schedule same day+time rejected

With schedule A: Monday 18:00, POST schedule B with **same** Monday 18:00, different label.


| Pass criteria                                               |
| ----------------------------------------------------------- |
| `409 Conflict`, message names conflicting schedule and slot |


### SCH-05 — Same day, different time allowed

Monday 18:00 vs Monday 20:00 on second schedule.


| Pass criteria |
| ------------- |
| `201`         |


### SCH-06 — Update schedule

```http
PATCH {{baseUrl}}/api/settings/learning-schedules/{{scheduleId}}
{ "label": "Evening study v2" }
```


| Pass criteria        |
| -------------------- |
| `200`, label updated |


### SCH-07 — Delete schedule (no active goal)

DELETE schedule not linked to active `learning_goals.learning_schedule_id`.


| Pass criteria            |
| ------------------------ |
| `200`, removed from list |


### SCH-08 — Delete blocked when active goal uses schedule

Create learning plan using schedule X, then DELETE schedule X.


| Pass criteria                             |
| ----------------------------------------- |
| `409`, explains active plan blocks delete |


### SCH-09 — Quiet hours (for ADD-04)

```http
PATCH {{baseUrl}}/api/settings

{
  "quiet_hours_enabled": true,
  "quiet_hours": [
    { "label": "Sleep", "start": "22:00", "end": "07:00", "enabled": true }
  ]
}
```


| Pass criteria                            |
| ---------------------------------------- |
| `GET /api/settings` reflects quiet hours |


### SCH-10 — Analytics thresholds (behavioral)

In settings document or PATCH: `analytics_min_tasks_threshold` (default 20), `analytics_min_tasks_per_day` (default 5).

---

## 6. Scheduling — Add

**Intent:** `scheduling_add` · **Redis intent:** `add`

### ADD-01 — Happy path (one shot)


| Step | Message                                        |
| ---- | ---------------------------------------------- |
| 1    | `add physics exam on Monday at 4pm for 1 hour` |



| Pass criteria                                                  |
| -------------------------------------------------------------- |
| `intent` = `scheduling_add`, `ai_status` = `success`           |
| `tasks`: title ~ physics exam, `duration` 60, `status` pending |
| `activity_logs`: `action_type` = `task_created`                |
| `conversation_history` updated                                 |


### ADD-02 — Missing fields (multi-turn)


| Step | Message                                           |
| ---- | ------------------------------------------------- |
| 1    | `add chemistry assignment`                        |
| 2    | Wait for prompt → provide date e.g. `next Monday` |
| 3    | Provide time e.g. `3pm`                           |



| Pass criteria                                                              |
| -------------------------------------------------------------------------- |
| Step 1: `ai_status` pending, `missing_entity` task_name or date/time chain |
| Redis `context:{userId}` exists between steps                              |
| Final: task created                                                        |


### ADD-03 — Duplicate same day

| Pre | Task "physics exam" already on target Monday |
| 1 | `add physics exam on Monday at 4pm` |


| Pass criteria                                                                        |
| ------------------------------------------------------------------------------------ |
| pending `yes_no`, `pending_reason` duplicate (or equivalent in `data.route.pending`) |
| `yes` → second task created; `no` → no new task                                      |


### ADD-04 — Quiet hours

| Pre | Quiet hours enabled; time inside block |
| 1 | `add quiz today at 11pm` (adjust to hit your block) |


| Pass criteria                          |
| -------------------------------------- |
| pending `yes_no`, quiet hour mentioned |
| `yes` → creates; `no` → does not       |


### ADD-05 — Time overlap (hard reject)

| Pre | Task Monday 5:00 PM, 60 min |
| 1 | `add task B on Monday at 5:30pm for 1 hour` |


| Pass criteria                                      |
| -------------------------------------------------- |
| `ai_status` = `conflict` (or conflict in response) |
| No new task inserted                               |


### ADD-06 — Behavioral time suggestion

| Pre | User has ≥20 completed logs; missing time path |
| 1 | `add workshop next Tuesday` (no time) |
| 2 | If offered 1/2: reply `1` or `2` |


| Pass criteria                                             |
| --------------------------------------------------------- |
| Option 1: `scheduled_by` = `behavioral_analytics` on task |
| Suggestion uses productivity data (natural language)      |


### ADD-07 — Past time today

| 1 | Add task today at a time already passed |


| Pass criteria                                        |
| ---------------------------------------------------- |
| Re-asks time or date; `pending_reason` past_datetime |


### ADD-08 — Collaborator happy path

| Pre | User B is accepted friend |
| 1 | `add group study on Friday 6pm with USER_B_USERNAME` |


| Pass criteria                                   |
| ----------------------------------------------- |
| Task created; `collaborators[0].status` pending |
| Notification `collaboration_invite` for B       |
| `notifications.inserted` ≥ 1                    |


### ADD-09 — Collaborator not found / not friend

| 1 | `add task tomorrow 3pm with notauser12345` |


| Pass criteria                              |
| ------------------------------------------ |
| `validation_error` or clear error; no task |


### ADD-10 — Max 2 collaborators

| 1 | `add task Monday 3pm with user1, user2, user3` |


| Pass criteria                   |
| ------------------------------- |
| Error about max 2 collaborators |


### ADD-11 — Cancel mid-flow

| 1 | `add something` → pending |
| 2 | `cancel` |


| Pass criteria                   |
| ------------------------------- |
| Redis key gone; no partial task |


### ADD-12 — Google Calendar (if connected)

| Pre | `POST /api/integrations/google/connect` with valid tokens |
| 1 | ADD-01 again |


| Pass criteria                                                   |
| --------------------------------------------------------------- |
| Task has `google_calendar_event_id`; reply may mention calendar |


---

## 7. Scheduling — Delete

**Intent:** `scheduling_delete` · **Redis intent:** `delete`

### DEL-01 — Single match confirm

| Pre | One matching pending task |
| 1 | `delete physics exam on Monday` |


| Pass criteria                                |
| -------------------------------------------- |
| pending `yes_no`                             |
| `yes` → `is_deleted: true`; `no` → unchanged |


### DEL-02 — Multi match (2–5)

| Pre | 2+ tasks match filter |
| 1 | `delete physics` |


| Pass criteria                             |
| ----------------------------------------- |
| Numbered list, `expected_response` number |
| Reply `1` → confirm → yes/no              |
| Reply `all` → bulk confirm                |


### DEL-03 — Too broad (6+)

| Pre | Many tasks match name |
| 1 | `delete task` |


| Pass criteria             |
| ------------------------- |
| Asks to narrow; no delete |


### DEL-04 — Not found

| 1 | `delete nonexistent task xyz on Monday` |


| Pass criteria                       |
| ----------------------------------- |
| not_found style reply; no DB change |


### DEL-05 — Invalid filter date

| 1 | `delete physics exam on blursday` → pending date |
| 2 | Provide valid date |


| Pass criteria                       |
| ----------------------------------- |
| `missing_entity` date on retry path |


### DEL-06 — Calendar event removed

| Pre | Task had `google_calendar_event_id` |
| 1 | Delete with confirm yes |


| Pass criteria                                   |
| ----------------------------------------------- |
| Event removed in Google Calendar (manual check) |


### DEL-07 — Cancel

| 1 | Start delete → pending → `cancel` |


| Pass criteria                   |
| ------------------------------- |
| Redis cleared; task not deleted |


---

## 8. Scheduling — Update

**Intent:** `scheduling_update` · **Redis intent:** `update` · **Stages:** `identify` → `what_to_update` → `confirm`

### UPD-01 — Identify then ask what to change

| 1 | `update physics exam on Monday` |


| Pass criteria                                      |
| -------------------------------------------------- |
| If no changes in message: pending `what_to_update` |


### UPD-02 — Single field change with confirm

| 1 | `change physics exam priority to high` |


| Pass criteria                                 |
| --------------------------------------------- |
| Summary + pending `yes_no` stage confirm      |
| `yes` → priority high in DB; `no` → unchanged |


### UPD-03 — Date and time together

| 1 | `move physics exam to Tuesday at 3pm` |


| Pass criteria                             |
| ----------------------------------------- |
| Both `due_datetime` updated after confirm |


### UPD-04 — Multi-match number pick

| Pre | 2+ "physics" tasks |
| 1 | `update physics priority to low` |


| Pass criteria                   |
| ------------------------------- |
| number → pick → confirm → apply |


### UPD-05 — Overlap block

| Pre | Another task at target slot |
| 1 | `move physics exam to Monday 5pm` (conflicting) |


| Pass criteria                                          |
| ------------------------------------------------------ |
| conflict; returns to what_to_update or blocked message |


### UPD-06 — Complete task locked

| Pre | Task `status: complete` |
| 1 | `mark physics exam as pending` |


| Pass criteria             |
| ------------------------- |
| `blocked`; still complete |


### UPD-07 — Mark complete

| Pre | Pending task |
| 1 | `mark physics exam complete` or update status via confirm |


| Pass criteria                                  |
| ---------------------------------------------- |
| `status` complete; log may be `task_completed` |


### UPD-08 — Calendar update

| Pre | Task has calendar event id |
| 1 | Change time with confirm yes |


| Pass criteria                          |
| -------------------------------------- |
| Google event time moves (manual check) |


### UPD-09 — Cancel at confirm

| 1 | Trigger confirm → reply `no` |


| Pass criteria                  |
| ------------------------------ |
| No DB change (main handles no) |


---

## 9. Scheduling — Show

**Intent:** `scheduling_show` · **No Redis pending**

### SHOW-01 — By date

| 1 | `show my tasks on Monday` |


| Pass criteria                               |
| ------------------------------------------- |
| `scheduling_show`; lists tasks or not_found |
| Times in user timezone                      |


### SHOW-02 — By task name

| 1 | `show physics exam` |


| Pass criteria                                                         |
| --------------------------------------------------------------------- |
| Filters by `task_name` (NER may send `subject` → scoped as task_name) |


### SHOW-03 — By priority / status

| 1 | `show high priority pending tasks` |


| Pass criteria                                    |
| ------------------------------------------------ |
| Filtered list ≤10 items; total mentioned if more |


### SHOW-04 — This week

| 1 | `show my tasks this week` |


| Pass criteria                             |
| ----------------------------------------- |
| Week range applied (message + date logic) |


### SHOW-05 — Overdue keyword

| Pre | Past-due pending tasks exist |
| 1 | `show my overdue tasks` |


| Pass criteria                       |
| ----------------------------------- |
| Lists overdue-related pending tasks |


### SHOW-06 — Relaxed title

| Pre | Task "physics midterm exam" |
| 1 | `show physics exam` |


| Pass criteria           |
| ----------------------- |
| May match relaxed title |


### SHOW-07 — Completed sort

| 1 | `show completed tasks` |


| Pass criteria                         |
| ------------------------------------- |
| Completed tasks ordered appropriately |


### SHOW-08 — Not found

| 1 | `show tasks on 31st february` or impossible filter |


| Pass criteria                      |
| ---------------------------------- |
| Graceful not_found / empty message |


### SHOW-09 — Blocked during yes/no pending (other command)

| Pre | Start delete → yes/no pending |
| 1 | `show my tasks tomorrow` |


| Pass criteria                                                            |
| ------------------------------------------------------------------------ |
| Blocked or told one request at a time (Model 1 multiple_command / block) |


### SHOW-10 — During free_text pending (edge)

| Pre | `add chemistry` pending date |
| 1 | `show all my tasks` |


| Pass criteria                                                                              |
| ------------------------------------------------------------------------------------------ |
| **Known behavior:** may be interpreted as add filter text, not show — document if observed |


---

## 10. Behavioral analytics

**Intent:** `behavioral` · **Read-only** · Thresholds: **20** global completed logs, **5** per weekday when filtered

### BEH-01 — Not enough data

| Pre | New user, <20 `task_completed` logs |
| 1 | `when am I most productive` |


| Pass criteria                                 |
| --------------------------------------------- |
| Explains need more history; no deep analytics |


### BEH-02 — Productive hours (general)

| Pre | ≥20 completed logs |
| 1 | `when am I most productive` |


| Pass criteria                                    |
| ------------------------------------------------ |
| Hour **ranges** and reliable days (not raw dump) |


### BEH-03 — Productive hours for one day

| 1 | `what are my best hours on Monday` |


| Pass criteria                                     |
| ------------------------------------------------- |
| Monday-specific; or insufficient day data message |


### BEH-04 — Productive days

| 1 | `which days am I most focused` |


| Pass criteria   |
| --------------- |
| Ranked weekdays |


### BEH-05 — Best time for day (pending)

| 1 | `find the best time for me` |
| 2 | `Friday` |


| Pass criteria                 |
| ----------------------------- |
| Step 1: pending, asks for day |
| Step 2: best range for Friday |


### BEH-06 — Completion rate

| 1 | `show my completion rate` |


| Pass criteria                   |
| ------------------------------- |
| Totals, on-time %, weekly trend |


### BEH-07 — Productivity report

| 1 | `give me my productivity report` |


| Pass criteria                                 |
| --------------------------------------------- |
| Combined days + hours + completion + avg time |


### BEH-08 — REST analytics mirror

```http
GET {{baseUrl}}/api/analytics/productivity
GET {{baseUrl}}/api/analytics/hours?day=monday
GET {{baseUrl}}/api/analytics/days
GET {{baseUrl}}/api/analytics/completion-trend
```


| Pass criteria                                         |
| ----------------------------------------------------- |
| `200` JSON aligns with chat answers (same thresholds) |


### BEH-09 — Cancel pending ask-day

| 1 | `best time for me` → pending |
| 2 | `cancel` |


| Pass criteria |
| ------------- |
| Redis cleared |


---

## 11. Learning — Add (create)

**Intent:** `learning_create` · **Order:** topic → start_date → **schedule_choice** → duration → create

### LRN-PRE — Schedules


| Pass criteria                                  |
| ---------------------------------------------- |
| At least one labeled schedule in settings (§5) |
| Roadmap seed done for chosen language          |


### LRN-01 — Full sentence + schedule choice (critical)


| Step | Message                                                                       |
| ---- | ----------------------------------------------------------------------------- |
| 1    | `want to learn Ruby loops from tomorrow for 3 weeks`                          |
| 2    | EVA lists schedule(s) — reply `**1`** to use listed schedule                  |
| 3    | (Optional) Test reply `**2**` separately — should direct to Settings, no plan |



| Pass criteria                                                          |
| ---------------------------------------------------------------------- |
| Step 1: **No goal yet** — only schedule prompt                         |
| Step 2: `ai_status` success; `learning_goals` + topics + tasks created |
| Reply mentions sessions / first dates                                  |
| `learning_schedule_id` set on goal                                     |


### LRN-02 — One schedule still asks 1 or 2

| Pre | Exactly one schedule in settings |
| 1 | Learning create message → reply `1` |


| Pass criteria                                              |
| ---------------------------------------------------------- |
| Same as LRN-01 — **must not** auto-pick without user reply |


### LRN-03 — No schedules in settings

| Pre | Delete all schedules |
| 1 | `learn Python for 2 weeks` |


| Pass criteria                             |
| ----------------------------------------- |
| Tells user to configure Settings; no goal |


### LRN-04 — Multi-turn missing topic

| 1 | `learn from Monday for 2 weeks` |
| 2 | `Python` |


| Pass criteria                |
| ---------------------------- |
| Topic pending then continues |


### LRN-05 — Unsupported language

| 1 | `learn COBOL for 2 weeks starting Monday` → schedule flow if needed |


| Pass criteria                      |
| ---------------------------------- |
| Lists supported languages; no goal |


### LRN-06 — Duplicate same track

| Pre | Active Python basics goal exists |
| 1 | `learn Python basics for 2 weeks starting next Monday` |


| Pass criteria                        |
| ------------------------------------ |
| Blocked with clear duplicate message |


### LRN-07 — Different subtopic allowed

| Pre | Active Python **basics** |
| 1 | `learn Python intermediate for 3 weeks starting Monday` → `1` |


| Pass criteria       |
| ------------------- |
| Second goal created |


### LRN-08 — Duration too short

| 1 | `learn Python basics for 5 days starting Monday` |


| Pass criteria                                |
| -------------------------------------------- |
| Error / ask for longer duration (min 7 days) |


### LRN-09 — Feasibility (not enough session slots)

| Pre | Short duration vs many roadmap topics |
| 1 | Create plan that cannot fit all sessions |


| Pass criteria                 |
| ----------------------------- |
| Explains need more weeks/days |


### LRN-10 — With collaborator

| Pre | Friend B |
| 1 | `learn Python basics in 3 weeks starting Monday with B_USERNAME` → `1` |


| Pass criteria                              |
| ------------------------------------------ |
| Goal has collaborator pending              |
| B receives `learning_collaboration_invite` |


### LRN-11 — Cancel mid-flow

| 1 | Start learn → pending → `cancel` |


| Pass criteria        |
| -------------------- |
| No goal/topics/tasks |


### LRN-12 — Subtopic alias / general

| 1 | `learn Python beginner for 2 weeks` → maps toward basics/general |
| 2 | `learn Python` only (no subtopic) → general roadmap |


| Pass criteria               |
| --------------------------- |
| Valid `roadmap_key` in goal |


---

## 12. Learning — Lifecycle and APIs

### LRN-API-01 — List goals

```http
GET {{baseUrl}}/api/learning
```


| Pass criteria                        |
| ------------------------------------ |
| Active/paused goals; progress fields |


### LRN-API-02 — Get goal + topics

```http
GET {{baseUrl}}/api/learning/{{goalId}}
GET {{baseUrl}}/api/learning/{{goalId}}/topics
```


| Pass criteria                                           |
| ------------------------------------------------------- |
| Topics ordered; `scheduled_date`; `resources` if seeded |


### LRN-API-03 — Pause / resume / cancel

```http
PATCH {{baseUrl}}/api/learning/{{goalId}}/status
{ "status": "paused" }
{ "status": "active" }
{ "status": "cancelled" }
```


| Pass criteria                                                       |
| ------------------------------------------------------------------- |
| Status updates; cancel soft-deletes linked tasks per implementation |


### LRN-API-04 — Complete topic (API)

```http
POST {{baseUrl}}/api/learning/{{goalId}}/topics/{{topicId}}/complete
```


| Pass criteria                                                        |
| -------------------------------------------------------------------- |
| Topic completed; `completed_topics` increments; linked task complete |


### LRN-API-05 — Topic complete via chat

| Pre | Pending topic scheduled today or pick from plan |
| 1 | `I completed today's learning session` |
| 2 | `I finished my Python session` |


| Pass criteria                  |
| ------------------------------ |
| Correct topic marked completed |
| Progress reply                 |


### LRN-API-06 — Last topic completes goal

| Pre | One topic left |
| 1 | Complete last topic (API or chat) |


| Pass criteria                                              |
| ---------------------------------------------------------- |
| Goal `status` completed; `completed_at`; `time_taken_days` |


### LRN-API-07 — display_status on learning tasks

```http
GET {{baseUrl}}/api/tasks?date=YYYY-MM-DD
```


| Pass criteria                                                         |
| --------------------------------------------------------------------- |
| Learning tasks show `display_status` pending/ongoing/overdue/complete |


---

## 13. Collaboration (tasks and learning)

### COL-T-01 — Task invite accept (API)

| Pre | Task with pending collaborator B |
| B | `POST /api/tasks/{{taskId}}/collaborators/respond` `{ "action": "accept" }` |


| Pass criteria                |
| ---------------------------- |
| Collaborator status accepted |


### COL-T-02 — Task invite reject

| B | `{ "action": "reject" }` |


| Pass criteria                                          |
| ------------------------------------------------------ |
| status rejected; owner may get notification if enabled |


### COL-L-01 — Learning invite accept

| B | `POST /api/learning/{{goalId}}/collaborators/respond` accept |


| Pass criteria                           |
| --------------------------------------- |
| B gets **cloned** goal + topics + tasks |
| Owner goal unchanged                    |


### COL-L-02 — Learning invite reject

| B | reject |


| Pass criteria                                                           |
| ----------------------------------------------------------------------- |
| Collaborator row rejected                                               |
| Owner gets `learning_collaboration_response` (in-app; email if enabled) |


### COL-L-03 — Email link (optional)

| Pre | SMTP + email enabled on owner |
| B | Open accept/reject link from email |


| Pass criteria                          |
| -------------------------------------- |
| HTML page success; same as API respond |


---

## 14. Tasks page REST APIs

### TASK-01 — List with display_status

```http
GET {{baseUrl}}/api/tasks?page=1&limit=20
```


| Pass criteria                             |
| ----------------------------------------- |
| Each task has `status` + `display_status` |


### TASK-02 — Filter pending

```http
GET {{baseUrl}}/api/tasks?status=pending
```


| Pass criteria      |
| ------------------ |
| Non-complete tasks |


### TASK-03 — Filter by date

```http
GET {{baseUrl}}/api/tasks?date=2026-05-20
```


| Pass criteria                          |
| -------------------------------------- |
| Only tasks on that local day (user TZ) |


### TASK-04 — Patch status

```http
PATCH {{baseUrl}}/api/tasks/{{taskId}}/status
{ "status": "complete" }
```


| Pass criteria                         |
| ------------------------------------- |
| Only `pending` or `complete` accepted |
| Returns enriched task                 |


### TASK-05 — Delete task (UI)

```http
DELETE {{baseUrl}}/api/tasks/{{taskId}}
```


| Pass criteria |
| ------------- |
| Soft delete   |


---

## 15. Dashboard

### DASH-01 — Full dashboard

```http
GET {{baseUrl}}/api/dashboard
```


| Pass criteria                                    |
| ------------------------------------------------ |
| `up_next` — next non-complete task today         |
| `daily_progress` — counts + percentage           |
| `learning[]` — goals with `next_topic`           |
| `today_schedule[]` — tasks with `display_status` |


### DASH-02 — After learning create


| Pass criteria                                           |
| ------------------------------------------------------- |
| New goal appears in `learning`                          |
| Today's learning tasks in `today_schedule` if due today |


---

## 16. Notifications and email

### NOT-01 — Task scheduled (owner)

| Pre | email_notifications_enabled true |
| 1 | ADD-01 |


| Pass criteria                                    |
| ------------------------------------------------ |
| `notifications` collection type `task_scheduled` |
| Email received (if SMTP ok)                      |


### NOT-02 — Collaboration invite

| 1 | ADD with collaborator |


| Pass criteria                                         |
| ----------------------------------------------------- |
| type `collaboration_invite`; push if token registered |


### NOT-03 — Learning collaboration response

| 1 | B rejects learning invite |


| Pass criteria                                        |
| ---------------------------------------------------- |
| Owner notification `learning_collaboration_response` |
| Email if enabled                                     |


### NOT-04 — Topic reminder (manual timing)

| Pre | Learning task due soon; reminder job running |
| Wait | Until job fires (~1 min cron) |


| Pass criteria                                     |
| ------------------------------------------------- |
| type `topic_reminder` not generic `task_reminder` |


---

## 17. Google Calendar integration

### CAL-01 — Connect

```http
POST {{baseUrl}}/api/integrations/google/connect

{
  "access_token": "ya29....",
  "refresh_token": "1//...",
  "calendar_id": "primary"
}
```


| Pass criteria                                        |
| ---------------------------------------------------- |
| `GET /api/integrations` shows google_calendar active |


### CAL-02 — Create on add

| 1 | ADD-01 |


| Pass criteria                      |
| ---------------------------------- |
| `google_calendar_event_id` on task |


### CAL-03 — Learning sessions

| 1 | LRN-01 success |


| Pass criteria                        |
| ------------------------------------ |
| Each learning task may have event id |


### CAL-04 — Update / delete

| 1 | UPD time change; DEL delete |


| Pass criteria                    |
| -------------------------------- |
| Calendar reflects change/removal |


---

## 18. Friends (prerequisite for collaborators)

### FR-01 — Search user

```http
GET {{baseUrl}}/api/friends/search?q=username
```

### FR-02 — Send request / accept

```http
POST {{baseUrl}}/api/friends/request
PATCH {{baseUrl}}/api/friends/{{requestId}}/respond
{ "action": "accept" }
```


| Pass criteria                 |
| ----------------------------- |
| Appears in `GET /api/friends` |


---

## 19. Cross-command and edge cases


| ID   | Scenario                                        | Expected                                                          |
| ---- | ----------------------------------------------- | ----------------------------------------------------------------- |
| X-01 | `cancel` during any pending                     | Redis cleared                                                     |
| X-02 | `thanks` during pending                         | Model 1 may block or general reply                                |
| X-03 | Two commands in one message                     | multiple_command style reply                                      |
| X-04 | Empty message                                   | too_short / prompt                                                |
| X-05 | Wrong session id                                | 404 from Node                                                     |
| X-06 | Expired JWT                                     | 401                                                               |
| X-07 | AI server down                                  | 500 from Node chat                                                |
| X-08 | Change timezone after tasks                     | Show/tasks date filters shift                                     |
| X-09 | Learning plan on schedule A, create second plan | Must pick schedule; used schedule cannot reuse on 2nd active goal |
| X-10 | `GET /health` degraded                          | AI or Mongo down flags in JSON                                    |


---

## 20. Automated regression (optional)

Run before sign-off to catch regressions automated tests cover:

```bash
# AI server
cd Eva_AI_Server
PYTHONPATH=. python3 -m pytest -q

# Node backend
cd Eva_Backend_Server
npm test
```

Key suites: `test_learning_create_handler.py`, `test_*_handler.py`, `settings-learning-schedule.test.js`, `learning.test.js`, `dashboard.test.js`, `tasks.test.js`.

---

## 21. Sign-off checklist


| Area                   | Tests  | PASS | FAIL | Notes |
| ---------------------- | ------ | ---- | ---- | ----- |
| Environment            | §1, §4 | ☐    | ☐    |       |
| Learning schedules API | §5     | ☐    | ☐    |       |
| Scheduling add         | §6     | ☐    | ☐    |       |
| Scheduling delete      | §7     | ☐    | ☐    |       |
| Scheduling update      | §8     | ☐    | ☐    |       |
| Scheduling show        | §9     | ☐    | ☐    |       |
| Behavioral             | §10    | ☐    | ☐    |       |
| Learning add + APIs    | §11–12 | ☐    | ☐    |       |
| Collaboration          | §13    | ☐    | ☐    |       |
| Tasks REST             | §14    | ☐    | ☐    |       |
| Dashboard              | §15    | ☐    | ☐    |       |
| Notifications          | §16    | ☐    | ☐    |       |
| Google Calendar        | §17    | ☐    | ☐    |       |
| Friends                | §18    | ☐    | ☐    |       |
| Edge cases             | §19    | ☐    | ☐    |       |
| Automated tests        | §20    | ☐    | ☐    |       |


**Tester name:** _______________  
**Date:** _______________  
**Build / commit:** _______________  
**Environment:** Local / Staging / Production  

---

## Appendix A — Quick message examples (copy-paste)

```text
# Add
add team meeting tomorrow 2pm for 45 minutes
add assignment with FRIEND_USERNAME on Friday 6pm

# Delete
delete team meeting tomorrow
delete physics

# Update
change team meeting priority to high
move team meeting to Wednesday at 10am

# Show
show my tasks tomorrow
show overdue tasks
show high priority tasks this week

# Behavioral
when am I most productive
what are my best hours on Tuesday
show my completion rate
give me my productivity report

# Learning
want to learn Python basics in 3 weeks starting Monday
1
I completed today's learning session
```

---

## Appendix B — Related files


| File                               | Use                                           |
| ---------------------------------- | --------------------------------------------- |
| `ALL_COMMANDS_TESTING_PLAYBOOK.md` | Older scheduling+behavioral playbook (subset) |
| `PROJECT_COMPLETION_REPORT.md`     | Implementation status                         |
| `EVA_Complete_Test_Cases.txt`      | Legacy case list                              |
| `add_command_flow.txt` etc.        | Per-command SYNC sections                     |


**This guide is the master manual test document** — prefer it over older playbooks when they disagree.

---

*End of EVA Manual Testing Guide*
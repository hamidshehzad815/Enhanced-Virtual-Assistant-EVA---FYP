# EVA Commands Testing Playbook (Scheduling + Behavioral)

## 1. Scope

This playbook covers end-to-end API testing for all currently completed command families:

1. `scheduling_add`
2. `scheduling_delete`
3. `scheduling_show`
4. `scheduling_update`
5. `behavioral`

It is designed for Postman/manual testing against the live integrated flow:

`Frontend/Postman -> Node.js (/api/chat/process) -> AI Server (/process) -> MongoDB/Redis`

## 2. APIs Under Test

Primary command endpoint:

1. `POST /api/chat/session`
2. `POST /api/chat/process`

Setup/verification endpoints:

1. `PATCH /api/settings` (quiet hours, notifications)
2. `GET /api/settings`
3. `GET /api/tasks`
4. `GET /api/analytics/productivity`
5. `GET /api/analytics/hours`
6. `GET /api/analytics/days`
7. `GET /api/analytics/completion-trend`

## 3. Preconditions

Services must be up:

1. Node backend running
2. AI server running
3. MongoDB connected
4. Redis connected
5. Duckling connected

Recommended environment setup:

1. Create one test user and log in via `POST /api/auth/login`
2. Save:
   - `accessToken`
   - `userId`
3. Create chat session via `POST /api/chat/session`, save `sessionId`
4. Set user timezone to the one you will validate (example: `Asia/Karachi`)
5. Clear old task noise for this user (or use fresh DB user)

Postman variables:

1. `baseUrl`
2. `accessToken`
3. `userId`
4. `sessionId`

Auth header:

1. `Authorization: Bearer {{accessToken}}`

## 4. Common Request Template

Use this body for chat processing tests:

```json
{
  "message": "YOUR_COMMAND_HERE",
  "session_id": "{{sessionId}}",
  "input_type": "text"
}
```

Expected top-level backend response shape:

```json
{
  "status": "success",
  "response_text": "...",
  "session_id": "...",
  "intent": "...",
  "ai_status": "...",
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

## 5. Redis and DB Verification Tips

Redis (pending context):

1. Key format: `context:{userId}`
2. Check pending flow:
   - `expected_response`
   - `pending_action.intent`
   - `pending_action.entities`

Mongo collections to verify:

1. `tasks`
2. `activity_logs`
3. `conversation_history`
4. `chat_sessions`
5. `notifications`
6. `user_settings`

## 6. Scheduling Add Tests

### ADD-01 Happy Path Add

Request message:

1. `add physics exam on monday 4pm for 1 hour`

Expected:

1. `intent` = `scheduling_add`
2. `ai_status` = `success`
3. Task inserted in `tasks` with:
   - `title = physics exam`
   - `duration = 60`
   - `status = pending`
4. `conversation_history` has user + eva messages
5. `chat_sessions.last_message_preview` updated

### ADD-02 Missing Entity Prompt (Date/Time)

Request message:

1. `add chemistry assignment`

Expected:

1. `ai_status` = `pending`
2. `data.route.pending.expected_response = free_text`
3. `data.route.pending.missing_entity` present
4. Redis context exists for this user

Follow-up:

1. Send date/time as next message, ensure handler continues and creates task

### ADD-03 Duplicate Detection Confirmation

Precondition:

1. A task with same title already scheduled on same day

Request message:

1. `add physics exam on monday 4pm`

Expected:

1. `ai_status` = `pending`
2. `expected_response = yes_no`
3. Response mentions existing scheduled date/time

Follow-up:

1. Send `yes` -> task gets inserted
2. Send `no` -> no new task inserted

### ADD-04 Quiet Hours Confirmation

Precondition:

1. Configure quiet hours in `PATCH /api/settings`:

```json
{
  "has_quiet_hours": true,
  "quiet_hours_enabled": true,
  "quiet_hours": [
    { "label": "sleep", "start": "22:00", "end": "07:00", "enabled": true },
    { "label": "uni", "start": "09:00", "end": "13:00", "enabled": true }
  ]
}
```

Request message:

1. `add quiz today 12:35pm`

Expected:

1. `ai_status` = `pending`
2. `pending.reason = quiet_hours`
3. `pending.quiet_hour_matches` lists matching block(s)
4. Redis context saved

Follow-up:

1. Send `yes` -> task inserted
2. Send `no` -> task not inserted

### ADD-05 Overlap Conflict Rejection

Precondition:

1. Task A exists: Monday 5:00 PM, duration 60

Request message:

1. `add task B on monday 5:30pm for 1 hour`

Expected:

1. Request is rejected (no new insert)
2. Response clearly says schedule conflict/overlap
3. Existing task remains unchanged

## 7. Scheduling Delete Tests

### DEL-01 Single Match -> Yes/No Confirmation

Request message:

1. `delete physics exam on monday`

Expected:

1. `ai_status` = `pending`
2. `expected_response = yes_no`
3. Redis pending contains selected `task_id`

Follow-up:

1. `yes` -> task soft deleted (`is_deleted = true`)
2. `no` -> unchanged

### DEL-02 Multi Match (2-5) -> Number or All

Request message:

1. `delete physics exam`

Expected:

1. `ai_status` = `pending`
2. Response lists numbered matches
3. `expected_response = number`

Follow-up:

1. Send `2` -> switches to yes/no confirm for selected task
2. Send `all` -> asks bulk delete confirmation

### DEL-03 Too Broad (>5)

Request message:

1. Broad delete with many matches

Expected:

1. `ai_status` indicates too broad
2. No deletion performed
3. User asked to narrow filters

### DEL-04 Cancel During Pending

When delete flow is pending:

1. Send `cancel`

Expected:

1. Redis context cleared
2. No deletion performed

## 8. Scheduling Show Tests

### SHOW-01 Show By Date

Request message:

1. `show tasks on monday`

Expected:

1. `intent = scheduling_show`
2. `ai_status = success` or `not_found`
3. If found: `data.route.tasks[]` returned
4. Display times formatted in user timezone

### SHOW-02 Show By Task Name + Date

Request message:

1. `show physics exam on monday`

Expected:

1. matching task(s) returned
2. response contains local date/time string

### SHOW-03 Approximate Task Name Match

Precondition:

1. Task exists: `physics exam`

Request message:

1. `show physics task on monday`

Expected:

1. If exact not found but related match exists, response should mention related matches
2. Returns matched tasks instead of hard fail

### SHOW-04 No Match

Request message:

1. `show impossible-task-name on monday`

Expected:

1. `ai_status = not_found`
2. Clear not-found response with filters

## 9. Scheduling Update Tests

### UPD-01 Identify -> Ask What To Update

Request message:

1. `update physics exam on monday`

Expected:

1. Handler identifies task
2. If no new fields, asks what to change
3. Pending context stage: `what_to_update`

### UPD-02 One Match + Change -> Yes/No Confirm

Request message:

1. `change physics exam priority to high`

Expected:

1. pending confirm
2. update summary shown
3. `expected_response = yes_no`

Follow-up:

1. `yes` -> DB update applied
2. `no` -> no update

### UPD-03 Multi Match -> Number Select

Request message:

1. `update physics exam priority to high` with 2+ matching tasks

Expected:

1. `expected_response = number`
2. selecting a number transitions to `yes_no` or `what_to_update` based on available new fields

### UPD-04 Overlap Block

Request message:

1. `move physics exam to monday 5:30pm` where overlap exists

Expected:

1. conflict detected
2. no update applied
3. user prompted for another change

### UPD-05 Status Backward Lock

Precondition:

1. Task status = `complete`

Request message:

1. `mark physics exam pending`

Expected:

1. blocked response
2. task remains `complete`

## 10. Behavioral Tests

### BEH-01 Threshold Not Met

Precondition:

1. completed logs below `analytics_min_tasks_threshold`

Request message:

1. `when am i most productive`

Expected:

1. not-enough-data response
2. no analytics deep query response payload

### BEH-02 Productive Hours (General)

Request message:

1. `when am i most productive`

Expected:

1. `sub_intent = productive_hours`
2. top hours insight response

### BEH-03 Productive Hours (Day Filter)

Request message:

1. `what are my best hours on monday`

Expected:

1. day-filtered analytics response

### BEH-04 Productive Days

Request message:

1. `which days am i most focused`

Expected:

1. `sub_intent = productive_days`
2. ranked day insights

### BEH-05 Best Time For Day (Day Missing -> Pending)

Request message:

1. `find the best time for me`

Expected:

1. pending free_text asking for weekday
2. Redis behavioral pending context created

Follow-up:

1. Send `Friday` -> context consumed, re-enters behavioral, returns best time
2. Send invalid day text -> ask again, keep context
3. Send `cancel` -> clear context

### BEH-06 Completion Rate

Request message:

1. `show my completion rate`

Expected:

1. `sub_intent = completion_rate`
2. includes totals, on-time rate, weekly trend

### BEH-07 Productivity Report

Request message:

1. `show my productivity report`

Expected:

1. `sub_intent = productivity_report`
2. combines hours + days + completion + avg_time_taken

### BEH-08 No Data For Filter

Request message:

1. `what are my best hours on sunday` where sunday has no logs

Expected:

1. no-data-for-filter response

## 11. Notification Verification Scenarios

For add/update/delete where notifications are expected:

1. Check `notifications.requested/inserted/dispatched_*` in API response
2. Validate `notifications` collection insert
3. Validate behavior for disabled channels:
   - `email_notifications_enabled = false`
   - `push_notifications_enabled = false`
4. If FCM token missing, expect push dispatch skipped log (not crash)

## 12. Timezone Validation Scenarios

Run same command with different user timezone values:

1. `UTC`
2. `Asia/Karachi`
3. `Asia/Kolkata`

Validate:

1. Stored task datetime remains consistent
2. User-facing response time is shown in user timezone
3. `GET /api/tasks?date=YYYY-MM-DD` uses local day boundaries correctly

## 13. Regression Suite Commands

AI server:

```bash
cd Eva_AI_Server
PYTHONPATH=. pytest -q
```

Node backend:

```bash
cd Eva_Backend_Server
npm test
```

## 14. Exit Criteria

Consider command stack validated when:

1. All scenarios in sections 6-10 pass
2. No server crash for invalid/edge input
3. Pending contexts behave correctly (set, consume, clear)
4. Notifications and logs are consistent with each operation
5. Full automated suites pass on both servers

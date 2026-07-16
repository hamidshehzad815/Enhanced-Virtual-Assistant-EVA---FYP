# Scheduling DELETE — Full Test Case Plan

End-to-end delete testing for the `scheduling_delete` command, covering every
branch and constraint in the handler + context manager.

Flow under test: `Postman/Frontend -> Node (/api/chat/process) -> AI Server (/process) -> Mongo/Redis`

Source of truth:
- Handler: `Eva_AI_Server/handlers/scheduling/delete.py`
- Context manager: `delete_context_manager.txt` (States 1–4)
- Flow: `delete_command_flow.txt`
- DB query: `find_tasks_for_delete` / `_build_delete_query` in `Eva_AI_Server/db/tasks.py`
- Fallback: `Eva_AI_Server/pipeline/delete_entity_fallback.py`

---

## 0. Constraint Reference (what to hold in your head while testing)

| # | Constraint | Where enforced |
|---|-----------|----------------|
| 1 | **Soft delete only** — sets `is_deleted=true`, `deleted_at`, `updated_at`. Never hard delete. | `soft_delete_task` |
| 2 | **Confirmation required** before any deletion. Nothing is deleted on the first turn. | handler yes_no gate |
| 3 | Match routing: **0→not found**, **1→yes/no**, **2–5→numbered list**, **6+→too broad (no Redis state)**. | Step 4 |
| 4 | **No entity** extracted → `free_text` prompt (State 1). Reply is treated as `task_name`, handler re-enters from Step 1. | Step 1 |
| 5 | Recognized delete entities: **task_name, date, priority, status, time**. Priority ∈ {low,medium,high}, status ∈ {pending,ongoing,complete}. | NER + `_build_delete_query` |
| 6 | Fallback **never invents task_name** (only date/priority/status). task_name must come from NER. | `delete_entity_fallback.py` (PR #54/#55) |
| 7 | task_name match = **case-insensitive substring** (regex-escaped) on `title`. Partial names match. | `_build_delete_query` |
| 8 | date → resolved via Duckling to ISO, then **local day bounds → UTC**. Unresolvable date → `free_text` + `missing_entity="date"`. | `_resolve_date_filter` |
| 9 | date **+** time → **±15 min window** around the due datetime. time **without** date → time is **ignored** in the query (but still shows in filters summary). | handler time block |
| 10 | Invalid time (date present but time unresolvable) → `free_text` + `missing_entity="time"`. | handler time block |
| 11 | Only **owner** can delete. Query is `owner_id`-based; no collaborator fallback (unlike show). | `find_tasks_for_delete` |
| 12 | Already soft-deleted tasks are excluded (`is_deleted != true`) → re-deleting → not found. | query |
| 13 | On confirmed delete: **activity_log** (`action_type=task_deleted`), **Google Calendar** delete if `event_id`+token, **collaborator notifications** for `accepted` collaborators. | Step 5 |
| 14 | **Cancel** is checked FIRST in every pending state. | context manager |
| 15 | New **command** while pending (yes_no/number) → Model 1 runs, Redis stays (TTL reset), EVA re-prompts. free_text state skips Model 1. | context manager |
| 16 | Redis TTL = **300s**, reset on every write. Expiry → next input starts fresh, no message. | context manager |
| 17 | Bulk delete (`all`) requires a **separate** yes/no confirmation (State 4). | context manager |
| 18 | Query sort = `due_datetime` asc, `limit 10`. | `find_tasks_for_delete` |

**Confirmation keywords** — YES: yes / yeah / yep / sure / go ahead / do it / confirm / ok · NO: no / nope / nah / don't / leave it / keep it
**Cancel keywords:** cancel / stop / abort / never mind / forget it / forget that / leave it / discard / no cancel
**"all" triggers:** all / all of them / delete all / every one / all tasks

---

## 1. Seed Data (create these BEFORE testing)

Set user timezone to **Asia/Karachi**. Create via `add` command or DB insert. All non-deleted, owned by the test user.

**Anchor date: today = Thursday, 2026-07-16.** All dates below are concrete so
you know exactly what to schedule. They are also chosen so the relative day-words
used in the test messages resolve to the right task (Duckling resolves a bare
weekday to its **next** occurrence from today): `monday → 2026-07-20`,
`tuesday → 2026-07-21`, `wednesday → 2026-07-22`, `today → 2026-07-16`.

| Ref | Title | Date (local) | Weekday | Time | priority | status | Notes |
|-----|-------|--------------|---------|------|----------|--------|-------|
| T1 | Physics exam | 2026-07-20 | Mon | 17:00 | high | pending | unique-ish name for single-match; "on monday at 5pm" |
| T2 | Physics lab | 2026-07-21 | Tue | 15:00 | medium | pending | shares "physics" substring |
| T3 | Physics quiz | 2026-07-22 | Wed | 14:00 | low | complete | shares "physics", completed |
| T4 | Chemistry paper | 2026-07-20 | Mon | 09:00 | high | pending | **same date as T1**, different time/priority mix |
| T5 | Team standup | 2026-07-16 | Thu (today) | 10:00 | low | ongoing | for `today` / status tests |
| T6 | Study block | 2026-07-17 | Fri | 08:00 | medium | pending | part of the 6-same-name set |
| T7 | Study block | 2026-07-17 | Fri | 10:00 | medium | pending | part of the 6-same-name set |
| T8 | Study block | 2026-07-17 | Fri | 12:00 | medium | pending | part of the 6-same-name set |
| T9 | Study block | 2026-07-17 | Fri | 14:00 | medium | pending | part of the 6-same-name set |
| T10 | Study block | 2026-07-17 | Fri | 16:00 | medium | pending | part of the 6-same-name set |
| T11 | Study block | 2026-07-17 | Fri | 18:00 | medium | pending | **6 tasks, same name/day** → too-broad (>5) |
| T12 | Shared review | 2026-07-23 | Thu (next) | 16:00 | medium | pending | has ≥1 **accepted collaborator** |
| T13 | Synced meeting | 2026-07-23 | Thu (next) | 11:00 | high | pending | has `google_calendar_event_id` |

High-priority set (for `delete high priority tasks`): **T1, T4, T13**.
"physics" substring set: **T1, T2, T3**. "study block" set: **T6–T11**.

> Tip: keep a `GET /api/tasks` snapshot before and after each destructive case to confirm soft-delete counts.

---

## 2. Entity Extraction & Initial Resolution

### DEL-E01 — No entity → free_text (State 1)
- Msg: `delete a task`
- Expect: `status=pending`, `expected_response=free_text`, Redis `pending_action.intent=delete`, `entities={}`, `task_ids=[]`.
- No `missing_entity` key set.

### DEL-E02 — Fallback must NOT invent task_name (PR #54/#55 regression)
- Msg: `remove something` / `delete it`
- Expect: goes to **free_text** (State 1), NOT a fake name search. Redis `entities` has no `task_name`.

### DEL-E03 — task_name only (partial, case-insensitive)
- Msg: `delete PHYSICS`
- Expect: substring match → T1,T2,T3 (3 matches) → numbered list (State 3). Confirms case-insensitive + partial matching (constraint 7).

### DEL-E04 — Unique task_name → single match
- Msg: `delete chemistry paper`
- Expect: 1 match (T4) → `expected_response=yes_no`.

### DEL-E05 — date only
- Msg: `delete my tasks today`
- Expect: matches T5 (and any other due today). Verify day-bounds are Karachi local, not UTC (a task at 00:30 local should be included).

### DEL-E06 — priority only (via fallback)
- Msg: `delete high priority tasks`
- Expect: matches T1, T4, T13 (all high) → routing by count. Priority filter exact-match.

### DEL-E07 — status only
- Msg: `delete completed tasks`
- Expect: matches T3 (status=complete). Confirms status canonicalization (completed→complete).

### DEL-E08 — task_name + date combo
- Msg: `delete physics exam on monday`
- Expect: task_name "physics" AND Monday range → narrows to T1 → single match yes/no.

### DEL-E09 — date + time → ±15 min window
- Msg: `delete the task on monday at 5pm`
- Expect: window 16:45–17:15 local → T1 only. A task at 17:30 must NOT match.

### DEL-E10 — time WITHOUT date is ignored in query
- Msg: `delete the task at 5pm`
- Expect: time appears in filters summary but does NOT filter results (no date). If no other entity present, this is task_name-less + time-only → still counts as an entity (won't hit State 1), query runs with no effective narrowing → likely too broad / broad match. Document actual count.

### DEL-E11 — Invalid / unresolvable date
- Msg: `delete physics exam on blurday`
- Expect: `status=pending`, `expected_response=free_text`, Redis `missing_entity="date"`, `entities` retains task_name but date dropped. Re-prompt asks for the date specifically.

### DEL-E12 — Invalid time (valid date)
- Msg: `delete physics exam on monday at 99pm`
- Expect: `expected_response=free_text`, `missing_entity="time"`, time dropped from pending entities.

---

## 3. Match-Count Routing (Step 4)

### DEL-M01 — 0 matches → not found
- Msg: `delete biology homework`
- Expect: `status=not_found`, `match_count=0`, NO Redis pending state. EVA natural "couldn't find" reply.

### DEL-M02 — 1 match → yes/no (State 2)
- Msg: `delete chemistry paper`
- Expect: `status=pending`, `expected_response=yes_no`, Redis `task_ids=[T4]`, `bulk=false`, single-confirm reply names task + due + priority.

### DEL-M03 — 2 matches → numbered list
- Pre: ensure exactly 2 "physics" pending (e.g. T1,T2 by adding date filter that excludes T3).
- Msg: `delete physics on monday and tuesday` (or narrow so 2 remain)
- Expect: `expected_response=number`, 2 numbered lines + "Reply with a number, or say 'all'".

### DEL-M04 — 5 matches → numbered list (upper bound)
- Pre: 5 matching tasks.
- Expect: numbered list of 5, `expected_response=number`.

### DEL-M05 — 6+ matches → too broad, NO Redis
- Msg: `delete study block` (matches T6–T11 = 6)
- Expect: `status=too_broad`, `match_count>=6`, **no Redis pending state written**, EVA asks to narrow. Verify Redis key absent.

---

## 4. Single-Match Confirmation — State 2 (yes/no)

Precede each with DEL-M02 (`delete chemistry paper`) to arm State 2.

### DEL-S01 — yes → soft delete
- Reply: `yes`
- Expect: `status=success`, Redis cleared, T4 now `is_deleted=true` + `deleted_at` set. Success reply names the task.

### DEL-S02 — no → no deletion
- Reply: `no`
- Expect: `status=cancelled`, Redis cleared, T4 unchanged (`is_deleted` still false). "left it as it is" reply.

### DEL-S03 — synonym yes (`go ahead` / `do it` / `sure` / `confirm`)
- Reply: `go ahead`
- Expect: same as DEL-S01. Test 2–3 synonyms.

### DEL-S04 — synonym no (`nope` / `nah` / `keep it`)
- Reply: `nope`
- Expect: same as DEL-S02.

### DEL-S05 — unrecognized reply
- Reply: `maybe` / `hmm`
- Expect: Redis stays (TTL reset), EVA "just a yes or no" re-prompt, no deletion.

### DEL-S06 — new command while pending
- Reply: `add gym at 6pm` (Model 1 → command)
- Expect: Redis stays (TTL reset), EVA "still waiting for your reply… say cancel". Original task NOT deleted, gym NOT added.

### DEL-S07 — cancel during confirm
- Reply: `cancel`
- Expect: Redis cleared, no deletion, "nothing was deleted" reply.

---

## 5. Multi-Match Selection — State 3 (number)

Precede each with DEL-E03 (`delete physics`) → list of T1,T2,T3.

### DEL-N01 — valid number → yes/no (→ State 2)
- Reply: `2`
- Expect: Redis updates to `expected_response=yes_no`, `task_ids=[<2nd task>]`, `bulk=false`. EVA confirms that one task. (No deletion yet.)

### DEL-N02 — then confirm
- Reply (after N01): `yes`
- Expect: only the selected task soft-deleted; others untouched.

### DEL-N03 — "all" → bulk confirm (→ State 4)
- Reply: `all`
- Expect: Redis `expected_response=yes_no`, `bulk=true`, `task_ids` unchanged (all 3). EVA "confirm — delete all 3…". Nothing deleted yet.

### DEL-N04 — number out of range
- Reply: `9`
- Expect: Redis stays, EVA "pick between 1 and N, or say 'all'". No change.

### DEL-N05 — non-number junk
- Reply: `banana`
- Expect: Redis stays, EVA "pick a number… or 'all'". No change.

### DEL-N06 — new command while numbering
- Reply: `show my tasks`
- Expect: Redis stays (TTL reset), "still waiting for your choice" re-prompt.

### DEL-N07 — cancel while numbering
- Reply: `never mind`
- Expect: Redis cleared, no deletion.

---

## 6. Bulk Confirmation — State 4 (yes/no on "all")

Precede with DEL-E03 → `all` (State 4 armed).

### DEL-B01 — yes → bulk soft delete
- Reply: `yes`
- Expect: `status=success`, `deleted.bulk=true`, `deleted.count=3`, ALL of T1,T2,T3 `is_deleted=true`. Bulk success reply. One activity_log per task.

### DEL-B02 — no → nothing deleted
- Reply: `no`
- Expect: `status=cancelled`, Redis cleared, all 3 untouched. "left all those tasks as they are".

### DEL-B03 — cancel at bulk
- Reply: `stop`
- Expect: Redis cleared, nothing deleted.

### DEL-B04 — unrecognized at bulk
- Reply: `ok maybe later` (not a clean yes/no)
- Expect: Redis stays, "just a yes or no" re-prompt.

---

## 7. Free-Text Resume — State 1

### DEL-F01 — reply becomes task_name → re-enter Step 1
- Setup: DEL-E01 (`delete a task`) → free_text.
- Reply: `chemistry paper`
- Expect: treated as `task_name`, Redis cleared, handler re-runs → 1 match → `expected_response=yes_no`. (Model 1 skipped for this reply.)

### DEL-F02 — free_text reply that matches nothing
- Setup: DEL-E01.
- Reply: `nonexistent task`
- Expect: re-enters → 0 matches → `not_found`.

### DEL-F03 — date re-prompt resume (missing_entity=date)
- Setup: DEL-E11 (invalid date) → free_text + `missing_entity=date`.
- Reply: `monday`
- Expect: reply mapped to **date** (not task_name, because `missing_entity=date`), merged with retained task_name, handler re-runs.

### DEL-F04 — cancel from free_text
- Setup: DEL-E01.
- Reply: `forget it`
- Expect: Redis cleared, nothing pending.

---

## 8. Side Effects (verify on confirmed delete)

### DEL-X01 — soft delete fields
- After any successful delete: task doc has `is_deleted=true`, `deleted_at` (recent), `updated_at` bumped. Doc NOT removed from collection.

### DEL-X02 — activity_logs entry
- Verify `activity_logs` insert: `action_type=task_deleted`, `subject=<title>`, `task_priority`, `source=scheduling_module`, plus `day_of_week`/`hour_of_day`/`week_number` when due_datetime present.

### DEL-X03 — Google Calendar delete
- Delete T13 (has `google_calendar_event_id`) with Google integration connected.
- Expect: `delete_event` called; on API failure it logs but does NOT block the delete (task still soft-deleted, `status=success`).

### DEL-X04 — collaborator notifications
- Delete T12 (accepted collaborator).
- Expect: response `notifications[]` contains one payload per accepted collaborator: `type=task_deleted`, `reference_type=task`, `action_required=false`, `delivery_channel=[push,in_app]`. Owner is excluded; duplicates deduped. Node dispatches them.

### DEL-X05 — no collaborators → empty notifications
- Delete T1 (no collaborators). `notifications=[]`.

---

## 9. Cross-Cutting / Edge Constraints

### DEL-C01 — re-delete already-deleted task → not found
- Delete T4 (DEL-S01), then `delete chemistry paper` again.
- Expect: `not_found` (excluded by `is_deleted != true`).

### DEL-C02 — TTL expiry
- Arm State 2, wait > 300s, then reply `yes`.
- Expect: Redis expired → treated as a fresh command (Model 1 classifies "yes" as general/out_of_scope). No deletion.

### DEL-C03 — owner-only (collaborator cannot delete)
- As a user who is an **accepted collaborator** (not owner) on a task, `delete <that task>`.
- Expect: `not_found` — delete queries by `owner_id` only (constraint 11). Contrast with `show`, which has a collaborator fallback.

### DEL-C04 — priority value guarding
- Msg: `delete urgent priority tasks` (urgent is not low/medium/high canonical → check normalizer maps it or drops it).
- Expect: document whether "urgent" canonicalizes to high or is ignored. Query only accepts low/medium/high.

### DEL-C05 — status "completed" vs "complete"
- Msg: `delete completed tasks` and `delete complete tasks`.
- Expect: both canonicalize to `complete` and match T3.

### DEL-C06 — limit 10 / sort order
- With >10 matches, confirm only 10 fetched and sorted by due_datetime asc (mostly relevant to the too-broad branch which triggers at 6 anyway; verify ordering in the 2–5 list).

### DEL-C07 — regex-escape safety
- Task titled `C++ review (final)` → `delete C++ review (final)`.
- Expect: special chars are regex-escaped, exact substring still matches (no regex error / no over-match).

### DEL-C08 — "leave it" ambiguity (cancel vs no)
- In State 2, reply `leave it`.
- Expect: either cancel or no path — both clear Redis and delete nothing. Confirm no deletion.

---

## 10. Quick Regression Sequence (smoke)

Run in order against a fresh seeded user:

1. `delete physics` → numbered list (State 3)
2. `all` → bulk confirm (State 4)
3. `no` → cancelled, nothing deleted
4. `delete chemistry paper` → yes/no (State 2)
5. `yes` → success, T4 soft-deleted
6. `delete chemistry paper` → not_found (already deleted)
7. `delete study block` → too_broad (6+)
8. `delete a task` → free_text; reply `physics lab` → yes/no; `cancel` → cleared

Pass criteria: each transition matches `expected_response`, Redis state matches the table, and only confirmed deletes flip `is_deleted`.

---

## 11. Per-Case Verification Checklist

For every case capture:
- [ ] `status` / `ai_status` in response
- [ ] `expected_response` (free_text / yes_no / number) when pending
- [ ] Redis `context:{userId}` — `pending_action.intent`, `task_ids`, `bulk`, `entities`, `missing_entity`
- [ ] `tasks` collection — `is_deleted`, `deleted_at` on the right doc(s) only
- [ ] `activity_logs` — one `task_deleted` per deleted task
- [ ] `notifications` array — collaborators only, correct shape
- [ ] EVA reply is natural + names the task (no robotic "invalid input")

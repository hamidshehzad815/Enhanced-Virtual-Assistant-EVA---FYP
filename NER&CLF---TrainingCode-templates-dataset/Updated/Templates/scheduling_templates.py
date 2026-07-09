"""
Scheduling NER Templates
========================
Phase 3: added word-order variants, casual triggers, person-distinction
patterns, and negative guard task names (see scheduling_slots.py).

Pure template definitions — no slot values, no generation logic.
Import this file from DataGenerationCode scripts.

Format: (template_string, [entity_labels_in_order])
Slot notation:
  {task_name}    → task name
  {date}         → date expression
  {time}         → time expression
  {priority}     → low / medium / high
  {person}       → collaborator name
  {duration}     → duration expression
  {status}       → pending / ongoing / complete
  {day}          → specific weekday
  {new_taskname} → new task name (update)
  {new_date}     → new date (update)
  {new_time}     → new time (update)
  {new_priority} → new priority (update)
  {new_status}   → new status (update)
  {new_duration} → new duration (update)

NOTE: Templates with empty entity list [] are used for CLF2 only.
NER generation scripts should skip them: [t for t in TEMPLATES if t[1]]
"""

# ================================================================
# ADD TEMPLATES
# ================================================================

ADD_TEMPLATES = [

    # ── COMBINATION 1 — task only ────────────────────────────────
    ("add {task_name}", ["task_name"]),
    ("add task {task_name}", ["task_name"]),
    ("schedule {task_name}", ["task_name"]),
    ("create {task_name}", ["task_name"]),
    ("set {task_name}", ["task_name"]),
    ("add a task called {task_name}", ["task_name"]),
    ("add a new task for {task_name}", ["task_name"]),
    ("create a task named {task_name}", ["task_name"]),
    ("schedule a task called {task_name}", ["task_name"]),
    ("can you add {task_name}", ["task_name"]),
    ("I need to add {task_name}", ["task_name"]),
    ("please add {task_name}", ["task_name"]),
    ("I want to create {task_name}", ["task_name"]),
    ("set up {task_name} for me", ["task_name"]),
    ("I have to do {task_name}", ["task_name"]),
    ("could u please add {task_name}", ["task_name"]),
    ("pls add {task_name}", ["task_name"]),
    ("yo add {task_name}", ["task_name"]),
    ("hey can u add {task_name}", ["task_name"]),
    ("{task_name}", ["task_name"]),

    # ── COMBINATION 2 — task + date ──────────────────────────────
    ("add {task_name} {date}", ["task_name", "date"]),
    ("schedule {task_name} {date}", ["task_name", "date"]),
    ("add {task_name} on {date}", ["task_name", "date"]),
    ("add {task_name} for {date}", ["task_name", "date"]),
    ("add {task_name} by {date}", ["task_name", "date"]),
    ("schedule {task_name} on {date}", ["task_name", "date"]),
    ("create {task_name} for {date}", ["task_name", "date"]),
    ("set {task_name} on {date}", ["task_name", "date"]),
    ("add {task_name} this {date}", ["task_name", "date"]),
    ("add {task_name} next {date}", ["task_name", "date"]),
    ("on {date} add {task_name}", ["task_name", "date"]),
    ("add {task_name} and set it for {date}", ["task_name", "date"]),
    ("can you schedule {task_name} on {date}", ["task_name", "date"]),
    ("I want to add {task_name} on {date}", ["task_name", "date"]),
    ("please schedule {task_name} for {date}", ["task_name", "date"]),
    ("I have {task_name} on {date}", ["task_name", "date"]),
    ("remind me about {task_name} on {date}", ["task_name", "date"]),
    ("create a task for {task_name} on {date}", ["task_name", "date"]),
    ("{task_name} is on {date}", ["task_name", "date"]),
    ("{task_name} {date}", ["task_name", "date"]),
    ("{date} {task_name}", ["task_name", "date"]),
    ("pls schedule {task_name} {date}", ["task_name", "date"]),

    # ── COMBINATION 3 — task + time ──────────────────────────────
    ("add {task_name} {time}", ["task_name", "time"]),
    ("schedule {task_name} {time}", ["task_name", "time"]),
    ("add {task_name} at {time}", ["task_name", "time"]),
    ("add {task_name} for {time}", ["task_name", "time"]),
    ("add {task_name} by {time}", ["task_name", "time"]),
    ("add {task_name} around {time}", ["task_name", "time"]),
    ("schedule {task_name} at {time}", ["task_name", "time"]),
    ("create {task_name} at {time}", ["task_name", "time"]),
    ("set {task_name} for {time}", ["task_name", "time"]),
    ("add {task_name} at around {time}", ["task_name", "time"]),
    ("at {time} add {task_name}", ["task_name", "time"]),
    ("add {task_name} and set time to {time}", ["task_name", "time"]),
    ("can you add {task_name} at {time}", ["task_name", "time"]),
    ("I want {task_name} scheduled at {time}", ["task_name", "time"]),
    ("I have {task_name} at {time}", ["task_name", "time"]),
    ("put {task_name} at {time}", ["task_name", "time"]),
    ("{task_name} at {time}", ["task_name", "time"]),
    ("{time} {task_name}", ["task_name", "time"]),

    # ── COMBINATION 4 — task + priority ──────────────────────────
    ("add {task_name} {priority} priority", ["task_name", "priority"]),
    ("schedule {task_name} with {priority} priority", ["task_name", "priority"]),
    ("add {task_name} priority {priority}", ["task_name", "priority"]),
    ("create {task_name} mark it {priority}", ["task_name", "priority"]),
    ("add {task_name} it is {priority}", ["task_name", "priority"]),
    ("add {task_name} set priority to {priority}", ["task_name", "priority"]),

    # ── COMBINATION 5 — task + date + time ───────────────────────
    ("add {task_name} on {date} at {time}", ["task_name", "date", "time"]),
    ("schedule {task_name} on {date} at {time}", ["task_name", "date", "time"]),
    ("create {task_name} for {date} at {time}", ["task_name", "date", "time"]),
    ("add {task_name} {date} {time}", ["task_name", "date", "time"]),
    ("I have {task_name} on {date} at {time}", ["task_name", "date", "time"]),
    ("remind me about {task_name} on {date} at {time}", ["task_name", "date", "time"]),
    ("put {task_name} on {date} at {time}", ["task_name", "date", "time"]),
    ("on {date} at {time} add {task_name}", ["task_name", "date", "time"]),
    ("{date} {time} {task_name}", ["task_name", "date", "time"]),
    ("{task_name} {date} {time}", ["task_name", "date", "time"]),
    ("please add {task_name} on {date} {time}", ["task_name", "date", "time"]),
    ("can u schedule {task_name} {date} {time}", ["task_name", "date", "time"]),
    ("at {time} on {date} add {task_name}", ["task_name", "date", "time"]),

    # ── COMBINATION 6 — task + date + time + priority ────────────
    ("add {task_name} on {date} at {time} with {priority} priority", ["task_name", "date", "time", "priority"]),
    ("schedule {task_name} on {date} at {time} priority {priority}", ["task_name", "date", "time", "priority"]),
    ("create {task_name} for {date} {time} mark as {priority}", ["task_name", "date", "time", "priority"]),
    ("add {task_name} {date} {time} {priority}", ["task_name", "date", "time", "priority"]),

    # ── COMBINATION 7 — task + date + time + duration ────────────
    ("add {task_name} on {date} at {time} for {duration}", ["task_name", "date", "time", "duration"]),
    ("schedule {task_name} {date} {time} duration {duration}", ["task_name", "date", "time", "duration"]),
    ("add {task_name} on {date} at {time} it will take {duration}", ["task_name", "date", "time", "duration"]),

    # ── COMBINATION 8 — task + date + time + person ──────────────
    ("add {task_name} on {date} at {time} with {person}", ["task_name", "date", "time", "person"]),
    ("schedule {task_name} with {person} on {date} at {time}", ["task_name", "date", "time", "person"]),
    ("add {task_name} on {date} {time} collaborating with {person}", ["task_name", "date", "time", "person"]),
    ("create {task_name} with {person} for {date} {time}", ["task_name", "date", "time", "person"]),
    ("with {person} add {task_name} on {date} at {time}", ["task_name", "date", "time", "person"]),

    # ── COMBINATION 9 — task + duration ──────────────────────────
    ("add {task_name} for {duration}", ["task_name", "duration"]),
    ("schedule {task_name} duration {duration}", ["task_name", "duration"]),
    ("add {task_name} it will take {duration}", ["task_name", "duration"]),
    ("create {task_name} block {duration}", ["task_name", "duration"]),

    # ── COMBINATION 10 — task + person ───────────────────────────
    ("add {task_name} with {person}", ["task_name", "person"]),
    ("schedule {task_name} with {person}", ["task_name", "person"]),
    ("add {task_name} collaborator {person}", ["task_name", "person"]),
    ("create {task_name} invite {person}", ["task_name", "person"]),
    ("add {task_name} and include {person}", ["task_name", "person"]),

    # ── COMBINATION 11 — task + date + priority ───────────────────
    ("add {task_name} on {date} priority {priority}", ["task_name", "date", "priority"]),
    ("schedule {task_name} for {date} mark as {priority}", ["task_name", "date", "priority"]),
    ("add {task_name} {date} {priority} priority", ["task_name", "date", "priority"]),

    # ── COMBINATION 12 — task + date + person ────────────────────
    ("add {task_name} on {date} with {person}", ["task_name", "date", "person"]),
    ("schedule {task_name} with {person} on {date}", ["task_name", "date", "person"]),
    ("create {task_name} for {date} include {person}", ["task_name", "date", "person"]),

    # ── COMBINATION 13 — full: task + date + time + priority + person ──
    ("add {task_name} on {date} at {time} with {person} priority {priority}", ["task_name", "date", "time", "person", "priority"]),
    ("schedule {task_name} with {person} on {date} {time} mark {priority}", ["task_name", "date", "time", "person", "priority"]),

    # ── EXTRA WORD-ORDER VARIANTS (Phase 3) ──────────────────────────
    # task-first bare (no trigger word) — forces model off position 0 = task_name
    ("{task_name} {date} {time}", ["task_name", "date", "time"]),
    ("{task_name} on {date}", ["task_name", "date"]),
    ("{task_name} at {time}", ["task_name", "time"]),
    ("{task_name} {date}", ["task_name", "date"]),
    ("{task_name} {time}", ["task_name", "time"]),
    # date-first
    ("{date} {task_name}", ["task_name", "date"]),
    ("{date} {time} {task_name}", ["task_name", "date", "time"]),
    ("on {date} at {time} {task_name}", ["task_name", "date", "time"]),
    ("on {date} {task_name} at {time}", ["task_name", "date", "time"]),
    # time-first
    ("{time} {task_name}", ["task_name", "time"]),
    ("at {time} {task_name} on {date}", ["task_name", "date", "time"]),
    # mid-sentence placement
    ("I have {task_name} on {date} please add it", ["task_name", "date"]),
    ("I have {task_name} at {time} add it", ["task_name", "time"]),
    ("there is {task_name} on {date} at {time} add that", ["task_name", "date", "time"]),
    ("don't forget {task_name} on {date}", ["task_name", "date"]),
    ("don't forget {task_name} {date} {time}", ["task_name", "date", "time"]),
    ("need to do {task_name} on {date}", ["task_name", "date"]),
    ("got {task_name} {date} add it pls", ["task_name", "date"]),
    ("got {task_name} at {time} {date}", ["task_name", "date", "time"]),
    # casual triggers
    ("sched {task_name} {date}", ["task_name", "date"]),
    ("sched {task_name} {date} {time}", ["task_name", "date", "time"]),
    ("sched {task_name} at {time}", ["task_name", "time"]),
    ("hey sched {task_name} {date}", ["task_name", "date"]),
    ("add pls {task_name} {date}", ["task_name", "date"]),
    ("pls sched {task_name} {date} {time}", ["task_name", "date", "time"]),
    ("yo sched {task_name} {date}", ["task_name", "date"]),
    ("can u sched {task_name} for {date}", ["task_name", "date"]),
    ("bro add {task_name} {date}", ["task_name", "date"]),
    ("quick add {task_name} {date} {time}", ["task_name", "date", "time"]),

    # ── PERSON DISTINCTION PATTERNS (Phase 3) ────────────────────────
    # person always follows "with"/"alongside"/"and add" — teaches model
    # that task_name appearing WITHOUT that context is never person
    ("add {task_name} with {person} on {date} at {time}", ["task_name", "date", "time", "person"]),
    ("{task_name} with {person} on {date}", ["task_name", "date", "person"]),
    ("schedule {task_name} for {date} and add {person}", ["task_name", "date", "person"]),
    ("I have {task_name} with {person} on {date} at {time}", ["task_name", "date", "time", "person"]),
    ("add {task_name} on {date} invite {person}", ["task_name", "date", "person"]),
    ("add {task_name} collaborator is {person}", ["task_name", "person"]),
    ("add {task_name} add {person} as collaborator", ["task_name", "person"]),
    ("{task_name} on {date} include {person}", ["task_name", "date", "person"]),
    ("sched {task_name} with {person} {date}", ["task_name", "date", "person"]),
]

# ================================================================
# DELETE TEMPLATES
# ================================================================

DELETE_TEMPLATES = [

    # ── COMBINATION 1 — task only ────────────────────────────────
    ("delete {task_name}", ["task_name"]),
    ("remove {task_name}", ["task_name"]),
    ("cancel {task_name}", ["task_name"]),
    ("get rid of {task_name}", ["task_name"]),
    ("erase {task_name}", ["task_name"]),
    ("drop {task_name}", ["task_name"]),
    ("delete my {task_name}", ["task_name"]),
    ("remove my {task_name}", ["task_name"]),
    ("cancel my {task_name}", ["task_name"]),
    ("please delete {task_name}", ["task_name"]),
    ("I want to delete {task_name}", ["task_name"]),
    ("I need to remove {task_name}", ["task_name"]),
    ("can you delete {task_name}", ["task_name"]),
    ("get rid of my {task_name}", ["task_name"]),
    ("take off {task_name}", ["task_name"]),
    ("I don't need {task_name} anymore", ["task_name"]),
    ("scratch {task_name}", ["task_name"]),
    ("pls remove {task_name}", ["task_name"]),

    # ── COMBINATION 2 — task + date ──────────────────────────────
    ("delete {task_name} on {date}", ["task_name", "date"]),
    ("remove {task_name} on {date}", ["task_name", "date"]),
    ("cancel {task_name} on {date}", ["task_name", "date"]),
    ("delete {task_name} for {date}", ["task_name", "date"]),
    ("remove {task_name} scheduled for {date}", ["task_name", "date"]),
    ("on {date} delete {task_name}", ["task_name", "date"]),
    ("{task_name} on {date} delete it", ["task_name", "date"]),
    ("{date} {task_name} remove", ["task_name", "date"]),

    # ── COMBINATION 3 — task + priority ──────────────────────────
    ("delete {task_name} the {priority} priority one", ["task_name", "priority"]),
    ("remove my {priority} {task_name}", ["task_name", "priority"]),
    ("cancel the {priority} {task_name}", ["task_name", "priority"]),

    # ── COMBINATION 4 — task + status ────────────────────────────
    ("delete {task_name} the {status} one", ["task_name", "status"]),
    ("remove my {status} {task_name}", ["task_name", "status"]),
    ("delete {task_name} that is {status}", ["task_name", "status"]),

    # ── COMBINATION 5 — task + date + priority ────────────────────
    ("delete {task_name} on {date} the {priority} one", ["task_name", "date", "priority"]),
    ("remove {priority} {task_name} on {date}", ["task_name", "date", "priority"]),

    # ── EXTRA WORD-ORDER VARIANTS (Phase 3) ──────────────────────────
    # date-first
    ("on {date} delete {task_name}", ["task_name", "date"]),
    ("on {date} remove {task_name}", ["task_name", "date"]),
    ("{date} {task_name} remove it", ["task_name", "date"]),
    ("{date} {task_name} delete", ["task_name", "date"]),
    # task-first bare
    ("{task_name} delete", ["task_name"]),
    ("{task_name} remove it", ["task_name"]),
    ("{task_name} cancel it", ["task_name"]),
    # mid-sentence
    ("I no longer need {task_name} on {date} remove it", ["task_name", "date"]),
    ("I want to cancel {task_name} the one on {date}", ["task_name", "date"]),
    ("the {task_name} on {date} delete that", ["task_name", "date"]),
    ("for {date} remove {task_name}", ["task_name", "date"]),
    # status/priority bulk with order variants
    ("all {status} tasks delete them", ["status"]),
    ("remove all tasks that are {status}", ["status"]),
    ("{priority} tasks remove", ["priority"]),
    ("all {priority} tasks on {date} delete", ["priority", "date"]),
    ("{date} all {status} tasks remove", ["status", "date"]),
    # casual
    ("pls delete {task_name}", ["task_name"]),
    ("pls remove {task_name} on {date}", ["task_name", "date"]),
    ("can u delete {task_name} for {date}", ["task_name", "date"]),
    ("yo remove {task_name}", ["task_name"]),
    ("delete {task_name} asap", ["task_name"]),
]

# ================================================================
# UPDATE TEMPLATES
# ================================================================

UPDATE_TEMPLATES = [

    # ── COMBINATION 1 — task + new_priority ──────────────────────
    ("change {task_name} priority to {new_priority}", ["task_name", "new_priority"]),
    ("update {task_name} priority to {new_priority}", ["task_name", "new_priority"]),
    ("set {task_name} priority to {new_priority}", ["task_name", "new_priority"]),
    ("make {task_name} {new_priority} priority", ["task_name", "new_priority"]),
    ("mark {task_name} as {new_priority}", ["task_name", "new_priority"]),
    ("{task_name} priority {new_priority}", ["task_name", "new_priority"]),

    # ── COMBINATION 2 — task + new_status ────────────────────────
    ("mark {task_name} as {new_status}", ["task_name", "new_status"]),
    ("update {task_name} to {new_status}", ["task_name", "new_status"]),
    ("set {task_name} status to {new_status}", ["task_name", "new_status"]),
    ("change {task_name} to {new_status}", ["task_name", "new_status"]),
    ("{task_name} is now {new_status}", ["task_name", "new_status"]),
    ("I finished {task_name} mark it {new_status}", ["task_name", "new_status"]),
    ("done with {task_name} mark {new_status}", ["task_name", "new_status"]),

    # ── COMBINATION 3 — task + new_time ──────────────────────────
    ("reschedule {task_name} to {new_time}", ["task_name", "new_time"]),
    ("change {task_name} time to {new_time}", ["task_name", "new_time"]),
    ("update {task_name} time {new_time}", ["task_name", "new_time"]),
    ("move {task_name} to {new_time}", ["task_name", "new_time"]),
    ("shift {task_name} to {new_time}", ["task_name", "new_time"]),
    ("{task_name} change time to {new_time}", ["task_name", "new_time"]),

    # ── COMBINATION 4 — task + new_date ──────────────────────────
    ("reschedule {task_name} to {new_date}", ["task_name", "new_date"]),
    ("move {task_name} to {new_date}", ["task_name", "new_date"]),
    ("change {task_name} date to {new_date}", ["task_name", "new_date"]),
    ("update {task_name} to {new_date}", ["task_name", "new_date"]),
    ("postpone {task_name} to {new_date}", ["task_name", "new_date"]),
    ("{task_name} move to {new_date}", ["task_name", "new_date"]),

    # ── COMBINATION 5 — task + date + new_date ───────────────────
    ("move {task_name} on {date} to {new_date}", ["task_name", "date", "new_date"]),
    ("reschedule {task_name} from {date} to {new_date}", ["task_name", "date", "new_date"]),
    ("change {task_name} on {date} to {new_date}", ["task_name", "date", "new_date"]),
    ("{task_name} on {date} move it to {new_date}", ["task_name", "date", "new_date"]),

    # ── COMBINATION 6 — task + date + new_time ───────────────────
    ("move {task_name} on {date} to {new_time}", ["task_name", "date", "new_time"]),
    ("change {task_name} on {date} time to {new_time}", ["task_name", "date", "new_time"]),
    ("{task_name} on {date} reschedule to {new_time}", ["task_name", "date", "new_time"]),

    # ── COMBINATION 7 — task + date + new_date + new_time ────────
    ("move {task_name} on {date} to {new_date} at {new_time}", ["task_name", "date", "new_date", "new_time"]),
    ("reschedule {task_name} from {date} to {new_date} {new_time}", ["task_name", "date", "new_date", "new_time"]),

    # ── COMBINATION 8 — task + new_taskname ──────────────────────
    ("rename {task_name} to {new_taskname}", ["task_name", "new_taskname"]),
    ("change the name of {task_name} to {new_taskname}", ["task_name", "new_taskname"]),
    ("update {task_name} title to {new_taskname}", ["task_name", "new_taskname"]),
    ("{task_name} rename to {new_taskname}", ["task_name", "new_taskname"]),

    # ── COMBINATION 9 — task + date + new_taskname ───────────────
    ("rename {task_name} on {date} to {new_taskname}", ["task_name", "date", "new_taskname"]),
    ("change name of {task_name} on {date} to {new_taskname}", ["task_name", "date", "new_taskname"]),

    # ── COMBINATION 10 — task + new_duration ─────────────────────
    ("change {task_name} duration to {new_duration}", ["task_name", "new_duration"]),
    ("update {task_name} duration {new_duration}", ["task_name", "new_duration"]),
    ("set {task_name} to take {new_duration}", ["task_name", "new_duration"]),
    ("{task_name} update duration to {new_duration}", ["task_name", "new_duration"]),

    # ── COMBINATION 11 — task + new_priority + new_status ────────
    ("update {task_name} priority to {new_priority} and mark {new_status}", ["task_name", "new_priority", "new_status"]),
    ("change {task_name} to {new_priority} priority and {new_status}", ["task_name", "new_priority", "new_status"]),

    # ── COMBINATION 12 — task + date + new_priority ──────────────
    ("change {task_name} on {date} priority to {new_priority}", ["task_name", "date", "new_priority"]),
    ("update {task_name} on {date} mark as {new_priority}", ["task_name", "date", "new_priority"]),

    # ── COMBINATION 13 — task + date + new_status ────────────────
    ("mark {task_name} on {date} as {new_status}", ["task_name", "date", "new_status"]),
    ("update {task_name} on {date} to {new_status}", ["task_name", "date", "new_status"]),
    ("{task_name} on {date} mark it {new_status}", ["task_name", "date", "new_status"]),

    # ── EXTRA WORD-ORDER VARIANTS (Phase 3) ──────────────────────────
    # task-first bare reschedule
    ("{task_name} move to {new_date}", ["task_name", "new_date"]),
    ("{task_name} change time to {new_time}", ["task_name", "new_time"]),
    ("{task_name} mark {new_status}", ["task_name", "new_status"]),
    ("{task_name} priority {new_priority}", ["task_name", "new_priority"]),
    ("{task_name} rename to {new_taskname}", ["task_name", "new_taskname"]),
    # date-disambiguated (from/to pattern)
    ("the {task_name} on {date} move it to {new_date}", ["task_name", "date", "new_date"]),
    ("the {task_name} on {date} change time to {new_time}", ["task_name", "date", "new_time"]),
    ("{date} {task_name} reschedule to {new_date}", ["task_name", "date", "new_date"]),
    # casual triggers
    ("pls reschedule {task_name} to {new_date}", ["task_name", "new_date"]),
    ("pls change {task_name} time to {new_time}", ["task_name", "new_time"]),
    ("can u move {task_name} to {new_date}", ["task_name", "new_date"]),
    ("can u mark {task_name} as {new_status}", ["task_name", "new_status"]),
    ("yo update {task_name} priority to {new_priority}", ["task_name", "new_priority"]),
    ("hey mark {task_name} as {new_status}", ["task_name", "new_status"]),
    # mid-sentence
    ("I finished {task_name} please mark it {new_status}", ["task_name", "new_status"]),
    ("done with {task_name} set it to {new_status}", ["task_name", "new_status"]),
    ("I want to reschedule {task_name} from {date} to {new_date}", ["task_name", "date", "new_date"]),
    ("{task_name} I need it moved to {new_date}", ["task_name", "new_date"]),
    ("the priority of {task_name} change to {new_priority}", ["task_name", "new_priority"]),
    ("for {task_name} update status to {new_status}", ["task_name", "new_status"]),
    # duration updates
    ("extend {task_name} to {new_duration}", ["task_name", "new_duration"]),
    ("shorten {task_name} to {new_duration}", ["task_name", "new_duration"]),
    ("change duration of {task_name} on {date} to {new_duration}", ["task_name", "date", "new_duration"]),
]

# ================================================================
# SHOW TEMPLATES
# ================================================================

SHOW_TEMPLATES = [

    # ── COMBINATION 1 — task only ────────────────────────────────
    ("show {task_name}", ["task_name"]),
    ("find {task_name}", ["task_name"]),
    ("get {task_name}", ["task_name"]),
    ("display {task_name}", ["task_name"]),
    ("what is my {task_name}", ["task_name"]),
    ("check {task_name}", ["task_name"]),
    ("show me {task_name}", ["task_name"]),
    ("look up {task_name}", ["task_name"]),

    # ── COMBINATION 2 — date only ────────────────────────────────
    ("show tasks for {date}", ["date"]),
    ("what do I have on {date}", ["date"]),
    ("show my schedule for {date}", ["date"]),
    ("what's on {date}", ["date"]),
    ("list tasks for {date}", ["date"]),
    ("get my tasks for {date}", ["date"]),
    ("show me {date} tasks", ["date"]),
    ("{date} schedule", ["date"]),
    ("what do I have {date}", ["date"]),

    # ── COMBINATION 3 — priority only ────────────────────────────
    ("show {priority} priority tasks", ["priority"]),
    ("list my {priority} tasks", ["priority"]),
    ("what are my {priority} priority tasks", ["priority"]),
    ("get my {priority} tasks", ["priority"]),

    # ── COMBINATION 4 — status only ──────────────────────────────
    ("show {status} tasks", ["status"]),
    ("list all {status} tasks", ["status"]),
    ("what tasks are {status}", ["status"]),
    ("get {status} tasks", ["status"]),

    # ── COMBINATION 5 — date + priority ──────────────────────────
    ("show {priority} tasks for {date}", ["date", "priority"]),
    ("list my {priority} tasks on {date}", ["date", "priority"]),
    ("what {priority} tasks do I have on {date}", ["date", "priority"]),

    # ── COMBINATION 6 — date + status ────────────────────────────
    ("show {status} tasks for {date}", ["date", "status"]),
    ("list {status} tasks on {date}", ["date", "status"]),
    ("what tasks are {status} on {date}", ["date", "status"]),

    # ── COMBINATION 7 — task + date ──────────────────────────────
    ("show {task_name} on {date}", ["task_name", "date"]),
    ("find {task_name} for {date}", ["task_name", "date"]),
    ("check {task_name} on {date}", ["task_name", "date"]),

    # ── EXTRA WORD-ORDER VARIANTS (Phase 3) ──────────────────────────
    # date-first show
    ("{date} what do I have", ["date"]),
    ("{date} show tasks", ["date"]),
    ("{date} tasks", ["date"]),
    ("for {date} what tasks", ["date"]),
    # priority/status with different positions
    ("tasks that are {status} show them", ["status"]),
    ("{status} tasks list them", ["status"]),
    ("I want to see {priority} priority tasks", ["priority"]),
    ("show me all {priority} tasks", ["priority"]),
    ("list {status} tasks for {date}", ["date", "status"]),
    ("on {date} what {priority} tasks do I have", ["date", "priority"]),
    # natural question variants
    ("do I have anything on {date}", ["date"]),
    ("anything on {date}", ["date"]),
    ("what's scheduled for {date}", ["date"]),
    ("what's on my schedule for {date}", ["date"]),
    ("am I free on {date}", ["date"]),
    ("check my {date} tasks", ["date"]),
    ("how many {status} tasks do I have", ["status"]),
    ("how many {priority} tasks are there", ["priority"]),
    # task lookup
    ("where is {task_name}", ["task_name"]),
    ("when is {task_name}", ["task_name"]),
    ("when is {task_name} on {date}", ["task_name", "date"]),
    ("{task_name} when is it", ["task_name"]),
    ("{task_name} what time", ["task_name"]),
]

# ================================================================
# BEHAVIORAL TEMPLATES
# ================================================================

BEHAVIORAL_TEMPLATES = [

    # ── day-specific ─────────────────────────────────────────────
    ("when am I most productive on {day}", ["day"]),
    ("what are my best hours on {day}", ["day"]),
    ("when do I work best on {day}", ["day"]),
    ("show my productivity on {day}", ["day"]),
    ("what is my peak time on {day}", ["day"]),
    ("how productive am I on {day}", ["day"]),
    ("show my focus hours on {day}", ["day"]),
    ("when should I study on {day}", ["day"]),
    ("my productivity stats for {day}", ["day"]),
    ("show me my productive hours on {day}", ["day"]),
    ("what time am I most focused on {day}", ["day"]),
    ("best slot to work on {day}", ["day"]),
    ("on {day} when am I most productive", ["day"]),

    # ── no entity — general behavioral ───────────────────────────
    ("show my productivity report", []),
    ("what are my most productive hours", []),
    ("when am I most focused", []),
    ("show my activity patterns", []),
    ("analyze my study habits", []),
    ("show my performance stats", []),
    ("how productive have I been", []),
    ("show my work patterns", []),
    ("what day am I most productive", []),
    ("give me a productivity summary", []),
    ("show my completion rate", []),
    ("how often do I finish tasks on time", []),
    ("show my study habits", []),
]

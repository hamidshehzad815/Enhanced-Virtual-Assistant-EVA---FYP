#!/usr/bin/env node
/**
 * Seed realistic behavioral analytics data for manual E2E + analytics-page
 * testing, under the account hamidshehzad815@gmail.com (creates the user if
 * it doesn't exist yet — the DB was recently cleared).
 *
 * Generation model (same design as seed-areej-behavioral-analytics.js):
 *   - Day-by-day over the last DAYS_OF_HISTORY days, anchored to "now".
 *   - Realistic per-weekday productive windows (peak Tue/Thu afternoons).
 *   - On-time rate driven by priority (high slips more) + weaker evenings.
 *   - Deterministic per run-day: clear + re-run gives a clean, sensible dataset.
 *
 * Usage (from Eva_Backend_Server):
 *   node scripts/seed-hamid-analytics.js --dry-run   # preview full plan, no writes
 *   node scripts/seed-hamid-analytics.js --confirm   # create user + insert data
 *   node scripts/seed-hamid-analytics.js --confirm --clean  # wipe prior seed first, then insert
 *
 * Requires: MONGODB_URI in .env (same DB as AI server + backend)
 */

const fs = require("fs");
const path = require("path");

require("dotenv").config({ path: path.join(__dirname, "..", ".env") });

const { connectDB, disconnectDB } = require("../config/db");
const { User, UserSetting, Task, ActivityLog } = require("../models");

const TARGET_EMAIL = "hamidshehzad815@gmail.com";
const SEED_NAME = "Hamid Shehzad";
const SEED_USERNAME = "hamidshehzad";
const SEED_PASSWORD = "Hamid@Test1234";
const SEED_TAG = "[BEHAV-HAMID]";
const LOG_SOURCE = "seed_behavioral_hamid";
const TIMEZONE_LABEL = "Asia/Karachi";

// "past 2-3 weeks" -> 21 days.
const DAYS_OF_HISTORY = 21;
// Guarantee at least one completion on each of the most-recent days (streak).
const STREAK_TARGET_DAYS = 6;

const DAY_MS = 24 * 60 * 60 * 1000;

const TASK_POOL = [
  "FYP supervisor meeting notes",
  "Submit OS assignment on LMS",
  "Revise DBMS normalization slides",
  "Practice past paper MCQs",
  "Group meeting for FYP demo",
  "Read chapter for software engineering",
  "Fix bugs in Flutter login screen",
  "Prepare slides for presentation",
  "Watch recorded lecture and summarize",
  "Chemistry lab write-up",
  "Email professor about extension",
  "LeetCode practice — arrays",
  "Print and bind report draft",
  "Library quiet hour — thesis reading",
  "Mock viva with roommate",
  "Update Gantt chart for FYP",
  "Rehearse demo script",
  "Backup project to Google Drive",
  "Review teammate PR on GitHub",
  "Flashcards for midterm formulas",
];

/**
 * Per-weekday productive windows (Mon=0 … Sun=6).
 *   Peak days:   Tuesday & Thursday afternoons (2-5 PM)
 *   Good:        Mon/Wed mornings (9-11 AM)
 *   Weaker:      Friday evening, Sunday sparse
 */
const WEEKDAY_PROFILE = {
  0: [
    { h: 9, m: 30, dur: 60, rel: 0.85, freq: 8 },
    { h: 11, m: 0, dur: 45, rel: 0.8, freq: 6 },
    { h: 15, m: 0, dur: 75, rel: 0.82, freq: 6 },
  ],
  1: [
    { h: 10, m: 0, dur: 60, rel: 0.78, freq: 6 },
    { h: 14, m: 0, dur: 75, rel: 0.92, freq: 9 },
    { h: 15, m: 30, dur: 60, rel: 0.9, freq: 9 },
    { h: 16, m: 45, dur: 90, rel: 0.88, freq: 7 },
  ],
  2: [
    { h: 9, m: 45, dur: 60, rel: 0.85, freq: 7 },
    { h: 15, m: 0, dur: 75, rel: 0.82, freq: 7 },
    { h: 20, m: 30, dur: 45, rel: 0.6, freq: 4, part: "evening" },
  ],
  3: [
    { h: 11, m: 15, dur: 50, rel: 0.8, freq: 6 },
    { h: 14, m: 15, dur: 80, rel: 0.91, freq: 9 },
    { h: 16, m: 0, dur: 70, rel: 0.89, freq: 8 },
    { h: 17, m: 30, dur: 60, rel: 0.86, freq: 6 },
  ],
  4: [
    { h: 10, m: 0, dur: 45, rel: 0.75, freq: 10 },
    { h: 13, m: 0, dur: 60, rel: 0.72, freq: 9 },
    { h: 18, m: 30, dur: 90, rel: 0.5, freq: 6, part: "evening" },
  ],
  5: [
    { h: 11, m: 0, dur: 60, rel: 0.7, freq: 10 },
    { h: 16, m: 0, dur: 45, rel: 0.65, freq: 9 },
  ],
  6: [
    { h: 10, m: 30, dur: 45, rel: 0.68, freq: 10 },
    { h: 19, m: 0, dur: 60, rel: 0.6, freq: 9, part: "evening" },
  ],
};

const DAY_NAMES = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

// ~30% high, ~50% medium, ~20% low.
const PRIORITY_SEQUENCE = [
  "high", "medium", "medium", "low", "medium",
  "high", "medium", "low", "medium", "high",
];

const PRIORITY_ONTIME_TARGET = { high: 0.62, medium: 0.9, low: 0.95 };

const args = new Set(process.argv.slice(2));
const DRY_RUN = args.has("--dry-run");
const CONFIRM = args.has("--confirm");
const CLEAN_FIRST = args.has("--clean");

const toDateOrNull = (value) => {
  if (!value) return null;
  const parsed = value instanceof Date ? value : new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};

const getIsoWeekNumber = (inputDate) => {
  const date = new Date(
    Date.UTC(inputDate.getUTCFullYear(), inputDate.getUTCMonth(), inputDate.getUTCDate()),
  );
  const dayNum = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  return Math.ceil(((date - yearStart) / 86400000 + 1) / 7);
};

const pkDateIso = (date) =>
  new Intl.DateTimeFormat("en-CA", {
    year: "numeric", month: "2-digit", day: "2-digit", timeZone: TIMEZONE_LABEL,
  }).format(date);

const pkWeekdayMondayStart = (date) => {
  const midday = new Date(`${pkDateIso(date)}T12:00:00+05:00`);
  return (midday.getUTCDay() + 6) % 7;
};

const pkHour = (date) =>
  Number(
    new Intl.DateTimeFormat("en-GB", { hour: "numeric", hour12: false, timeZone: TIMEZONE_LABEL }).format(date),
  ) % 24;

const pkDateNDaysAgo = (daysAgo, hour, minute) => {
  const target = new Date(Date.now() - daysAgo * DAY_MS);
  const dateIso = pkDateIso(target);
  const hh = String(hour).padStart(2, "0");
  const mm = String(minute).padStart(2, "0");
  return new Date(`${dateIso}T${hh}:${mm}:00+05:00`);
};

const mulberry32 = (seed) => {
  let t = seed >>> 0;
  return () => {
    t += 0x6d2b79f5;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
};

const formatPkt = (date) =>
  new Intl.DateTimeFormat("en-GB", {
    weekday: "short", day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit", hour12: true, timeZone: TIMEZONE_LABEL,
  }).format(date);

function buildSeedPlan() {
  const plan = [];
  let taskIndex = 0;
  const nowPkHour = pkHour(new Date());

  const onTimeState = {
    high: { n: 0, ok: 0 },
    medium: { n: 0, ok: 0 },
    low: { n: 0, ok: 0 },
  };

  for (let daysAgo = DAYS_OF_HISTORY - 1; daysAgo >= 0; daysAgo -= 1) {
    const dayNoon = pkDateNDaysAgo(daysAgo, 12, 0);
    const weekday = pkWeekdayMondayStart(dayNoon);
    const profile = WEEKDAY_PROFILE[weekday] || [];

    const dayKey = Number(pkDateIso(dayNoon).replace(/-/g, ""));
    const rng = mulberry32(dayKey);

    let chosen = profile.filter((slot) => {
      if (daysAgo === 0 && slot.h > nowPkHour) return false;
      return rng() * 10 < slot.freq;
    });

    if (chosen.length === 0 && daysAgo < STREAK_TARGET_DAYS) {
      const fallback = profile
        .filter((slot) => !(daysAgo === 0 && slot.h > nowPkHour))
        .sort((a, b) => b.freq - a.freq)[0];
      if (fallback) chosen = [fallback];
    }

    for (const slot of chosen) {
      const priority = PRIORITY_SEQUENCE[taskIndex % PRIORITY_SEQUENCE.length];

      const st = onTimeState[priority];
      const currentRate = st.n === 0 ? 0 : st.ok / st.n;
      let wasOnTime = currentRate < PRIORITY_ONTIME_TARGET[priority];
      if (wasOnTime && slot.part === "evening" && rng() < 0.45) wasOnTime = false;
      else if (wasOnTime && weekday === 4 && rng() < 0.2) wasOnTime = false;
      st.n += 1;
      if (wasOnTime) st.ok += 1;

      const due = pkDateNDaysAgo(daysAgo, slot.h, slot.m);
      const offsetMin = wasOnTime
        ? -Math.floor(rng() * 25) - 5
        : Math.floor(rng() * 55) + 20;
      const completedAt = new Date(due.getTime() + offsetMin * 60 * 1000);
      const createdAt = new Date(due.getTime() - (1 + Math.floor(rng() * 3)) * DAY_MS);
      const timeTakenMinutes = Math.max(15, Math.round(slot.dur * (0.85 + rng() * 0.4)));
      const rescheduleCount = wasOnTime ? 0 : rng() < 0.4 ? 1 : 0;
      const titleBase = TASK_POOL[taskIndex % TASK_POOL.length];

      plan.push({
        title: `${SEED_TAG} ${titleBase}`,
        description: `Seeded for analytics E2E — ${DAY_NAMES[weekday]} ${slot.h}:${String(slot.m).padStart(2, "0")} PKT (${daysAgo}d ago)`,
        due_datetime: due,
        duration: slot.dur,
        priority,
        status: "complete",
        source: "manual",
        scheduled_by: "manual",
        collaborators: [],
        is_deleted: false,
        reminder_minutes_before: 30,
        completed_at: completedAt,
        created_at: createdAt,
        _seed: { reschedule_count: rescheduleCount, was_on_time: wasOnTime, time_taken_minutes: timeTakenMinutes },
        _meta: {
          days_ago: daysAgo,
          weekday,
          day_name: DAY_NAMES[weekday],
          part: slot.part || "day",
          scheduled_pkt: formatPkt(due),
          completed_pkt: formatPkt(completedAt),
          was_on_time: wasOnTime,
        },
      });

      taskIndex += 1;
    }
  }

  return plan;
}

const buildActivityLog = (task, seedMeta) => {
  const completedAt = toDateOrNull(task.completed_at) || new Date();
  const dueAt = toDateOrNull(task.due_datetime);
  const createdAt = toDateOrNull(task.created_at);
  const scheduledDay = dueAt ? pkWeekdayMondayStart(dueAt) : null;
  const scheduledHour = dueAt ? pkHour(dueAt) : null;

  let timeTakenMinutes = seedMeta.time_taken_minutes;
  if (timeTakenMinutes == null && createdAt) {
    timeTakenMinutes = Math.max(0, Math.floor((completedAt.getTime() - createdAt.getTime()) / (1000 * 60)));
  }

  return {
    user_id: task.owner_id,
    task_id: task._id,
    action_type: "task_completed",
    action_timestamp: completedAt,
    day_of_week: pkWeekdayMondayStart(completedAt),
    hour_of_day: pkHour(completedAt),
    week_number: getIsoWeekNumber(completedAt),
    task_priority: task.priority || null,
    subject: task.title || null,
    source: LOG_SOURCE,
    time_taken_minutes: timeTakenMinutes,
    was_on_time: seedMeta.was_on_time,
    scheduled_hour: scheduledHour,
    scheduled_day: scheduledDay,
    reschedule_count: seedMeta.reschedule_count || 0,
  };
};

function summarizeByDay(logs) {
  const counts = Array(7).fill(0);
  for (const log of logs) {
    const d = log.day_of_week;
    if (d >= 0 && d <= 6) counts[d] += 1;
  }
  return DAY_NAMES.map((name, i) => ({ day: name, count: counts[i] }));
}

function summarizeOnTime(plan) {
  let onTime = 0;
  const byPriority = {
    high: { total: 0, on_time: 0 },
    medium: { total: 0, on_time: 0 },
    low: { total: 0, on_time: 0 },
  };
  for (const row of plan) {
    if (row._seed.was_on_time) onTime += 1;
    const p = byPriority[row.priority];
    if (p) {
      p.total += 1;
      if (row._seed.was_on_time) p.on_time += 1;
    }
  }
  const pct = (n, d) => (d > 0 ? Math.round((n / d) * 100) : 0);
  return {
    overall: pct(onTime, plan.length),
    high: pct(byPriority.high.on_time, byPriority.high.total),
    medium: pct(byPriority.medium.on_time, byPriority.medium.total),
    low: pct(byPriority.low.on_time, byPriority.low.total),
  };
}

async function cleanPreviousSeed(userId) {
  const tasks = await Task.find({
    owner_id: userId,
    title: { $regex: SEED_TAG.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") },
  }).select("_id");
  const taskIds = tasks.map((t) => t._id);
  const logDelete = await ActivityLog.deleteMany({
    user_id: userId,
    $or: [{ source: LOG_SOURCE }, { task_id: { $in: taskIds } }],
  });
  const taskDelete = await Task.deleteMany({ _id: { $in: taskIds } });
  return { tasks_removed: taskDelete.deletedCount || 0, logs_removed: logDelete.deletedCount || 0 };
}

async function ensureUser() {
  const email = TARGET_EMAIL.toLowerCase();
  let user = await User.findOne({ email });
  let created = false;
  if (!user) {
    user = await User.create({
      name: SEED_NAME,
      username: SEED_USERNAME,
      email,
      password_hash: SEED_PASSWORD,
      timezone: TIMEZONE_LABEL,
      auth_provider: "local",
      is_verified: true,
      is_active: true,
    });
    await UserSetting.createDefaultSettings(user._id);
    created = true;
  }
  let settings = await UserSetting.findOne({ user_id: user._id });
  if (!settings) settings = await UserSetting.createDefaultSettings(user._id);
  settings.behavioral_analytics_enabled = true;
  await settings.save();
  return { user, created };
}

function printPlanTable(plan) {
  console.log("\nFull planned data (chronological):\n");
  console.log(
    "#".padEnd(4) + "Date".padEnd(18) + "Day".padEnd(11) + "Sched Time".padEnd(12) +
    "Title".padEnd(38) + "Dur".padEnd(6) + "Prio".padEnd(8) + "OnTime".padEnd(8) + "Completed",
  );
  plan.forEach((row, i) => {
    const m = row._meta;
    console.log(
      String(i + 1).padEnd(4) +
      pkDateIso(row.due_datetime).padEnd(18) +
      m.day_name.padEnd(11) +
      `${String(row.due_datetime.getHours()).padStart(2, "0")}:${String(row.due_datetime.getMinutes()).padStart(2, "0")}`.padEnd(12) +
      row.title.replace(SEED_TAG, "").trim().slice(0, 36).padEnd(38) +
      `${row.duration}m`.padEnd(6) +
      row.priority.padEnd(8) +
      String(row._seed.was_on_time).padEnd(8) +
      m.completed_pkt,
    );
  });
}

async function main() {
  if (!process.env.MONGODB_URI) {
    console.error("MONGODB_URI is not set in Eva_Backend_Server/.env");
    process.exit(1);
  }
  if (!DRY_RUN && !CONFIRM) {
    console.error("Refusing to run without --dry-run or --confirm.");
    process.exit(1);
  }

  const connected = await connectDB();
  if (!connected) {
    console.error("Failed to connect to MongoDB");
    process.exit(1);
  }

  try {
    const plan = buildSeedPlan();
    const previewLogs = plan.map((p) => ({
      action_timestamp: p.completed_at,
      day_of_week: pkWeekdayMondayStart(p.completed_at),
    }));

    if (DRY_RUN) {
      printPlanTable(plan);
      console.log(
        "\n" +
        JSON.stringify(
          {
            ok: true,
            dry_run: true,
            target_email: TARGET_EMAIL,
            days_of_history: DAYS_OF_HISTORY,
            would_insert_tasks: plan.length,
            would_insert_logs: plan.length,
            on_time: summarizeOnTime(plan),
            by_day: summarizeByDay(previewLogs),
          },
          null,
          2,
        ),
      );
      return;
    }

    const { user, created } = await ensureUser();

    let cleanStats = { tasks_removed: 0, logs_removed: 0 };
    if (CLEAN_FIRST) {
      cleanStats = await cleanPreviousSeed(user._id);
    }

    const taskDocs = plan.map(({ _meta, _seed, ...task }) => ({ ...task, owner_id: user._id }));
    const insertedTasks = await Task.insertMany(taskDocs);
    const logs = insertedTasks.map((task, i) => buildActivityLog(task.toObject(), plan[i]._seed));
    await ActivityLog.insertMany(logs);

    console.log(
      JSON.stringify(
        {
          ok: true,
          email: user.email,
          user_id: String(user._id),
          user_created: created,
          password: created ? SEED_PASSWORD : "(unchanged — user already existed)",
          inserted_tasks: insertedTasks.length,
          inserted_logs: logs.length,
          on_time: summarizeOnTime(plan),
          by_day: summarizeByDay(logs),
          clean: cleanStats,
        },
        null,
        2,
      ),
    );
  } finally {
    await disconnectDB();
  }
}

main().catch((error) => {
  console.error("Seed failed:", error.message);
  process.exit(1);
});

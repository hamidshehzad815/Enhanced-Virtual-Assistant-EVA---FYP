#!/usr/bin/env node
/**
 * Seed realistic behavioral analytics data for manual E2E + analytics-page testing.
 *
 * Target user: hamidlilla7@gmail.com (FYP student persona)
 *
 * Generation model (rewritten):
 *   - Day-by-day over the last DAYS_OF_HISTORY days, anchored to "now".
 *   - Fills the CURRENT week AND previous weeks (so week-over-week works).
 *   - Builds a live completion streak ending today.
 *   - Realistic per-weekday productive windows (peak Tue/Thu afternoons).
 *   - On-time rate driven by priority (high slips more) + weaker evenings.
 *   - Deterministic per run-day: clear + re-run gives a clean, sensible dataset
 *     anchored to whatever "today" is.
 *
 * This lights up every analytics-page section: productivity_score, hero,
 * insights, daily_completions, time_of_day, priority_performance, heatmap,
 * completion_trend, streak, and on-time rate.
 *
 * Usage (from Eva_Backend_Server):
 *   node scripts/seed-areej-behavioral-analytics.js
 *   node scripts/seed-areej-behavioral-analytics.js --clean   # remove prior seed data first
 *   node scripts/seed-areej-behavioral-analytics.js --dry-run # preview counts only
 *
 * Recommended (fresh, sensible data every time):
 *   node scripts/seed-areej-behavioral-analytics.js --clean
 *
 * Requires: MONGODB_URI in .env (same DB as AI server + backend)
 */

const fs = require("fs");
const path = require("path");

require("dotenv").config({ path: path.join(__dirname, "..", ".env") });

const mongoose = require("mongoose");
const { connectDB, disconnectDB } = require("../config/db");
const { User, UserSetting, Task, ActivityLog } = require("../models");

const TARGET_EMAIL = "hamidlilla7@gmail.com";
const SEED_TAG = "[BEHAV-AREEJ]";
const LOG_SOURCE = "seed_behavioral_areej";
const TIMEZONE_LABEL = "Asia/Karachi";

// How many days back to generate (covers current + ~4 previous weeks).
const DAYS_OF_HISTORY = 30;
// Guarantee at least one completion on each of the most-recent days (streak).
const STREAK_TARGET_DAYS = 6;

const DAY_MS = 24 * 60 * 60 * 1000;

// --- Persona: what the student actually completes (student voice) ---
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
 * Each slot:
 *   h, m       → local (PKT) start time
 *   dur        → planned duration (minutes)
 *   rel        → base reliability hint (kept for realism)
 *   freq       → 0–10 chance this slot fires on a given day (creates variance)
 *   part       → optional day-part tag; "evening" slots are less reliable
 *
 * Shape of the resulting analytics:
 *   - Peak days:   Tuesday & Thursday afternoons (2–5 PM)
 *   - Good:        Mon/Wed mornings (9–11 AM)
 *   - Weaker:      Friday evening, Sunday sparse
 *   - Dominant time-of-day: Afternoon
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
    { h: 13, m: 0, dur: 60, rel: 0.72, freq: 6 },
    { h: 18, m: 30, dur: 90, rel: 0.5, freq: 4, part: "evening" },
  ],
  5: [{ h: 11, m: 0, dur: 60, rel: 0.7, freq: 4 }],
  6: [{ h: 19, m: 0, dur: 60, rel: 0.6, freq: 3, part: "evening" }],
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

// ~30% high, ~50% medium, ~20% low — enough high-priority to show priority insights.
const PRIORITY_SEQUENCE = [
  "high",
  "medium",
  "medium",
  "low",
  "medium",
  "high",
  "medium",
  "low",
  "medium",
  "high",
];

// Target on-time rate per priority. High deliberately slips more so the
// "high-priority tasks slip" analytics insight surfaces cleanly. Enforced as a
// running average so the aggregate rates are stable regardless of sample size.
const PRIORITY_ONTIME_TARGET = { high: 0.62, medium: 0.9, low: 0.95 };

const args = new Set(process.argv.slice(2));
const DRY_RUN = args.has("--dry-run");
const CLEAN_FIRST = args.has("--clean");

const toDateOrNull = (value) => {
  if (!value) return null;
  const parsed = value instanceof Date ? value : new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};

const getIsoWeekNumber = (inputDate) => {
  const date = new Date(
    Date.UTC(
      inputDate.getUTCFullYear(),
      inputDate.getUTCMonth(),
      inputDate.getUTCDate(),
    ),
  );
  const dayNum = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  return Math.ceil(((date - yearStart) / 86400000 + 1) / 7);
};

const pkDateIso = (date) =>
  new Intl.DateTimeFormat("en-CA", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    timeZone: TIMEZONE_LABEL,
  }).format(date);

/** Monday=0 weekday in user's timezone (matches scorer expectations). */
const pkWeekdayMondayStart = (date) => {
  const midday = new Date(`${pkDateIso(date)}T12:00:00+05:00`);
  return (midday.getUTCDay() + 6) % 7;
};

const pkHour = (date) =>
  Number(
    new Intl.DateTimeFormat("en-GB", {
      hour: "numeric",
      hour12: false,
      timeZone: TIMEZONE_LABEL,
    }).format(date),
  ) % 24;

/** Build a PKT datetime for the calendar day `daysAgo` days before now. */
const pkDateNDaysAgo = (daysAgo, hour, minute) => {
  const target = new Date(Date.now() - daysAgo * DAY_MS);
  const dateIso = pkDateIso(target);
  const hh = String(hour).padStart(2, "0");
  const mm = String(minute).padStart(2, "0");
  return new Date(`${dateIso}T${hh}:${mm}:00+05:00`);
};

/** Small deterministic PRNG so a given run-day yields a stable dataset. */
const mulberry32 = (seed) => {
  let t = seed >>> 0;
  return () => {
    t += 0x6d2b79f5;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
};

const buildActivityLog = (task, seedMeta) => {
  const completedAt = toDateOrNull(task.completed_at) || new Date();
  const dueAt = toDateOrNull(task.due_datetime);
  const createdAt = toDateOrNull(task.created_at);
  const scheduledDay = dueAt ? pkWeekdayMondayStart(dueAt) : null;
  const scheduledHour = dueAt ? pkHour(dueAt) : null;

  let timeTakenMinutes = seedMeta.time_taken_minutes;
  if (timeTakenMinutes == null && createdAt) {
    timeTakenMinutes = Math.max(
      0,
      Math.floor((completedAt.getTime() - createdAt.getTime()) / (1000 * 60)),
    );
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

const formatPkt = (date) =>
  new Intl.DateTimeFormat("en-GB", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
    timeZone: TIMEZONE_LABEL,
  }).format(date);

async function ensureUserSettings(userId) {
  let settings = await UserSetting.findOne({ user_id: userId });
  if (!settings) {
    settings = await UserSetting.createDefaultSettings(userId);
  }
  settings.behavioral_analytics_enabled = true;
  await settings.save();
  return settings;
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

  return {
    tasks_removed: taskDelete.deletedCount || 0,
    logs_removed: logDelete.deletedCount || 0,
  };
}

/**
 * Day-by-day plan builder. Walks from the oldest day to today, choosing which
 * productive slots "fire" each day, then produces one completed task per slot.
 */
function buildSeedPlan() {
  const plan = [];
  let taskIndex = 0;

  const nowPkHour = pkHour(new Date());

  // Running on-time tally per priority so aggregate rates converge to target.
  const onTimeState = {
    high: { n: 0, ok: 0 },
    medium: { n: 0, ok: 0 },
    low: { n: 0, ok: 0 },
  };

  for (let daysAgo = DAYS_OF_HISTORY - 1; daysAgo >= 0; daysAgo -= 1) {
    const dayNoon = pkDateNDaysAgo(daysAgo, 12, 0);
    const weekday = pkWeekdayMondayStart(dayNoon);
    const profile = WEEKDAY_PROFILE[weekday] || [];

    // Deterministic per calendar day: same day → same choices on re-run.
    const dayKey = Number(pkDateIso(dayNoon).replace(/-/g, ""));
    const rng = mulberry32(dayKey);

    let chosen = profile.filter((slot) => {
      // Don't complete tasks in the future (today, before the slot's hour).
      if (daysAgo === 0 && slot.h > nowPkHour) return false;
      return rng() * 10 < slot.freq;
    });

    // Keep the streak alive on the most-recent days.
    if (chosen.length === 0 && daysAgo < STREAK_TARGET_DAYS) {
      const fallback = profile
        .filter((slot) => !(daysAgo === 0 && slot.h > nowPkHour))
        .sort((a, b) => b.freq - a.freq)[0];
      if (fallback) chosen = [fallback];
    }

    for (const slot of chosen) {
      const priority = PRIORITY_SEQUENCE[taskIndex % PRIORITY_SEQUENCE.length];

      // On-time: converge each priority to its target rate (clean analytics
      // signal), with a little extra lateness in the evening / on Fridays.
      const st = onTimeState[priority];
      const currentRate = st.n === 0 ? 0 : st.ok / st.n;
      let wasOnTime = currentRate < PRIORITY_ONTIME_TARGET[priority];
      if (wasOnTime && slot.part === "evening" && rng() < 0.45) wasOnTime = false;
      else if (wasOnTime && weekday === 4 && rng() < 0.2) wasOnTime = false;
      st.n += 1;
      if (wasOnTime) st.ok += 1;

      const due = pkDateNDaysAgo(daysAgo, slot.h, slot.m);

      // Complete a bit early when on time, a bit late otherwise (same day).
      const offsetMin = wasOnTime
        ? -Math.floor(rng() * 25) - 5
        : Math.floor(rng() * 55) + 20;
      const completedAt = new Date(due.getTime() + offsetMin * 60 * 1000);

      const createdAt = new Date(
        due.getTime() - (1 + Math.floor(rng() * 3)) * DAY_MS,
      );
      const timeTakenMinutes = Math.max(
        15,
        Math.round(slot.dur * (0.85 + rng() * 0.4)),
      );
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
        _seed: {
          reschedule_count: rescheduleCount,
          was_on_time: wasOnTime,
          time_taken_minutes: timeTakenMinutes,
        },
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

function summarizeByDay(logs) {
  const counts = Array(7).fill(0);
  for (const log of logs) {
    const d = log.day_of_week;
    if (d >= 0 && d <= 6) counts[d] += 1;
  }
  return DAY_NAMES.map((name, i) => ({ day: name, count: counts[i] }));
}

/** Split completions into current vs previous Monday-start local week. */
function summarizeWeekOverWeek(logs) {
  const now = new Date();
  const weekday = pkWeekdayMondayStart(now);
  const thisMondayIso = pkDateIso(new Date(Date.now() - weekday * DAY_MS));
  const thisMondayStart = new Date(`${thisMondayIso}T00:00:00+05:00`);
  const lastMondayStart = new Date(thisMondayStart.getTime() - 7 * DAY_MS);

  let thisWeek = 0;
  let lastWeek = 0;
  for (const log of logs) {
    const t = new Date(log.action_timestamp);
    if (t >= thisMondayStart) thisWeek += 1;
    else if (t >= lastMondayStart && t < thisMondayStart) lastWeek += 1;
  }
  return { thisWeek, lastWeek };
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

function writeSummaryFile(user, plan, logs, cleanStats) {
  const outPath = path.resolve(
    __dirname,
    "..",
    "..",
    "EVA_Behavioral_Seed_AREEJ.txt",
  );

  const wow = summarizeWeekOverWeek(logs);
  const onTime = summarizeOnTime(plan);
  const activeDays = new Set(
    logs.map((l) => pkDateIso(new Date(l.action_timestamp))),
  ).size;

  const chatTests = [
    "when am I most productive",
    "what are my peak hours",
    "which days am I most focused",
    "when am I productive on Tuesday",
    "find the best time for me on Thursday",
    "find the best time for me",
    "show my completion rate",
    "show my productivity report",
    "how am I doing this week",
  ];

  const lines = [
    "EVA Behavioral Analytics — Seed Summary",
    "=".repeat(60),
    `Email:     ${user.email}`,
    `User ID:   ${user._id}`,
    `Timezone:  ${user.timezone || TIMEZONE_LABEL}`,
    `Generated: ${new Date().toISOString()}`,
    "",
    "Cleanup (if --clean was used):",
    `  Tasks removed: ${cleanStats?.tasks_removed ?? 0}`,
    `  Logs removed:  ${cleanStats?.logs_removed ?? 0}`,
    "",
    `Inserted completed tasks: ${plan.length}`,
    `Inserted activity logs:   ${logs.length}`,
    `Active days (last ${DAYS_OF_HISTORY}): ${activeDays}`,
    "",
    "Week-over-week (Mon-start, PKT):",
    `  This week completed: ${wow.thisWeek}`,
    `  Last week completed: ${wow.lastWeek}`,
    "",
    "On-time rate:",
    `  Overall: ${onTime.overall}%`,
    `  High:    ${onTime.high}%   (intentionally lower — drives 'high-priority slips' insight)`,
    `  Medium:  ${onTime.medium}%`,
    `  Low:     ${onTime.low}%`,
    "",
    "Expected analytics-page shape:",
    "  - Productivity Score: mid-high (Great / Excellent)",
    "  - Strongest days:  Tuesday & Thursday",
    "  - Peak hours:      ~2:00 PM – 5:00 PM PKT",
    "  - Dominant time:   Afternoon",
    "  - Weaker:          Friday evening, late Sunday",
    "  - Streak:          alive through today",
    "  - Both CURRENT and PREVIOUS week populated",
    "",
    "Completions by day_of_week:",
    ...summarizeByDay(logs).map((row) => `  ${row.day.padEnd(10)} ${row.count}`),
    "",
    "CHAT PHRASES TO TEST:",
    ...chatTests.map((t, i) => `  ${i + 1}. "${t}"`),
    "",
    "Follow-up test (best time, no day):",
    '  User: "find the best time for me"',
    '  EVA should ask which day → reply: "Tuesday"',
    "",
    "Sample seeded tasks (most recent 15):",
    ...plan
      .slice(-15)
      .reverse()
      .map((row, i) => {
        const m = row._meta;
        return (
          `  ${String(i + 1).padStart(2, "0")}. ${row.title} [${row.priority}]\n` +
          `      Due: ${m.scheduled_pkt} | Done: ${m.completed_pkt} | on-time: ${m.was_on_time}`
        );
      }),
    "",
    "Re-run seed:",
    "  cd Eva_Backend_Server && node scripts/seed-areej-behavioral-analytics.js --clean",
    "",
  ];

  fs.writeFileSync(outPath, `${lines.join("\n")}\n`, "utf8");
  return outPath;
}

async function main() {
  if (!process.env.MONGODB_URI) {
    console.error("MONGODB_URI is not set in Eva_Backend_Server/.env");
    process.exit(1);
  }

  const connected = await connectDB();
  if (!connected) {
    console.error("Failed to connect to MongoDB");
    process.exit(1);
  }

  try {
    const email = TARGET_EMAIL.toLowerCase();
    const user = await User.findOne({ email }).lean();
    if (!user) {
      throw new Error(`User not found: ${email}. Create/seed the user first.`);
    }

    let cleanStats = { tasks_removed: 0, logs_removed: 0 };
    if (CLEAN_FIRST) {
      cleanStats = await cleanPreviousSeed(user._id);
      console.log("Cleaned previous seed:", cleanStats);
    }

    const plan = buildSeedPlan();

    if (DRY_RUN) {
      const previewLogs = plan.map((p) => ({
        action_timestamp: p.completed_at,
        day_of_week: pkWeekdayMondayStart(p.completed_at),
      }));
      console.log(
        JSON.stringify(
          {
            ok: true,
            dry_run: true,
            email,
            user_id: String(user._id),
            would_insert_tasks: plan.length,
            would_insert_logs: plan.length,
            week_over_week: summarizeWeekOverWeek(previewLogs),
            on_time: summarizeOnTime(plan),
            by_day: summarizeByDay(previewLogs),
          },
          null,
          2,
        ),
      );
      return;
    }

    await ensureUserSettings(user._id);

    const taskDocs = plan.map(({ _meta, _seed, ...task }) => ({
      ...task,
      owner_id: user._id,
    }));

    const insertedTasks = await Task.insertMany(taskDocs);

    const logs = insertedTasks.map((task, i) =>
      buildActivityLog(task.toObject(), plan[i]._seed),
    );

    await ActivityLog.insertMany(logs);

    const summaryPath = writeSummaryFile(user, plan, logs, cleanStats);

    const existingTotal = await ActivityLog.countDocuments({
      user_id: user._id,
      action_type: "task_completed",
    });

    console.log(
      JSON.stringify(
        {
          ok: true,
          email,
          user_id: String(user._id),
          name: user.name,
          inserted_tasks: insertedTasks.length,
          inserted_logs: logs.length,
          total_task_completed_logs_for_user: existingTotal,
          week_over_week: summarizeWeekOverWeek(logs),
          on_time: summarizeOnTime(plan),
          behavioral_analytics_enabled: true,
          clean: cleanStats,
          summary_file: summaryPath,
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

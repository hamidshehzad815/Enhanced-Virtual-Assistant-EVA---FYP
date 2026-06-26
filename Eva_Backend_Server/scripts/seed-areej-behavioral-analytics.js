#!/usr/bin/env node
/**
 * Seed realistic behavioral analytics data for manual E2E chat testing.
 *
 * Target user: areejFatima@gmail.com (Areej Fatima — FYP student persona)
 *
 * Inserts completed tasks + matching activity_logs (task_completed) with
 * human-like patterns across days, dates, and times (Asia/Karachi).
 *
 * Usage (from Eva_Backend_Server):
 *   node scripts/seed-areej-behavioral-analytics.js
 *   node scripts/seed-areej-behavioral-analytics.js --clean   # remove prior seed data first
 *   node scripts/seed-areej-behavioral-analytics.js --dry-run # preview counts only
 *
 * Requires: MONGODB_URI in .env (same DB as AI server + backend)
 */

const fs = require("fs");
const path = require("path");

require("dotenv").config({ path: path.join(__dirname, "..", ".env") });

const mongoose = require("mongoose");
const { connectDB, disconnectDB } = require("../config/db");
const { User, UserSetting, Task, ActivityLog } = require("../models");

const TARGET_EMAIL = "areejFatima@gmail.com";
const SEED_TAG = "[BEHAV-AREEJ]";
const LOG_SOURCE = "seed_behavioral_areej";
const TIMEZONE_LABEL = "Asia/Karachi";
const WEEKS_OF_HISTORY = 3;

// --- Persona: what Areej actually completes (student voice) ---
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
 * Weekly completion slots (PKT). Weight = how often this slot fires that week.
 * Designed so analytics show:
 *   - Peak hours: Tue/Thu 14:00–17:00
 *   - Good mornings: Mon/Wed 09:00–11:00
 *   - Weaker: Fri 18:00+, Sun sparse
 */
const SLOT_PROFILE = [
  { day: 0, hour: 9, minute: 30, weight: 3, duration: 60, onTimeRate: 0.85 },
  { day: 0, hour: 11, minute: 0, weight: 2, duration: 45, onTimeRate: 0.8 },
  { day: 0, hour: 19, minute: 0, weight: 1, duration: 90, onTimeRate: 0.55 },

  { day: 1, hour: 14, minute: 0, weight: 5, duration: 75, onTimeRate: 0.92 },
  { day: 1, hour: 15, minute: 30, weight: 5, duration: 60, onTimeRate: 0.9 },
  { day: 1, hour: 16, minute: 45, weight: 4, duration: 90, onTimeRate: 0.88 },
  { day: 1, hour: 10, minute: 0, weight: 2, duration: 60, onTimeRate: 0.75 },

  { day: 2, hour: 9, minute: 45, weight: 3, duration: 60, onTimeRate: 0.82 },
  { day: 2, hour: 15, minute: 0, weight: 3, duration: 75, onTimeRate: 0.8 },
  { day: 2, hour: 20, minute: 30, weight: 1, duration: 45, onTimeRate: 0.5 },

  { day: 3, hour: 14, minute: 15, weight: 5, duration: 80, onTimeRate: 0.91 },
  { day: 3, hour: 16, minute: 0, weight: 4, duration: 70, onTimeRate: 0.89 },
  { day: 3, hour: 17, minute: 30, weight: 3, duration: 60, onTimeRate: 0.86 },
  { day: 3, hour: 11, minute: 15, weight: 2, duration: 50, onTimeRate: 0.78 },

  { day: 4, hour: 13, minute: 0, weight: 2, duration: 60, onTimeRate: 0.7 },
  { day: 4, hour: 18, minute: 30, weight: 2, duration: 90, onTimeRate: 0.45 },
  { day: 4, hour: 21, minute: 0, weight: 1, duration: 45, onTimeRate: 0.4 },

  { day: 5, hour: 11, minute: 0, weight: 1, duration: 60, onTimeRate: 0.65 },
  { day: 5, hour: 15, minute: 0, weight: 1, duration: 75, onTimeRate: 0.6 },

  { day: 6, hour: 10, minute: 30, weight: 1, duration: 45, onTimeRate: 0.7 },
  { day: 6, hour: 19, minute: 0, weight: 1, duration: 60, onTimeRate: 0.55 },
];

const DAY_NAMES = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

const PRIORITIES = ["high", "medium", "low"];

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

/** Monday=0 weekday in user's timezone (matches hamid seed + scorer expectations). */
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
  );

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

const pkDateOnWeekday = (weeksAgo, weekdayMon0, hour, minute) => {
  const anchor = new Date();
  anchor.setHours(12, 0, 0, 0);
  anchor.setDate(anchor.getDate() - weeksAgo * 7);

  const jsDay = (weekdayMon0 + 1) % 7;
  const currentJs = anchor.getDay();
  let delta = jsDay - currentJs;
  if (delta > 0) delta -= 7;
  anchor.setDate(anchor.getDate() + delta);

  const y = anchor.getFullYear();
  const m = String(anchor.getMonth() + 1).padStart(2, "0");
  const d = String(anchor.getDate()).padStart(2, "0");
  const hh = String(hour).padStart(2, "0");
  const mm = String(minute).padStart(2, "0");
  return new Date(`${y}-${m}-${d}T${hh}:${mm}:00+05:00`);
};

const pickPriority = (index) => PRIORITIES[index % PRIORITIES.length];

const expandSlotEvents = () => {
  const events = [];
  for (let week = WEEKS_OF_HISTORY; week >= 1; week -= 1) {
    for (const slot of SLOT_PROFILE) {
      events.push({ week, slot, variant: week });
    }
  }
  return events;
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

function buildSeedPlan() {
  const events = expandSlotEvents();
  const plan = [];
  let taskIndex = 0;

  for (const { week, slot, variant } of events) {
    const due = pkDateOnWeekday(week, slot.day, slot.hour, slot.minute);
    const duration = slot.duration;
    const createdAt = new Date(due.getTime() - (2 + (variant % 3)) * 24 * 60 * 60 * 1000);

    const onTimeRoll = (taskIndex + variant) % 10;
    const onTimeThreshold = Math.round(slot.onTimeRate * 10);
    const wasOnTime = onTimeRoll < onTimeThreshold;
    const completeOffsetMin = wasOnTime
      ? Math.max(10, duration - 5)
      : duration + 20 + (variant % 4) * 15;
    const completedAt = new Date(due.getTime() + completeOffsetMin * 60 * 1000);
    const timeTakenMinutes = Math.max(15, completeOffsetMin);

    const titleBase = TASK_POOL[taskIndex % TASK_POOL.length];
    const title = `${SEED_TAG} ${titleBase}`;

    plan.push({
      title,
      description: `Seeded for behavioral E2E — week -${week}, ${DAY_NAMES[slot.day]} ${slot.hour}:${String(slot.minute).padStart(2, "0")} PKT`,
      due_datetime: due,
      duration,
      priority: pickPriority(taskIndex),
      status: "complete",
      source: "manual",
      scheduled_by: "manual",
      collaborators: [],
      is_deleted: false,
      reminder_minutes_before: 30,
      completed_at: completedAt,
      created_at: createdAt,
      _seed: {
        reschedule_count: variant % 5 === 0 ? 1 : 0,
        was_on_time: wasOnTime,
        time_taken_minutes: timeTakenMinutes,
      },
      _meta: {
        week,
        day_name: DAY_NAMES[slot.day],
        scheduled_pkt: formatPkt(due),
        completed_pkt: formatPkt(completedAt),
        was_on_time: wasOnTime,
      },
    });

    taskIndex += 1;
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

function writeSummaryFile(user, plan, logs, cleanStats) {
  const outPath = path.resolve(
    __dirname,
    "..",
    "..",
    "EVA_Behavioral_Seed_AREEJ.txt",
  );

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
    "EVA Behavioral Analytics — Seed Summary (Areej Fatima)",
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
    "",
    "Expected analytics pattern (for chat):",
    "  - Strongest days:  Tuesday & Thursday",
    "  - Peak hours:      ~2:00 PM – 5:00 PM PKT",
    "  - Weaker:          Friday evening, late Sunday",
    "  - Total completed: above global threshold (20)",
    "  - Per-day counts:  5+ per weekday (for day-specific queries)",
    "",
    "Completions by day_of_week:",
    ...summarizeByDay(logs).map((row) => `  ${row.day.padEnd(10)} ${row.count}`),
    "",
    "CHAT PHRASES TO TEST (login as areejFatima@gmail.com):",
    ...chatTests.map((t, i) => `  ${i + 1}. "${t}"`),
    "",
    "Follow-up test (best time, no day):",
    '  User: "find the best time for me"',
    '  EVA should ask which day → reply: "Tuesday"',
    "",
    "Sample seeded tasks (first 15):",
    ...plan.slice(0, 15).map((row, i) => {
      const m = row._meta;
      return (
        `  ${String(i + 1).padStart(2, "0")}. ${row.title}\n` +
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
      throw new Error(
        `User not found: ${email}. Run: node scripts/seed-areej-user.js first.`,
      );
    }

    let cleanStats = { tasks_removed: 0, logs_removed: 0 };
    if (CLEAN_FIRST) {
      cleanStats = await cleanPreviousSeed(user._id);
      console.log("Cleaned previous seed:", cleanStats);
    }

    const plan = buildSeedPlan();

    if (DRY_RUN) {
      console.log(
        JSON.stringify(
          {
            ok: true,
            dry_run: true,
            email,
            user_id: String(user._id),
            would_insert_tasks: plan.length,
            would_insert_logs: plan.length,
            by_day: summarizeByDay(
              plan.map((p) => ({
                day_of_week:
                  p.completed_at.getUTCDay() === 0
                    ? 6
                    : p.completed_at.getUTCDay() - 1,
              })),
            ),
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
          behavioral_analytics_enabled: true,
          clean: cleanStats,
          summary_file: summaryPath,
          chat_login: {
            email: TARGET_EMAIL,
            password_hint: "see seed-areej-user.js (default areejFatima@1234)",
          },
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

const fs = require("fs");
const path = require("path");
const mongoose = require("mongoose");

const User = require("../models/User");
const Task = require("../models/Task");
const ActivityLog = require("../models/ActivityLog");

const MONGODB_URI = process.env.MONGODB_URI || "mongodb://localhost:27017/EVA";
const TARGET_USERNAME = "hamid";
const TOTAL_TASKS = 36;

const TIME_SLOTS = [
  "12:15",
  "13:40",
  "15:10",
  "16:30",
  "18:00",
  "19:20",
  "20:40",
  "21:45",
];

const DURATIONS = [45, 60, 75, 90];
const PRIORITIES = ["high", "medium", "low"];
const TITLES = [
  "Physics revision",
  "Calculus practice",
  "Database assignment",
  "Operating systems prep",
  "Networking quiz review",
  "AI model debugging",
  "Final year project sync",
  "English presentation prep",
  "Software design notes",
  "Linear algebra drill",
  "Chemistry problem set",
  "Urdu assignment",
  "Machine learning exercises",
  "Weekend recap planning",
  "Roadmap progress review",
  "Data structures revision",
  "Probability worksheet",
  "Compiler design reading",
];

function toPkDate(dateStr, timeStr) {
  return new Date(`${dateStr}T${timeStr}:00+05:00`);
}

function toWeekdayMondayStart(dateStr) {
  const middayPk = new Date(`${dateStr}T12:00:00+05:00`);
  const sundayStart = middayPk.getUTCDay();
  return (sundayStart + 6) % 7;
}

function addMinutes(date, minutes) {
  return new Date(date.getTime() + minutes * 60 * 1000);
}

function fmtTime12(timeStr) {
  const [hRaw, m] = timeStr.split(":").map(Number);
  const suffix = hRaw >= 12 ? "PM" : "AM";
  const h12 = hRaw % 12 === 0 ? 12 : hRaw % 12;
  return `${h12}:${String(m).padStart(2, "0")} ${suffix}`;
}

function fmtDate(date) {
  return new Intl.DateTimeFormat("en-GB", {
    weekday: "long",
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "Asia/Karachi",
  }).format(date);
}

async function run() {
  await mongoose.connect(MONGODB_URI);
  try {
    const user = await User.findOne({ username: TARGET_USERNAME }).lean();
    if (!user) {
      throw new Error(`User '${TARGET_USERNAME}' not found.`);
    }

    const startPkDate = new Date("2026-04-01T00:00:00+05:00");
    const tasks = [];
    const logs = [];
    const lines = [];

    for (let i = 0; i < TOTAL_TASKS; i += 1) {
      const dayDate = new Date(startPkDate.getTime() + i * 24 * 60 * 60 * 1000);
      const dayIsoPk = new Intl.DateTimeFormat("en-CA", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        timeZone: "Asia/Karachi",
      }).format(dayDate);

      const timeStr = TIME_SLOTS[i % TIME_SLOTS.length];
      const due = toPkDate(dayIsoPk, timeStr);
      const duration = DURATIONS[i % DURATIONS.length];
      const priority = PRIORITIES[i % PRIORITIES.length];
      const titleBase = TITLES[i % TITLES.length];
      const title = `[AUTO-HAMID-${String(i + 1).padStart(2, "0")}] ${titleBase}`;
      const wasOnTime = i % 6 !== 0;
      const completeOffset = wasOnTime ? Math.max(10, duration - 5) : duration + 35;
      const completedAt = addMinutes(due, completeOffset);
      const weekdayMonStart = toWeekdayMondayStart(dayIsoPk);
      const scheduledHour = Number(timeStr.split(":")[0]);
      const timeTaken = Math.max(15, completeOffset);

      tasks.push({
        owner_id: user._id,
        title,
        due_datetime: due,
        is_all_day: false,
        duration,
        priority,
        status: "complete",
        source: "manual",
        scheduled_by: "manual",
        collaborators: [],
        is_deleted: false,
        reminder_minutes_before: 30,
        completed_at: completedAt,
      });

      lines.push(
        `${String(i + 1).padStart(2, "0")}. ${title}\n` +
          `    ${fmtDate(due)} at ${fmtTime12(timeStr)} PKT | duration ${duration}m | priority ${priority} | complete`,
      );

      logs.push({
        action_type: "task_completed",
        action_timestamp: completedAt,
        day_of_week: weekdayMonStart,
        hour_of_day: scheduledHour,
        week_number: Math.ceil((i + 1) / 7),
        task_priority: priority,
        source: "seed_script",
        time_taken_minutes: timeTaken,
        was_on_time: wasOnTime,
        scheduled_hour: scheduledHour,
        scheduled_day: weekdayMonStart,
        reschedule_count: i % 8 === 0 ? 1 : 0,
      });
    }

    const insertedTasks = await Task.insertMany(tasks);
    for (let i = 0; i < insertedTasks.length; i += 1) {
      logs[i].task_id = insertedTasks[i]._id;
      logs[i].user_id = user._id;
    }
    await ActivityLog.insertMany(logs);

    const summaryPath = path.resolve(
      __dirname,
      "..",
      "..",
      "EVA_Task_Test_Data_HAMID.txt",
    );
    const summary =
      `EVA Seeded Tasks for user '${user.username}' (${user.name})\n` +
      `Generated at: ${new Date().toISOString()}\n` +
      `Total inserted tasks: ${insertedTasks.length}\n` +
      `Total inserted logs: ${logs.length}\n\n` +
      lines.join("\n\n") +
      "\n";
    fs.writeFileSync(summaryPath, summary, "utf8");

    console.log(
      JSON.stringify(
        {
          ok: true,
          user_id: String(user._id),
          username: user.username,
          inserted_tasks: insertedTasks.length,
          inserted_logs: logs.length,
          summary_file: summaryPath,
        },
        null,
        2,
      ),
    );
  } finally {
    await mongoose.disconnect();
  }
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});


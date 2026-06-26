/**
 * Seed a full learning plan for a user — same DB shape as chat learning_create.
 *
 * Example (Python basics, 60 days, starting today):
 *   node scripts/seed-learning-plan.js
 *   node scripts/seed-learning-plan.js --email areejFatima@gmail.com --topic Python --level basics --days 60 --start today --replace
 *
 * Default (no --topic): seeds Python, JavaScript, and SQL basics for the user.
 *
 * Prerequisites:
 *   - User exists (run seed-areej-user.js first if needed)
 *   - roadmap_resources seeded (use --seed-roadmaps or npm run seed:roadmaps)
 *   - User gets a default learning schedule if none exists
 */

const path = require("path");
require("dotenv").config({ path: path.join(__dirname, "..", ".env") });

const mongoose = require("mongoose");
const { connectDB, disconnectDB } = require("../config/db");
const {
  User,
  UserSetting,
  Task,
  LearningGoal,
  RoadmapTopic,
} = require("../models");
const { normalizeTimezone, parseDateOnly, toUtcFromLocalParts } = require("../utils/timezone");
const {
  resolveRoadmapsJsonPath,
  loadRoadmapsJson,
  seedFromRoadmapsJson,
} = require("./seed-roadmaps");

const DEFAULT_DURATION_MINUTES = 90;
const DEFAULT_LEARNING_REMINDER_MINUTES = 15;
const DEFAULT_EMAIL = "areejFatima@gmail.com";
const DEFAULT_LEVEL = "basics";
const DEFAULT_DURATION_DAYS = 60;

/** Default seed: three learning plans (different languages can coexist). */
const DEFAULT_PLANS = [
  { topic: "Python", level: "basics" },
  { topic: "JavaScript", level: "basics" },
  { topic: "SQL", level: "basics" },
];

const DEMO_YOUTUBE_RESOURCES = [
  {
    title: "Python Tutorial - Python Full Course for Beginners",
    url: "https://www.youtube.com/watch?v=_uQrJ0TkZlc",
    thumbnail: "https://i.ytimg.com/vi/_uQrJ0TkZlc/hqdefault.jpg",
    channel: "Programming with Mosh",
    view_count: "42000000",
  },
  {
    title: "Learn Python - Full Course for Beginners",
    url: "https://www.youtube.com/watch?v=rfscVS0vtbw",
    thumbnail: "https://i.ytimg.com/vi/rfscVS0vtbw/hqdefault.jpg",
    channel: "freeCodeCamp.org",
    view_count: "48000000",
  },
  {
    title: "Python for Beginners - Learn Coding with Python",
    url: "https://www.youtube.com/watch?v=b093aqAZiPU",
    thumbnail: "https://i.ytimg.com/vi/b093aqAZiPU/hqdefault.jpg",
    channel: "Programming with Mosh",
    view_count: "1200000",
  },
];

const DEFAULT_LEARNING_SCHEDULE = {
  id: "seed-weekday-evenings",
  label: "Weekday evenings",
  slots: [
    { day: 0, time: "18:00", duration_minutes: 90 },
    { day: 2, time: "18:00", duration_minutes: 90 },
    { day: 4, time: "18:00", duration_minutes: 90 },
  ],
};

const parseArgs = () => {
  const argv = process.argv.slice(2);
  const getFlag = (name) => {
    const index = argv.indexOf(name);
    if (index === -1) {
      return null;
    }
    return argv[index + 1] ?? true;
  };

  return {
    email: String(getFlag("--email") || DEFAULT_EMAIL).trim().toLowerCase(),
    topic: getFlag("--topic") ? String(getFlag("--topic")).trim() : null,
    level: String(getFlag("--level") || DEFAULT_LEVEL).trim().toLowerCase(),
    days: Number.parseInt(String(getFlag("--days") || DEFAULT_DURATION_DAYS), 10),
    start: String(getFlag("--start") || "today").trim(),
    scheduleId: getFlag("--schedule-id") ? String(getFlag("--schedule-id")).trim() : null,
    replace: argv.includes("--replace"),
    seedRoadmaps: argv.includes("--seed-roadmaps"),
    pythonResources: argv.includes("--python-resources"),
  };
};

const resolvePlansToSeed = (options) => {
  if (options.topic) {
    return [{ topic: options.topic, level: options.level }];
  }
  return DEFAULT_PLANS;
};

const getTodayInTimezone = (timezone) => {
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: normalizeTimezone(timezone),
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
  return formatter.format(new Date());
};

const resolveStartDate = (rawStart, timezone) => {
  if (!rawStart || rawStart.toLowerCase() === "today") {
    return getTodayInTimezone(timezone);
  }
  if (!parseDateOnly(rawStart)) {
    throw new Error(`Invalid --start value "${rawStart}". Use YYYY-MM-DD or today.`);
  }
  return rawStart.slice(0, 10);
};

const dateOnlyToMidnight = (isoDate) => {
  const parsed = parseDateOnly(isoDate);
  if (!parsed) {
    throw new Error(`Invalid date: ${isoDate}`);
  }
  const { year, month, day } = parsed;
  return new Date(year, month - 1, day, 0, 0, 0, 0);
};

const learningDaysFromSlots = (slots) =>
  new Set((slots || []).map((slot) => Number(slot.day)).filter((day) => day >= 0 && day <= 6));

const calculateAvailableSessions = (startIso, durationDays, learningDays) => {
  const parsed = parseDateOnly(startIso);
  if (!parsed || durationDays < 1) {
    return 0;
  }

  let total = 0;
  const cursor = new Date(parsed.year, parsed.month - 1, parsed.day, 12, 0, 0, 0);

  for (let i = 0; i < durationDays; i += 1) {
    const weekday = (cursor.getDay() + 6) % 7;
    if (learningDays.has(weekday)) {
      total += 1;
    }
    cursor.setDate(cursor.getDate() + 1);
  }

  return total;
};

const parseHhMm = (value) => {
  const match = String(value || "").trim().match(/^(\d{1,2}):(\d{2})$/);
  if (!match) {
    throw new Error(`Invalid time "${value}"`);
  }
  return {
    hour: Number.parseInt(match[1], 10),
    minute: Number.parseInt(match[2], 10),
  };
};

const localDatetimeToUtcNaive = (dateIso, timeValue, timezone) => {
  const parsed = parseDateOnly(dateIso);
  if (!parsed) {
    return null;
  }
  const { hour, minute } = parseHhMm(timeValue);
  return toUtcFromLocalParts(
    parsed.year,
    parsed.month,
    parsed.day,
    hour,
    minute,
    0,
    normalizeTimezone(timezone),
  );
};

const normalizeResources = (resources) =>
  (Array.isArray(resources) ? resources : []).map((item) => ({
    title: String(item?.title || ""),
    url: String(item?.url || ""),
    thumbnail: item?.thumbnail || null,
    channel_name: item?.channel_name || item?.channel || null,
  }));

const buildSchedule = (startIso, topics, scheduleSlots, timezone) => {
  const byDay = new Map();
  for (const slot of scheduleSlots || []) {
    const day = Number(slot.day);
    let duration = DEFAULT_DURATION_MINUTES;
    if (slot.duration_minutes != null) {
      const parsed = Number(slot.duration_minutes);
      if (Number.isFinite(parsed)) {
        duration = Math.max(15, Math.min(240, parsed));
      }
    }
    byDay.set(day, {
      time: String(slot.time),
      duration_minutes: duration,
    });
  }

  const learningDays = new Set(byDay.keys());
  if (!learningDays.size || !topics.length) {
    return [];
  }

  const parsedStart = parseDateOnly(startIso);
  const current = new Date(parsedStart.year, parsedStart.month - 1, parsedStart.day, 12, 0, 0, 0);
  const out = [];
  let topicIndex = 0;

  while (topicIndex < topics.length) {
    const weekday = (current.getDay() + 6) % 7;
    if (learningDays.has(weekday)) {
      const row = topics[topicIndex];
      const slot = byDay.get(weekday);
      const dateIso = `${current.getFullYear()}-${String(current.getMonth() + 1).padStart(2, "0")}-${String(current.getDate()).padStart(2, "0")}`;
      const { hour, minute } = parseHhMm(slot.time);
      const scheduledDate =
        localDatetimeToUtcNaive(dateIso, slot.time, timezone) ||
        new Date(current.getFullYear(), current.getMonth(), current.getDate(), hour, minute, 0, 0);

      out.push({
        order: Number(row.order || topicIndex + 1),
        title: String(row.title || ""),
        resources: normalizeResources(row.resources),
        scheduled_date: scheduledDate,
        duration_minutes: slot.duration_minutes,
      });
      topicIndex += 1;
    }
    current.setDate(current.getDate() + 1);
  }

  return out;
};

const resolveReminderMinutes = (settings) => {
  const raw = settings?.default_learning_reminder_minutes;
  const parsed = Number.parseInt(String(raw ?? DEFAULT_LEARNING_REMINDER_MINUTES), 10);
  if (!Number.isFinite(parsed)) {
    return DEFAULT_LEARNING_REMINDER_MINUTES;
  }
  return Math.max(5, Math.min(parsed, 1440));
};

const ensureLearningSchedule = async (settings) => {
  const schedules = Array.isArray(settings.preferred_learning_schedules)
    ? settings.preferred_learning_schedules
    : [];

  if (schedules.length > 0) {
    return { settings, schedules, createdSchedule: false };
  }

  settings.preferred_learning_schedules = [DEFAULT_LEARNING_SCHEDULE];
  await settings.save();

  return {
    settings,
    schedules: settings.preferred_learning_schedules,
    createdSchedule: true,
  };
};

const pickSchedule = (schedules, scheduleId) => {
  if (!schedules.length) {
    return null;
  }
  if (scheduleId) {
    return schedules.find((entry) => String(entry.id) === scheduleId) || null;
  }
  return schedules[0];
};

const getRoadmapTopics = async (language, level) => {
  const collection = mongoose.connection.collection("roadmap_resources");
  return collection
    .find({ language, level })
    .sort({ order: 1 })
    .toArray();
};

const ensureRoadmapTemplates = async (shouldSeed) => {
  const collection = mongoose.connection.collection("roadmap_resources");
  const count = await collection.countDocuments();
  if (count > 0) {
    return { seeded: false, count };
  }

  if (!shouldSeed) {
    throw new Error(
      "roadmap_resources is empty. Run `npm run seed:roadmaps` first or pass --seed-roadmaps.",
    );
  }

  const jsonPath = resolveRoadmapsJsonPath(null);
  const data = loadRoadmapsJson(jsonPath);
  const result = await seedFromRoadmapsJson(data);
  return { seeded: true, count: result.expected, ...result };
};

/** Demo seed: fill Python basics resources; keep JavaScript/SQL basics empty. */
const applyPythonOnlyDemoResources = async () => {
  const collection = mongoose.connection.collection("roadmap_resources");
  const now = new Date();

  const pythonResult = await collection.updateMany(
    { language: "Python", level: "basics" },
    {
      $set: {
        resources: DEMO_YOUTUBE_RESOURCES,
        fetched_at: now,
        updated_at: now,
      },
    },
  );

  const clearedResult = await collection.updateMany(
    { language: { $in: ["JavaScript", "SQL"] }, level: "basics" },
    {
      $set: {
        resources: [],
        fetched_at: null,
        updated_at: now,
      },
    },
  );

  console.log(
    `Demo resources: Python basics ${pythonResult.modifiedCount} row(s) updated; JS/SQL basics cleared ${clearedResult.modifiedCount} row(s).`,
  );
};

const removeConflictingGoals = async (userId, subject) => {
  const goals = await LearningGoal.find({
    user_id: userId,
    subject: subject.toLowerCase(),
    status: { $in: ["active", "paused"] },
    is_deleted: false,
  }).select("_id");

  if (!goals.length) {
    return 0;
  }

  const now = new Date();
  const goalIds = goals.map((goal) => goal._id);

  await LearningGoal.updateMany(
    { _id: { $in: goalIds } },
    {
      $set: {
        is_deleted: true,
        deleted_at: now,
        status: "cancelled",
        updated_at: now,
      },
    },
  );

  await RoadmapTopic.updateMany(
    { goal_id: { $in: goalIds }, is_deleted: false },
    { $set: { is_deleted: true, deleted_at: now, updated_at: now } },
  );

  await Task.updateMany(
    { learning_plan_id: { $in: goalIds }, is_deleted: false },
    { $set: { is_deleted: true, deleted_at: now, updated_at: now } },
  );

  return goalIds.length;
};

const createLearningPlan = async (options, shared = {}) => {
  const {
    email,
    topic,
    level,
    days,
    start,
    scheduleId,
    replace,
    seedRoadmaps,
  } = options;

  if (!Number.isInteger(days) || days < 7) {
    throw new Error("--days must be an integer of at least 7");
  }

  let shouldDisconnect = false;
  if (!shared.connected) {
    const connected = await connectDB();
    if (!connected) {
      throw new Error("MongoDB connection failed");
    }
    shouldDisconnect = true;
  }

  try {
    if (!shared.templateChecked) {
      const templateInfo = await ensureRoadmapTemplates(seedRoadmaps);
      if (templateInfo.seeded) {
        console.log(
          `Seeded roadmap_resources: inserted ${templateInfo.inserted}, skipped ${templateInfo.skipped}`,
        );
      }
      shared.templateChecked = true;
    }

    if (options.pythonResources && !shared.pythonResourcesApplied) {
      await applyPythonOnlyDemoResources();
      shared.pythonResourcesApplied = true;
    }

    let user = shared.user;
    if (!user) {
      user = await User.findOne({ email });
      if (!user) {
        throw new Error(
          `User not found for ${email}. Run node scripts/seed-areej-user.js first or register the user.`,
        );
      }
      shared.user = user;
    }

    let settings = shared.settings;
    if (!settings) {
      settings = await UserSetting.findOne({ user_id: user._id });
      if (!settings) {
        settings = await UserSetting.createDefaultSettings(user._id);
      }

      const scheduleState = await ensureLearningSchedule(settings);
      settings = scheduleState.settings;
      shared.settings = settings;
      if (scheduleState.createdSchedule) {
        console.log(`Added default learning schedule: ${DEFAULT_LEARNING_SCHEDULE.label}`);
      }
    }

    const schedules = Array.isArray(settings.preferred_learning_schedules)
      ? settings.preferred_learning_schedules
      : [];
    const chosenSchedule = pickSchedule(schedules, scheduleId);
    if (!chosenSchedule) {
      throw new Error(
        scheduleId
          ? `Learning schedule id "${scheduleId}" not found on this user.`
          : "No learning schedule available for this user.",
      );
    }

    const scheduleSlots = Array.isArray(chosenSchedule.slots) ? chosenSchedule.slots : [];
    const learningDays = learningDaysFromSlots(scheduleSlots);
    if (!learningDays.size) {
      throw new Error("Chosen learning schedule has no slots.");
    }

    const timezone = user.timezone || "UTC";
    const startDate = resolveStartDate(start, timezone);
    const topicsDb = await getRoadmapTopics(topic, level);
    if (!topicsDb.length) {
      throw new Error(
        `No roadmap_resources rows for language="${topic}" level="${level}". Check seed:roadmaps and topic/level names.`,
      );
    }

    const available = calculateAvailableSessions(startDate, days, learningDays);
    if (available < topicsDb.length) {
      throw new Error(
        `In ${days} days this schedule only has ${available} learning slot(s), but ${topic} ${level} needs ${topicsDb.length}. Increase --days or add more learning days in Settings.`,
      );
    }

    const conflicting = await LearningGoal.findOne({
      user_id: user._id,
      subject: topic.toLowerCase(),
      status: { $in: ["active", "paused"] },
      is_deleted: false,
    });

    if (conflicting && !replace) {
      throw new Error(
        `User already has an active/paused ${topic} learning goal (${conflicting._id}). Pass --replace to cancel it and create a new plan.`,
      );
    }

    if (replace) {
      const removed = await removeConflictingGoals(user._id, topic);
      if (removed > 0) {
        console.log(`Removed ${removed} existing in-progress ${topic} goal(s).`);
      }
    }

    const scheduledRows = buildSchedule(startDate, topicsDb, scheduleSlots, timezone);
    if (scheduledRows.length !== topicsDb.length) {
      throw new Error(
        `Could only schedule ${scheduledRows.length}/${topicsDb.length} sessions. Extend --days or adjust the learning schedule.`,
      );
    }

    const lastSession = scheduledRows[scheduledRows.length - 1].scheduled_date;
    const endDate = lastSession instanceof Date ? lastSession : dateOnlyToMidnight(startDate);
    const title =
      level && level !== "general" ? `Learn ${topic} — ${level}` : `Learn ${topic}`;
    const now = new Date();
    const reminderMinutes = resolveReminderMinutes(settings);

    const goal = await LearningGoal.create({
      user_id: user._id,
      title,
      description: null,
      subject: topic.toLowerCase(),
      roadmap_key: level,
      learning_schedule_id: String(chosenSchedule.id || ""),
      start_date: dateOnlyToMidnight(startDate),
      end_date: dateOnlyToMidnight(
        `${endDate.getFullYear()}-${String(endDate.getMonth() + 1).padStart(2, "0")}-${String(endDate.getDate()).padStart(2, "0")}`,
      ),
      duration_days: days,
      total_topics: topicsDb.length,
      completed_topics: 0,
      status: "active",
      collaborators: [],
      generated_by: "eva",
      is_deleted: false,
    });

    const topicDocs = [];
    for (let idx = 0; idx < scheduledRows.length; idx += 1) {
      const row = scheduledRows[idx];
      topicDocs.push({
        goal_id: goal._id,
        order: Number(row.order || idx + 1),
        title: String(row.title || ""),
        resources: row.resources,
        scheduled_date: row.scheduled_date,
        estimated_duration: Number(row.duration_minutes || DEFAULT_DURATION_MINUTES),
        status: "pending",
        is_deleted: false,
      });
    }

    const insertedTopics = await RoadmapTopic.insertMany(topicDocs);
    const tasks = [];

    for (let idx = 0; idx < scheduledRows.length; idx += 1) {
      const row = scheduledRows[idx];
      const topicDoc = insertedTopics[idx];
      const taskTitle = `Learn: ${String(row.title || `Session ${idx + 1}`)}`.slice(0, 200);

      const task = await Task.create({
        owner_id: user._id,
        title: taskTitle,
        due_datetime: row.scheduled_date,
        duration: Number(row.duration_minutes || DEFAULT_DURATION_MINUTES),
        priority: "medium",
        status: "pending",
        source: "eva",
        scheduled_by: "manual",
        collaborators: [],
        learning_plan_id: goal._id,
        learning_topic_id: topicDoc._id,
        reminder_minutes_before: reminderMinutes,
        is_deleted: false,
      });

      topicDoc.task_id = task._id;
      await topicDoc.save();
      tasks.push(task);
    }

    console.log("Learning plan seeded (chat-equivalent).");
    console.log(`  User:      ${email}`);
    console.log(`  Goal:      ${goal.title} (${goal._id})`);
    console.log(`  Topic:     ${topic} / ${level}`);
    console.log(`  Start:     ${startDate}`);
    console.log(`  Duration:  ${days} days`);
    console.log(`  Schedule:  ${chosenSchedule.label} (${chosenSchedule.id})`);
    console.log(`  Sessions:  ${insertedTopics.length}`);
    console.log(`  Tasks:     ${tasks.length}`);
    console.log("  First sessions:");
    tasks.slice(0, 3).forEach((task) => {
      console.log(`    - ${task.title}: ${task.due_datetime.toISOString()}`);
    });

    return {
      goalId: String(goal._id),
      title: goal.title,
      topic,
      level,
      sessions: insertedTopics.length,
      tasks: tasks.length,
    };
  } finally {
    if (shouldDisconnect) {
      await disconnectDB();
    }
  }
};

const main = async () => {
  const options = parseArgs();
  const plans = resolvePlansToSeed(options);

  const connected = await connectDB();
  if (!connected) {
    throw new Error("MongoDB connection failed");
  }

  try {
    const results = [];
    const shared = { connected: true };

    for (const plan of plans) {
      const result = await createLearningPlan(
        { ...options, topic: plan.topic, level: plan.level },
        shared,
      );
      results.push(result);
      if (plans.length > 1) {
        console.log("");
      }
    }

    if (plans.length > 1) {
      console.log(`Seeded ${results.length} learning plan(s) for ${options.email}:`);
      results.forEach((row) => {
        console.log(`  - ${row.topic} / ${row.level}: ${row.sessions} sessions (${row.goalId})`);
      });
    }
  } finally {
    await disconnectDB();
  }
};

if (require.main === module) {
  main().catch((error) => {
    console.error("Seed failed:", error.message);
    process.exit(1);
  });
}

module.exports = { createLearningPlan, buildSchedule };

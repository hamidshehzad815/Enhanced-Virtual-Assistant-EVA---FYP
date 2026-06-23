/**
 * Seed script: verified user + sample tasks (today and upcoming days).
 *
 * Usage (from Eva_Backend_Server):
 *   node scripts/seed-areej-user.js
 */

const path = require("path");
require("dotenv").config({ path: path.join(__dirname, "..", ".env") });

const { connectDB, disconnectDB } = require("../config/db");
const { User, UserSetting, Task } = require("../models");

const SEED_EMAIL = "areejFatima@gmail.com";
const SEED_PASSWORD = "areejFatima@1234";
const SEED_NAME = "Areej Fatima";
const SEED_USERNAME = "areej_fatima";
const SEED_TIMEZONE = "Asia/Karachi";

const makeDueDate = (dayOffset, hour, minute = 0) => {
  const base = new Date();
  base.setHours(0, 0, 0, 0);
  base.setDate(base.getDate() + dayOffset);
  base.setHours(hour, minute, 0, 0);
  return base;
};

const buildTaskSeed = () => [
  {
    title: "Review lecture notes",
    description: "Go through today's CS lecture slides",
    dayOffset: 0,
    hour: 9,
    minute: 30,
    duration: 60,
    priority: "medium",
    status: "pending",
  },
  {
    title: "Submit lab report",
    description: "Finalize and upload the weekly lab report",
    dayOffset: 0,
    hour: 14,
    minute: 0,
    duration: 90,
    priority: "high",
    status: "pending",
  },
  {
    title: "Group project meetings",
    description: "Sync with team on FYP progress",
    dayOffset: 0,
    hour: 18,
    minute: 0,
    duration: 120,
    priority: "high",
    status: "pending",
  },
  {
    title: "Practice coding problems",
    description: "Solve 3 LeetCode medium problems",
    dayOffset: 1,
    hour: 10,
    minute: 0,
    duration: 120,
    priority: "medium",
    status: "pending",
  },
  {
    title: "Read research paper",
    description: "Summarize key points for tomorrow's class",
    dayOffset: 1,
    hour: 16,
    minute: 30,
    duration: 60,
    priority: "low",
    status: "pending",
  },
  {
    title: "Midterm revision - OOP",
    description: "Revise inheritance and polymorphism topics",
    dayOffset: 2,
    hour: 11,
    minute: 0,
    duration: 150,
    priority: "high",
    status: "pending",
  },
  {
    title: "Database assignment",
    description: "Complete normalization exercises",
    dayOffset: 2,
    hour: 19,
    minute: 0,
    duration: 120,
    priority: "medium",
    status: "pending",
  },
  {
    title: "Mock quiz",
    description: "Timed practice quiz for upcoming test",
    dayOffset: 3,
    hour: 15,
    minute: 0,
    duration: 45,
    priority: "medium",
    status: "pending",
  },
  {
    title: "Presentation prep",
    description: "Prepare slides for seminar next week",
    dayOffset: 7,
    hour: 13,
    minute: 0,
    duration: 180,
    priority: "high",
    status: "pending",
  },
];

const seed = async () => {
  if (!process.env.MONGODB_URI) {
    console.error("MONGODB_URI is not set in .env");
    process.exit(1);
  }

  const connected = await connectDB();
  if (!connected) {
    console.error("Failed to connect to MongoDB");
    process.exit(1);
  }

  const email = SEED_EMAIL.toLowerCase();
  let user = await User.findOne({ email });

  if (user) {
    user.name = SEED_NAME;
    user.username = SEED_USERNAME;
    user.password_hash = SEED_PASSWORD;
    user.timezone = SEED_TIMEZONE;
    user.is_verified = true;
    user.is_active = true;
    user.auth_provider = "local";
    user.email_verification_token = undefined;
    user.email_verification_expires = undefined;
    await user.save();
    console.log(`Updated existing user: ${email}`);
  } else {
    user = await User.create({
      name: SEED_NAME,
      username: SEED_USERNAME,
      email,
      password_hash: SEED_PASSWORD,
      timezone: SEED_TIMEZONE,
      auth_provider: "local",
      is_verified: true,
      is_active: true,
    });
    await UserSetting.createDefaultSettings(user._id);
    console.log(`Created user: ${email}`);
  }

  const removed = await Task.deleteMany({
    owner_id: user._id,
    source: "manual",
    scheduled_by: "manual",
  });

  const taskDocs = buildTaskSeed().map(
    ({ dayOffset, hour, minute, ...task }) => ({
      owner_id: user._id,
      title: task.title,
      description: task.description,
      due_datetime: makeDueDate(dayOffset, hour, minute),
      duration: task.duration,
      priority: task.priority,
      status: task.status,
      source: "manual",
      scheduled_by: "manual",
      is_deleted: false,
    }),
  );

  const inserted = await Task.insertMany(taskDocs);

  console.log("Seed complete.");
  console.log(`  Email:    ${email}`);
  console.log(`  Password: ${SEED_PASSWORD}`);
  console.log(`  Verified: true`);
  console.log(`  Removed old manual tasks: ${removed.deletedCount}`);
  console.log(`  Inserted tasks: ${inserted.length}`);
  console.log("  Task dates (local machine time):");
  inserted.forEach((task) => {
    console.log(`    - ${task.title}: ${task.due_datetime.toISOString()}`);
  });

  await disconnectDB();
  process.exit(0);
};

seed().catch(async (error) => {
  console.error("Seed failed:", error.message);
  await disconnectDB();
  process.exit(1);
});

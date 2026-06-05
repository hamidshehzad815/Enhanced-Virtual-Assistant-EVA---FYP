/**
 * Reminder Job (Phase 12)
 * - Runs every minute
 * - Sends task reminders at due_datetime - reminder_minutes_before
 * - Sends overdue alerts once when due_datetime passes
 */

const cron = require("node-cron");

const logger = require("../config/logger");
const { Task, User, LearningGoal } = require("../models");
const { insert_and_dispatch } = require("../services/notification.service");
const { formatDateInTimezone, resolveTimezone } = require("../utils/timezone");

let activeJob = null;
let isRunning = false;

const DEFAULT_REMINDER_MINUTES = 30;

const toDate = (value) => {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};

const formatDue = (dueDate, timezoneValue = "UTC") => {
  return formatDateInTimezone(dueDate, timezoneValue);
};

const buildReminderNotification = (task, timezoneValue) => ({
  user_id: String(task.owner_id),
  sender_id: null,
  type: "task_reminder",
  reference_type: "task",
  reference_id: String(task._id),
  title: "Task reminder",
  message: `Reminder: ${task.title} is coming up at ${formatDue(task.due_datetime, timezoneValue)}.`,
  action_required: false,
  delivery_channel: ["push", "in_app", "email"],
  scheduled_at: new Date(),
});

const buildLearningTopicReminderPayload = (task, timezoneValue, planTitle) => {
  const when = formatDue(task.due_datetime, timezoneValue);
  const plan = planTitle ? `"${planTitle}"` : "Your learning plan";
  return {
    user_id: String(task.owner_id),
    sender_id: null,
    type: "topic_reminder",
    reference_type: "topic",
    reference_id: String(task.learning_topic_id),
    title: "Learning session reminder",
    message: `${plan} — ${task.title} is coming up at ${when}. Mark complete when you finish.`,
    action_required: true,
    delivery_channel: ["push", "in_app", "email"],
    scheduled_at: new Date(),
    push_data: {
      learning_goal_id: String(task.learning_plan_id),
      learning_topic_id: String(task.learning_topic_id),
      suggested_action: "complete_learning_topic",
    },
  };
};

const buildLearningOverduePayload = (task, timezoneValue, planTitle) => {
  const when = formatDue(task.due_datetime, timezoneValue);
  const plan = planTitle ? `"${planTitle}"` : "Your learning plan";
  return {
    user_id: String(task.owner_id),
    sender_id: null,
    type: "topic_reminder",
    reference_type: "topic",
    reference_id: String(task.learning_topic_id),
    title: "Learning session overdue",
    message: `${plan} — ${task.title} was scheduled for ${when}. Mark it complete or it will be auto-completed soon.`,
    action_required: true,
    delivery_channel: ["push", "in_app", "email"],
    scheduled_at: new Date(),
    push_data: {
      learning_goal_id: String(task.learning_plan_id),
      learning_topic_id: String(task.learning_topic_id),
      suggested_action: "complete_learning_topic",
    },
  };
};

const buildOverdueNotification = (task, timezoneValue) => ({
  user_id: String(task.owner_id),
  sender_id: null,
  type: "overdue_alert",
  reference_type: "task",
  reference_id: String(task._id),
  title: "Task overdue",
  message: `Overdue: ${task.title} was due at ${formatDue(task.due_datetime, timezoneValue)}.`,
  action_required: true,
  delivery_channel: ["push", "in_app", "email"],
  scheduled_at: new Date(),
});

const loadUserTimezones = async (ownerIds) => {
  if (!ownerIds.length) {
    return new Map();
  }

  const users = await User.find(
    { _id: { $in: ownerIds } },
    { _id: 1, timezone: 1 },
  ).lean();

  const timezoneByUserId = new Map();
  users.forEach((user) => {
    const userId = String(user._id);
    timezoneByUserId.set(userId, resolveTimezone(user.timezone));
  });

  return timezoneByUserId;
};

const sendReminderNotifications = async (now) => {
  const pendingTasks = await Task.find({
    status: "pending",
    is_deleted: false,
    reminder_sent_at: null,
  })
    .select(
      "_id owner_id title due_datetime reminder_minutes_before learning_plan_id learning_topic_id",
    )
    .lean();

  if (!pendingTasks.length) {
    return { checked: 0, sentFor: 0 };
  }

  // 60s window to avoid missing jobs due to minor scheduler drift.
  const windowStart = new Date(now.getTime() - 60 * 1000);
  const windowEnd = new Date(now.getTime() + 60 * 1000);

  const dueForReminder = pendingTasks.filter((task) => {
    const dueDate = toDate(task.due_datetime);
    if (!dueDate) {
      return false;
    }

    const mins = Number.isFinite(task.reminder_minutes_before)
      ? task.reminder_minutes_before
      : DEFAULT_REMINDER_MINUTES;
    const reminderAt = new Date(dueDate.getTime() - mins * 60 * 1000);

    return reminderAt > windowStart && reminderAt <= windowEnd;
  });

  if (!dueForReminder.length) {
    return { checked: pendingTasks.length, sentFor: 0 };
  }

  const ownerIds = [
    ...new Set(dueForReminder.map((task) => String(task.owner_id))),
  ];
  const timezoneByUserId = await loadUserTimezones(ownerIds);

  const learningPlanIds = [
    ...new Set(
      dueForReminder
        .filter((t) => t.learning_topic_id && t.learning_plan_id)
        .map((t) => String(t.learning_plan_id)),
    ),
  ];
  let titleByPlanId = new Map();
  if (learningPlanIds.length) {
    const goals = await LearningGoal.find({
      _id: { $in: learningPlanIds },
    })
      .select("title")
      .lean();
    titleByPlanId = new Map(goals.map((g) => [String(g._id), g.title]));
  }

  const payloads = dueForReminder.map((task) => {
    const tz = timezoneByUserId.get(String(task.owner_id)) || "UTC";
    if (task.learning_topic_id && task.learning_plan_id) {
      const planTitle = titleByPlanId.get(String(task.learning_plan_id)) || "";
      return buildLearningTopicReminderPayload(task, tz, planTitle);
    }
    return buildReminderNotification(task, tz);
  });
  const summary = await insert_and_dispatch(payloads);

  await Task.updateMany(
    { _id: { $in: dueForReminder.map((task) => task._id) } },
    {
      $set: {
        reminder_sent_at: now,
        updated_at: now,
      },
    },
  );

  logger.info("Reminder job: task reminders processed", {
    checked_tasks: pendingTasks.length,
    due_for_reminder: dueForReminder.length,
    notification_requested: summary.requested,
    notification_inserted: summary.inserted,
    notification_failed: summary.failed,
  });

  return { checked: pendingTasks.length, sentFor: dueForReminder.length };
};

const sendOverdueAlerts = async (now) => {
  const overdueTasks = await Task.find({
    status: "pending",
    is_deleted: false,
    overdue_notified_at: null,
    learning_topic_id: null,
    due_datetime: { $lte: now },
  })
    .select("_id owner_id title due_datetime")
    .lean();

  if (!overdueTasks.length) {
    return { sentFor: 0 };
  }

  const ownerIds = [
    ...new Set(overdueTasks.map((task) => String(task.owner_id))),
  ];
  const timezoneByUserId = await loadUserTimezones(ownerIds);
  const payloads = overdueTasks.map((task) =>
    buildOverdueNotification(
      task,
      timezoneByUserId.get(String(task.owner_id)) || "UTC",
    ),
  );
  const summary = await insert_and_dispatch(payloads);

  await Task.updateMany(
    { _id: { $in: overdueTasks.map((task) => task._id) } },
    {
      $set: {
        overdue_notified_at: now,
        updated_at: now,
      },
    },
  );

  logger.info("Reminder job: overdue alerts processed", {
    overdue_tasks: overdueTasks.length,
    notification_requested: summary.requested,
    notification_inserted: summary.inserted,
    notification_failed: summary.failed,
  });

  return { sentFor: overdueTasks.length };
};

const sendLearningOverdueAlerts = async (now) => {
  const overdueLearningTasks = await Task.find({
    status: "pending",
    is_deleted: false,
    overdue_notified_at: null,
    learning_plan_id: { $ne: null },
    learning_topic_id: { $ne: null },
    due_datetime: { $lte: now },
  })
    .select("_id owner_id title due_datetime learning_plan_id learning_topic_id")
    .lean();

  if (!overdueLearningTasks.length) {
    return { sentFor: 0 };
  }

  const planIds = [
    ...new Set(overdueLearningTasks.map((task) => String(task.learning_plan_id))),
  ];
  const plans = await LearningGoal.find(
    { _id: { $in: planIds }, status: "active", is_deleted: false },
    { _id: 1, title: 1 },
  ).lean();
  const planById = new Map(plans.map((p) => [String(p._id), p]));

  const activeOnly = overdueLearningTasks.filter((t) =>
    planById.has(String(t.learning_plan_id)),
  );
  if (!activeOnly.length) {
    return { sentFor: 0 };
  }

  const ownerIds = [...new Set(activeOnly.map((task) => String(task.owner_id)))];
  const timezoneByUserId = await loadUserTimezones(ownerIds);

  const payloads = activeOnly.map((task) => {
    const tz = timezoneByUserId.get(String(task.owner_id)) || "UTC";
    const plan = planById.get(String(task.learning_plan_id));
    return buildLearningOverduePayload(task, tz, plan?.title || null);
  });

  const summary = await insert_and_dispatch(payloads);

  await Task.updateMany(
    { _id: { $in: activeOnly.map((task) => task._id) } },
    { $set: { overdue_notified_at: now, updated_at: now } },
  );

  logger.info("Reminder job: learning overdue alerts processed", {
    overdue_learning_tasks: activeOnly.length,
    notification_requested: summary.requested,
    notification_inserted: summary.inserted,
    notification_failed: summary.failed,
  });

  return { sentFor: activeOnly.length };
};

const runReminderCycle = async () => {
  if (isRunning) {
    logger.warn("Reminder job skipped because previous cycle is still running");
    return;
  }

  isRunning = true;

  try {
    const now = new Date();
    await sendReminderNotifications(now);
    await sendLearningOverdueAlerts(now);
    await sendOverdueAlerts(now);
  } catch (error) {
    logger.error("Reminder job cycle failed", { error: error.message });
  } finally {
    isRunning = false;
  }
};

const startReminderJob = () => {
  if (activeJob) {
    return activeJob;
  }

  activeJob = cron.schedule("* * * * *", runReminderCycle, {
    scheduled: true,
  });

  logger.info("Reminder job started (every minute)");
  return activeJob;
};

const stopReminderJob = () => {
  if (!activeJob) {
    return;
  }

  activeJob.stop();
  activeJob = null;
  logger.info("Reminder job stopped");
};

module.exports = {
  runReminderCycle,
  startReminderJob,
  stopReminderJob,
  sendReminderNotifications,
  sendOverdueAlerts,
  sendLearningOverdueAlerts,
};

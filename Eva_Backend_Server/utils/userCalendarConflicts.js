/**
 * Task + learning-schedule conflict checks for any user (e.g. collaborators).
 */

const { Task, User, UserSetting } = require("../models");
const {
  findTaskConflictsWithLearningSchedules,
} = require("./learningScheduleConflict");
const { getSchedulesFromSettingsDoc } = require("./learningSchedules");

const DEFAULT_TASK_DURATION = 120;

function taskWindowsOverlap(existingStart, existingDuration, newStart, newDuration) {
  const existingDur = Math.max(1, Number(existingDuration) || DEFAULT_TASK_DURATION);
  const newDur = Math.max(1, Number(newDuration) || DEFAULT_TASK_DURATION);
  const existingEnd = new Date(existingStart.getTime() + existingDur * 60000);
  const newEnd = new Date(newStart.getTime() + newDur * 60000);
  return existingStart < newEnd && existingEnd > newStart;
}

async function findOverlappingTaskForUser(userId, dueDate, durationMinutes) {
  const newDur = Math.max(1, Number(durationMinutes) || DEFAULT_TASK_DURATION);
  const newStart = new Date(dueDate);
  const newEnd = new Date(newStart.getTime() + newDur * 60000);
  const searchStart = new Date(newStart.getTime() - 24 * 60 * 60000);

  const tasks = await Task.find({
    is_deleted: { $ne: true },
    due_datetime: { $gte: searchStart, $lt: newEnd },
    $or: [
      { owner_id: userId },
      {
        collaborators: {
          $elemMatch: {
            user_id: userId,
            status: "accepted",
          },
        },
      },
    ],
  })
    .select("_id title due_datetime duration")
    .lean();

  for (const task of tasks) {
    if (!task.due_datetime) {
      continue;
    }
    const existingStart = new Date(task.due_datetime);
    if (taskWindowsOverlap(existingStart, task.duration, newStart, newDur)) {
      return task;
    }
  }
  return null;
}

async function resolveUserTimezone(userId) {
  const user = await User.findById(userId).select("timezone").lean();
  const tz = user && user.timezone ? String(user.timezone).trim() : "";
  return tz || "UTC";
}

async function findUserCalendarConflicts(userId, dueDate, durationMinutes, timeZone) {
  const tz = timeZone || (await resolveUserTimezone(userId));
  const dur = Math.max(1, Number(durationMinutes) || DEFAULT_TASK_DURATION);

  const overlapTask = await findOverlappingTaskForUser(userId, dueDate, dur);
  if (overlapTask) {
    return {
      kind: "task",
      title: overlapTask.title || "another task",
      task_id: String(overlapTask._id),
    };
  }

  const settingsDoc = await UserSetting.findOne({ user_id: userId }).lean();
  const schedules = getSchedulesFromSettingsDoc(settingsDoc || {});
  const scheduleConflicts = findTaskConflictsWithLearningSchedules(
    new Date(dueDate),
    dur,
    schedules,
    tz,
  );
  if (scheduleConflicts.length > 0) {
    const first = scheduleConflicts[0];
    return {
      kind: "learning_schedule",
      schedule_label: first.schedule_label,
      slot: first.slot,
      conflicts: scheduleConflicts,
    };
  }

  return null;
}

function formatCollaboratorConflictMessage(collaboratorName, conflict, { forLearningPlan = false } = {}) {
  const name = (collaboratorName || "Your collaborator").trim();
  if (conflict.kind === "task") {
    const title = conflict.title || "another task";
    if (forLearningPlan) {
      return (
        `${name} already has “${title}” scheduled when a lesson in this plan would run. `
        + "Pick different plan dates, remove that collaborator, or ask them to free that time."
      );
    }
    return (
      `${name} is busy — they already have “${title}” at that time. `
      + "Please choose a different time."
    );
  }

  const label = conflict.schedule_label || "a learning schedule";
  const dayNames = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
  ];
  const dayI = Number((conflict.slot && conflict.slot.day) || 0);
  const dayName = dayNames[dayI] || `day ${dayI}`;
  const timeS = (conflict.slot && conflict.slot.time) || "";
  if (forLearningPlan) {
    return (
      `${name} has learning time reserved on ${dayName} ${timeS} (“${label}”), `
      + "which clashes with a lesson in this plan. "
      + "Adjust the plan, remove that collaborator, or ask them to change their learning schedule."
    );
  }
  return (
    `${name} has learning time reserved on ${dayName} ${timeS} (“${label}”). `
    + "Please choose a different time for this task."
  );
}

module.exports = {
  findUserCalendarConflicts,
  findOverlappingTaskForUser,
  formatCollaboratorConflictMessage,
  resolveUserTimezone,
  taskWindowsOverlap,
};

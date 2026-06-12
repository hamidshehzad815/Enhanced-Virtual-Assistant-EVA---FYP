/**
 * Task display status (UI) vs stored status (DB).
 * DB: pending | complete only (legacy "ongoing" treated as pending).
 * UI: pending | ongoing | overdue | complete — derived from time window.
 */

const DEFAULT_DURATION_MINUTES = 120;

const isStoredComplete = (status) => {
  const normalized = String(status || "").trim().toLowerCase();
  return normalized === "complete" || normalized === "completed";
};

const normalizeStoredStatus = (status) =>
  (isStoredComplete(status) ? "complete" : "pending");

const toDateOrNull = (value) => {
  if (!value) {
    return null;
  }
  const parsed = value instanceof Date ? value : new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};

const taskWindowEnd = (dueDatetime, durationMinutes) => {
  const start = toDateOrNull(dueDatetime);
  if (!start) {
    return null;
  }
  const parsedDuration = Number(durationMinutes);
  const duration = Number.isFinite(parsedDuration) && parsedDuration > 0
    ? parsedDuration
    : DEFAULT_DURATION_MINUTES;
  return new Date(start.getTime() + duration * 60 * 1000);
};

/**
 * @returns {"pending"|"ongoing"|"overdue"|"complete"}
 */
const computeTaskDisplayStatus = (task, now = new Date()) => {
  if (isStoredComplete(task?.status)) {
    return "complete";
  }

  const start = toDateOrNull(task?.due_datetime);
  if (!start) {
    return "pending";
  }

  const end = taskWindowEnd(start, task?.duration) || start;
  const nowMs = now.getTime();

  if (nowMs < start.getTime()) {
    return "pending";
  }
  if (nowMs < end.getTime()) {
    return "ongoing";
  }
  return "overdue";
};

const { localizeApiPayload } = require("./apiDateTime");

/**
 * Public task shape for tasks page / detail (no internal DB fields).
 */
const serializeTaskForApi = (
  task,
  now = new Date(),
  timezone = "UTC",
  { includeDescription = false } = {},
) => {
  if (!task || typeof task !== "object") {
    return task;
  }

  const learningGoalId = task.learning_plan_id
    ? String(task.learning_plan_id)
    : null;

  const payload = {
    id: task._id != null ? String(task._id) : String(task.id || ""),
    title: task.title,
    due_datetime: task.due_datetime,
    duration: Number.isFinite(Number(task.duration)) && Number(task.duration) > 0
      ? Number(task.duration)
      : DEFAULT_DURATION_MINUTES,
    priority: task.priority || "medium",
    status: normalizeStoredStatus(task.status),
    display_status: computeTaskDisplayStatus(task, now),
    is_learning_task: Boolean(learningGoalId),
    learning_goal_id: learningGoalId,
  };

  if (task.completed_at) {
    payload.completed_at = task.completed_at;
  }

  if (includeDescription) {
    payload.description = task.description || null;
  }

  return localizeApiPayload(payload, timezone);
};

/** @deprecated Prefer serializeTaskForApi for HTTP responses. */
const enrichTaskForApi = (task, now = new Date(), timezone = "UTC") =>
  serializeTaskForApi(task, now, timezone, { includeDescription: true });

module.exports = {
  DEFAULT_DURATION_MINUTES,
  isStoredComplete,
  normalizeStoredStatus,
  computeTaskDisplayStatus,
  serializeTaskForApi,
  enrichTaskForApi,
  taskWindowEnd,
};

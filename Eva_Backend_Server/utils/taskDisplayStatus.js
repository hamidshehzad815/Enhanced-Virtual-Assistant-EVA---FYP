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

const enrichTaskForApi = (task, now = new Date(), timezone = "UTC") => {
  if (!task || typeof task !== "object") {
    return task;
  }
  const enriched = {
    ...task,
    status: normalizeStoredStatus(task.status),
    display_status: computeTaskDisplayStatus(task, now),
  };
  return localizeApiPayload(enriched, timezone);
};

module.exports = {
  DEFAULT_DURATION_MINUTES,
  isStoredComplete,
  normalizeStoredStatus,
  computeTaskDisplayStatus,
  enrichTaskForApi,
  taskWindowEnd,
};

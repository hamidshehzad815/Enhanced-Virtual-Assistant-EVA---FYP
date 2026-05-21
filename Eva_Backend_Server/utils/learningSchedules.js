/**
 * Labeled learning schedules: [{ id, label, slots: [{ day, time, duration_minutes }] }]
 */

const crypto = require("crypto");

const TIME_PATTERN = /^([01]?[0-9]|2[0-3]):[0-5][0-9]$/;
const MIN_DURATION = 15;
const MAX_DURATION = 240;
const MAX_LABEL_LEN = 80;
const MAX_SCHEDULES = 20;

const DAY_LABELS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

const formatSlotLabel = (day, time) => {
  const name = DAY_LABELS[day] || `day ${day}`;
  return `${name} ${time}`;
};

const normalizeTime = (value, fieldName) => {
  const normalized = String(value || "").trim();
  if (!TIME_PATTERN.test(normalized)) {
    throw new Error(`${fieldName} must be in HH:mm format`);
  }
  return normalized;
};

const normalizeInteger = (value, fieldName) => {
  const parsed =
    typeof value === "number" ? value : Number.parseInt(String(value).trim(), 10);
  if (!Number.isInteger(parsed)) {
    throw new Error(`${fieldName} must be an integer`);
  }
  return parsed;
};

/**
 * Normalize slots array for a schedule.
 */
const normalizeScheduleSlots = (value, pathPrefix, defaultDurationMinutes = 90) => {
  if (!Array.isArray(value)) {
    throw new Error(`${pathPrefix} must be an array`);
  }
  if (value.length === 0) {
    throw new Error(`${pathPrefix} must include at least one day`);
  }

  const seenDays = new Set();
  return value.map((slot, index) => {
    const base = `${pathPrefix}[${index}]`;
    if (!slot || typeof slot !== "object" || Array.isArray(slot)) {
      throw new Error(`${base} must be an object with day, time, and duration_minutes`);
    }

    const day = normalizeInteger(slot.day, `${base}.day`);
    if (day < 0 || day > 6) {
      throw new Error(`${base}.day must be between 0 and 6`);
    }
    if (seenDays.has(day)) {
      throw new Error(`${pathPrefix}: duplicate day ${day}; at most one slot per weekday`);
    }
    seenDays.add(day);

    const time = normalizeTime(slot.time, `${base}.time`);
    let durationMinutes = defaultDurationMinutes;
    if (slot.duration_minutes !== undefined && slot.duration_minutes !== null) {
      durationMinutes = normalizeInteger(
        slot.duration_minutes,
        `${base}.duration_minutes`,
      );
      if (durationMinutes < MIN_DURATION || durationMinutes > MAX_DURATION) {
        throw new Error(
          `${base}.duration_minutes must be between ${MIN_DURATION} and ${MAX_DURATION}`,
        );
      }
    }

    return { day, time, duration_minutes: durationMinutes };
  });
};

/**
 * @param {unknown} value
 * @param {number} defaultDurationMinutes
 * @returns {{ id: string, label: string, slots: object[] }[]}
 */
const normalizePreferredLearningSchedules = (value, defaultDurationMinutes = 90) => {
  if (value === undefined) {
    return undefined;
  }
  if (value === null) {
    return [];
  }
  if (!Array.isArray(value)) {
    throw new Error("preferred_learning_schedules must be an array");
  }
  if (value.length > MAX_SCHEDULES) {
    throw new Error(`At most ${MAX_SCHEDULES} learning schedules are allowed`);
  }

  const seenIds = new Set();
  const seenLabels = new Set();

  const schedules = value.map((entry, index) => {
    const base = `preferred_learning_schedules[${index}]`;
    if (!entry || typeof entry !== "object" || Array.isArray(entry)) {
      throw new Error(`${base} must be an object with label and slots`);
    }

    const label = String(entry.label || "").trim();
    if (!label) {
      throw new Error(`${base}.label is required`);
    }
    if (label.length > MAX_LABEL_LEN) {
      throw new Error(`${base}.label cannot exceed ${MAX_LABEL_LEN} characters`);
    }
    const labelKey = label.toLowerCase();
    if (seenLabels.has(labelKey)) {
      throw new Error("Each learning schedule must have a unique label");
    }
    seenLabels.add(labelKey);

    let id = String(entry.id || "").trim();
    if (!id) {
      id = crypto.randomUUID();
    }
    if (seenIds.has(id)) {
      throw new Error("Each learning schedule must have a unique id");
    }
    seenIds.add(id);

    const slots = normalizeScheduleSlots(
      entry.slots,
      `${base}.slots`,
      defaultDurationMinutes,
    );

    return { id, label, slots };
  });

  assertNoDuplicateSlotsAcrossSchedules(schedules);
  return schedules;
};

/** One-time read: old Mongo docs may still have a flat slot array under this key. */
const migrateFlatSlotsFromDoc = (flatSlots, defaultDurationMinutes = 90) => {
  if (!Array.isArray(flatSlots) || flatSlots.length === 0) {
    return [];
  }
  const slots = normalizeScheduleSlots(
    flatSlots.map((s) => ({
      day: s.day,
      time: s.time,
      duration_minutes: s.duration_minutes,
    })),
    "slots",
    defaultDurationMinutes,
  );
  return [
    {
      id: "default",
      label: "Default",
      slots,
    },
  ];
};

const toPlainSchedule = (entry, defaultDur) => {
  if (!entry || typeof entry !== "object") {
    return null;
  }
  const id = String(entry.id || "").trim();
  const label = String(entry.label || "").trim();
  const rawSlots = Array.isArray(entry.slots) ? entry.slots : [];
  if (!id || !label || !rawSlots.length) {
    return null;
  }
  try {
    const slots = normalizeScheduleSlots(rawSlots, "slots", defaultDur);
    return { id, label, slots };
  } catch {
    return null;
  }
};

const normalizeSingleLearningSchedule = (
  entry,
  defaultDurationMinutes = 90,
  options = {},
) => {
  const pathPrefix = options.pathPrefix || "schedule";
  if (!entry || typeof entry !== "object" || Array.isArray(entry)) {
    throw new Error(`${pathPrefix} must be an object with label and slots`);
  }

  const label = String(entry.label || "").trim();
  if (!label) {
    throw new Error(`${pathPrefix}.label is required`);
  }
  if (label.length > MAX_LABEL_LEN) {
    throw new Error(`${pathPrefix}.label cannot exceed ${MAX_LABEL_LEN} characters`);
  }

  let id = String(entry.id || "").trim();
  if (!id) {
    if (options.allowMissingId === false) {
      throw new Error(`${pathPrefix}.id is required`);
    }
    id = crypto.randomUUID();
  }

  const slots = normalizeScheduleSlots(
    entry.slots,
    `${pathPrefix}.slots`,
    defaultDurationMinutes,
  );

  return { id, label, slots };
};

const findScheduleIndex = (schedules, scheduleId) => {
  const sid = String(scheduleId || "").trim();
  if (!sid || !Array.isArray(schedules)) {
    return -1;
  }
  return schedules.findIndex((s) => String(s?.id || "").trim() === sid);
};

/**
 * Find slots in candidateSlots that duplicate (day + time) on another schedule.
 * @param {{ day: number, time: string }[]} candidateSlots
 * @param {{ id: string, label: string, slots: object[] }[]} schedules
 * @param {string|null} excludeScheduleId schedule to skip (e.g. the one being updated)
 */
const findCrossScheduleSlotConflicts = (
  candidateSlots,
  schedules,
  excludeScheduleId = null,
) => {
  const exclude = excludeScheduleId ? String(excludeScheduleId).trim() : null;
  const conflicts = [];
  const seen = new Map();

  for (const sched of schedules || []) {
    const schedId = String(sched?.id || "").trim();
    if (exclude && schedId === exclude) {
      continue;
    }
    const schedLabel = String(sched?.label || "").trim() || schedId;
    for (const slot of sched?.slots || []) {
      const key = `${slot.day}:${slot.time}`;
      if (!seen.has(key)) {
        seen.set(key, { schedule_id: schedId, schedule_label: schedLabel, slot });
      }
    }
  }

  for (const slot of candidateSlots || []) {
    const key = `${slot.day}:${slot.time}`;
    const existing = seen.get(key);
    if (existing) {
      conflicts.push({
        slot: { day: slot.day, time: slot.time },
        conflicting_schedule: {
          id: existing.schedule_id,
          label: existing.schedule_label,
        },
      });
    }
  }

  return conflicts;
};

/**
 * Ensure no two schedules share the same weekday + start time.
 * @throws {Error}
 */
const assertNoDuplicateSlotsAcrossSchedules = (schedules) => {
  const slotOwner = new Map();

  for (const sched of schedules || []) {
    const schedId = String(sched?.id || "").trim();
    const schedLabel = String(sched?.label || "").trim() || schedId;
    for (const slot of sched?.slots || []) {
      const key = `${slot.day}:${slot.time}`;
      if (slotOwner.has(key)) {
        const prev = slotOwner.get(key);
        throw new Error(
          `${formatSlotLabel(slot.day, slot.time)} is already used in schedule "${prev.schedule_label}"; `
          + `the same weekday and start time cannot appear in more than one learning schedule (conflicts with "${schedLabel}")`,
        );
      }
      slotOwner.set(key, { schedule_id: schedId, schedule_label: schedLabel });
    }
  }
};

const crossScheduleConflictMessage = (candidateLabel, conflicts) => {
  const first = conflicts[0];
  const slotText = formatSlotLabel(first.slot.day, first.slot.time);
  const otherLabel = first.conflicting_schedule.label;
  return (
    `Learning schedule "${candidateLabel}" uses ${slotText}, which is already set in "${otherLabel}". `
    + "Use a different start time on that day, or remove the slot from the other schedule."
  );
};

const assertUniqueLabelAmong = (schedules, label, excludeId = null) => {
  const key = String(label || "").trim().toLowerCase();
  if (!key) {
    return;
  }
  const exclude = excludeId ? String(excludeId).trim() : null;
  for (const entry of schedules || []) {
    const entryId = String(entry?.id || "").trim();
    if (exclude && entryId === exclude) {
      continue;
    }
    if (String(entry?.label || "").trim().toLowerCase() === key) {
      throw new Error("Each learning schedule must have a unique label");
    }
  }
};

const applyLearningSchedules = (settings, schedules) => {
  settings.preferred_learning_schedules = Array.isArray(schedules) ? schedules : [];
};

/**
 * Read schedules from settings (supports old flat slot array still in Mongo).
 */
const getSchedulesFromSettingsDoc = (settings) => {
  const defaultDur = Number(settings?.preferred_learning_duration) || 90;
  const modern = settings?.preferred_learning_schedules;
  if (Array.isArray(modern) && modern.length > 0) {
    const out = modern
      .map((entry) => toPlainSchedule(entry, defaultDur))
      .filter(Boolean);
    if (out.length > 0) {
      return out;
    }
  }
  const orphanFlat = settings?.preferred_learning_schedule;
  if (Array.isArray(orphanFlat) && orphanFlat.length > 0) {
    return migrateFlatSlotsFromDoc(orphanFlat, defaultDur);
  }
  return [];
};

const listSchedulesFromSettings = (settings) => {
  const defaultDur = Number(settings?.preferred_learning_duration) || 90;
  const stored = Array.isArray(settings?.preferred_learning_schedules)
    ? settings.preferred_learning_schedules
    : [];
  if (stored.length > 0) {
    return stored
      .map((entry) => toPlainSchedule(entry, defaultDur))
      .filter(Boolean);
  }
  return getSchedulesFromSettingsDoc(settings);
};

module.exports = {
  MIN_DURATION,
  MAX_DURATION,
  MAX_SCHEDULES,
  DAY_LABELS,
  formatSlotLabel,
  normalizeScheduleSlots,
  normalizePreferredLearningSchedules,
  normalizeSingleLearningSchedule,
  getSchedulesFromSettingsDoc,
  listSchedulesFromSettings,
  findScheduleIndex,
  findCrossScheduleSlotConflicts,
  assertNoDuplicateSlotsAcrossSchedules,
  crossScheduleConflictMessage,
  assertUniqueLabelAmong,
  applyLearningSchedules,
};

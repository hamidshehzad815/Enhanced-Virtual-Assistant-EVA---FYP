/**
 * Calendar dates eligible for learning session reschedule for a plan.
 * Mirrors Eva_AI_Server handlers/learning/update.py reschedule weekday rules.
 */

const {
  DAY_LABELS,
  resolveLearningSlotsForGoal,
  listSchedulesFromSettings,
  findScheduleIndex,
} = require("./learningSchedules");
const {
  normalizeTimezone,
  parseDateOnly,
  toUtcFromLocalParts,
} = require("./timezone");
const { serializeInstantForApi } = require("./apiDateTime");

const DEFAULT_HORIZON_WEEKS = 12;
const MAX_HORIZON_WEEKS = 52;
const MS_PER_DAY = 86400000;

const WEEKDAY_SHORT_TO_MON0 = {
  Mon: 0,
  Tue: 1,
  Wed: 2,
  Thu: 3,
  Fri: 4,
  Sat: 5,
  Sun: 6,
};

const toLocalDateString = (timeZone, dateValue = new Date()) => {
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
  const parts = formatter.formatToParts(dateValue);
  const partMap = {};
  parts.forEach((part) => {
    if (part.type !== "literal") {
      partMap[part.type] = part.value;
    }
  });
  return `${partMap.year}-${partMap.month}-${partMap.day}`;
};

const localWeekdayMon0 = (dateStr, timeZone) => {
  const parsed = parseDateOnly(dateStr);
  if (!parsed) {
    return null;
  }
  const utc = toUtcFromLocalParts(
    parsed.year,
    parsed.month,
    parsed.day,
    12,
    0,
    0,
    timeZone,
  );
  const shortDay = new Intl.DateTimeFormat("en-US", {
    timeZone,
    weekday: "short",
  }).format(utc);
  return WEEKDAY_SHORT_TO_MON0[shortDay.slice(0, 3)] ?? null;
};

const addLocalDays = (dateStr, days, timeZone) => {
  const parsed = parseDateOnly(dateStr);
  if (!parsed) {
    return null;
  }
  const utc = toUtcFromLocalParts(
    parsed.year,
    parsed.month,
    parsed.day,
    12,
    0,
    0,
    timeZone,
  );
  return toLocalDateString(timeZone, new Date(utc.getTime() + days * MS_PER_DAY));
};

const parseSlotTime = (timeValue) => {
  const match = String(timeValue || "")
    .trim()
    .match(/^(\d{1,2}):(\d{2})$/);
  if (!match) {
    return { hour: 18, minute: 0 };
  }
  return {
    hour: Number.parseInt(match[1], 10),
    minute: Number.parseInt(match[2], 10),
  };
};

const slotsByWeekday = (slots) => {
  const map = new Map();
  (slots || []).forEach((slot) => {
    const day = Number(slot?.day);
    if (!Number.isInteger(day) || day < 0 || day > 6) {
      return;
    }
    map.set(day, {
      day,
      day_label: DAY_LABELS[day] || `Day ${day}`,
      time: String(slot.time || "18:00").trim(),
      duration_minutes: Number(slot.duration_minutes || 90),
    });
  });
  return map;
};

const resolveScheduleMeta = (settings, goal) => {
  const schedules = listSchedulesFromSettings(settings || {});
  const scheduleId = String(goal?.learning_schedule_id || "").trim();
  if (!scheduleId) {
    return { schedule_id: null, schedule_label: null, slots: resolveLearningSlotsForGoal(settings, goal) };
  }
  const index = findScheduleIndex(schedules, scheduleId);
  if (index < 0) {
    return { schedule_id: scheduleId, schedule_label: null, slots: resolveLearningSlotsForGoal(settings, goal) };
  }
  const entry = schedules[index];
  return {
    schedule_id: entry.id,
    schedule_label: entry.label,
    slots: Array.isArray(entry.slots) ? entry.slots : [],
  };
};

const compareDateStrings = (a, b) => {
  if (a === b) {
    return 0;
  }
  return a < b ? -1 : 1;
};

/**
 * @param {object} goal - learning goal lean doc
 * @param {object} settings - user settings lean doc
 * @param {string} timezoneValue
 * @param {{ horizonWeeks?: number }} options
 */
const buildPlanScheduleDates = (goal, settings, timezoneValue, options = {}) => {
  const timeZone = normalizeTimezone(timezoneValue);
  const { schedule_id, schedule_label, slots } = resolveScheduleMeta(settings, goal);
  const byWeekday = slotsByWeekday(slots);
  const learningDays = [...byWeekday.keys()].sort((a, b) => a - b);

  const weekdays = learningDays.map((day) => byWeekday.get(day));

  const today = toLocalDateString(timeZone);
  const goalEnd = goal?.end_date
    ? toLocalDateString(timeZone, new Date(goal.end_date))
    : today;

  let horizonWeeks = Number(options.horizonWeeks);
  if (!Number.isFinite(horizonWeeks) || horizonWeeks < 1) {
    horizonWeeks = DEFAULT_HORIZON_WEEKS;
  }
  horizonWeeks = Math.min(horizonWeeks, MAX_HORIZON_WEEKS);

  const horizonEnd = addLocalDays(today, horizonWeeks * 7, timeZone);
  const rangeTo =
    compareDateStrings(goalEnd, horizonEnd) > 0 ? goalEnd : horizonEnd;

  const dates = [];
  if (learningDays.length > 0) {
    let cursor = today;
    while (compareDateStrings(cursor, rangeTo) <= 0) {
      const weekday = localWeekdayMon0(cursor, timeZone);
      const slot = weekday !== null ? byWeekday.get(weekday) : null;
      if (slot) {
        const parsed = parseDateOnly(cursor);
        const { hour, minute } = parseSlotTime(slot.time);
        const utcInstant = toUtcFromLocalParts(
          parsed.year,
          parsed.month,
          parsed.day,
          hour,
          minute,
          0,
          timeZone,
        );
        dates.push({
          date: cursor,
          day: slot.day,
          day_label: slot.day_label,
          time: slot.time,
          duration_minutes: slot.duration_minutes,
          scheduled_datetime: serializeInstantForApi(utcInstant, timeZone),
        });
      }
      cursor = addLocalDays(cursor, 1, timeZone);
    }
  }

  return {
    goal_id: String(goal._id),
    schedule_id,
    schedule_label,
    weekdays,
    range: {
      from: today,
      to: rangeTo,
    },
    dates,
  };
};

module.exports = {
  buildPlanScheduleDates,
  DEFAULT_HORIZON_WEEKS,
  MAX_HORIZON_WEEKS,
};

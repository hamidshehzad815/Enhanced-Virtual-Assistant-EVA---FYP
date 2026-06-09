/**
 * Quiet hours vs learning schedule slot conflicts (Settings save validation).
 */

const { getSchedulesFromSettingsDoc } = require("./learningSchedules");

const MINUTES_PER_DAY = 24 * 60;

const parseMinutes = (hhmm) => {
  const [h, m] = String(hhmm || "").split(":").map((x) => Number.parseInt(x, 10));
  if (!Number.isInteger(h) || !Number.isInteger(m)) {
    return null;
  }
  return h * 60 + m;
};

const intervalsOverlap = (startA, endA, startB, endB) =>
  startA < endB && endA > startB;

const windowOverlapsQuietBlock = (
  startMinutes,
  durationMinutes,
  blockStart,
  blockEnd,
) => {
  const dur = Math.max(1, Number(durationMinutes) || 1);
  const taskEnd = startMinutes + dur;

  if (blockStart === blockEnd) {
    return true;
  }

  const taskParts = [];
  if (taskEnd <= MINUTES_PER_DAY) {
    taskParts.push([startMinutes, taskEnd]);
  } else {
    taskParts.push([startMinutes, MINUTES_PER_DAY]);
    taskParts.push([0, taskEnd - MINUTES_PER_DAY]);
  }

  const quietParts =
    blockStart < blockEnd
      ? [[blockStart, blockEnd]]
      : [[blockStart, MINUTES_PER_DAY], [0, blockEnd]];

  for (const [ts, te] of taskParts) {
    for (const [qs, qe] of quietParts) {
      if (intervalsOverlap(ts, te, qs, qe)) {
        return true;
      }
    }
  }
  return false;
};

const normalizeQuietHourBlocksFromSettings = (settingsDoc = {}) => {
  const enabled = Boolean(
    settingsDoc.has_quiet_hours || settingsDoc.quiet_hours_enabled,
  );
  if (!enabled) {
    return [];
  }

  const blocks = [];
  for (const block of settingsDoc.quiet_hours || []) {
    if (!block || block.enabled === false) {
      continue;
    }
    const start = String(block.start || "").trim();
    const end = String(block.end || "").trim();
    if (parseMinutes(start) === null || parseMinutes(end) === null) {
      continue;
    }
    blocks.push({
      label: String(block.label || "quiet hours").trim() || "quiet hours",
      start,
      end,
    });
  }

  if (blocks.length > 0) {
    return blocks;
  }

  const legacyStart = String(settingsDoc.quiet_hours_start || "").trim();
  const legacyEnd = String(settingsDoc.quiet_hours_end || "").trim();
  if (parseMinutes(legacyStart) !== null && parseMinutes(legacyEnd) !== null) {
    return [{ label: "quiet hours", start: legacyStart, end: legacyEnd }];
  }

  return [];
};

const weeklySlotOverlapsQuietHours = (slotTime, slotDurationMinutes, quietBlocks) => {
  const start = parseMinutes(slotTime);
  if (start === null) {
    return [];
  }
  const dur = Math.max(1, Number(slotDurationMinutes) || 90);
  return (quietBlocks || []).filter((block) => {
    const blockStart = parseMinutes(block.start);
    const blockEnd = parseMinutes(block.end);
    if (blockStart === null || blockEnd === null) {
      return false;
    }
    return windowOverlapsQuietBlock(start, dur, blockStart, blockEnd);
  });
};

const findLearningSlotQuietHourConflicts = (schedules, quietBlocks) => {
  const conflicts = [];
  if (!quietBlocks || quietBlocks.length === 0) {
    return conflicts;
  }

  for (const schedule of schedules || []) {
    const scheduleId = String(schedule.id || "").trim();
    const label = String(schedule.label || "Learning schedule").trim();
    for (const slot of schedule.slots || []) {
      const time = String(slot.time || "").trim();
      if (!time) {
        continue;
      }
      const dur = slot.duration_minutes ?? 90;
      const hits = weeklySlotOverlapsQuietHours(time, dur, quietBlocks);
      for (const hit of hits) {
        conflicts.push({
          schedule_id: scheduleId,
          schedule_label: label,
          slot: {
            day: slot.day,
            time,
            duration_minutes: dur,
          },
          quiet_hour: hit,
        });
      }
    }
  }
  return conflicts;
};

const findQuietHourLearningConflicts = (settingsDoc, schedulesOverride = null) => {
  const quietBlocks = normalizeQuietHourBlocksFromSettings(settingsDoc);
  const schedules =
    schedulesOverride !== null && schedulesOverride !== undefined
      ? schedulesOverride
      : getSchedulesFromSettingsDoc(settingsDoc || {});
  return findLearningSlotQuietHourConflicts(schedules, quietBlocks);
};

const findQuietHourMatches = (settingsDoc, timeValue, durationMinutes = 60) => {
  const start = parseMinutes(timeValue);
  if (start === null) {
    return [];
  }
  const dur = Math.max(1, Number(durationMinutes) || 60);
  const blocks = normalizeQuietHourBlocksFromSettings(settingsDoc);
  return blocks.filter((block) => {
    const blockStart = parseMinutes(block.start);
    const blockEnd = parseMinutes(block.end);
    if (blockStart === null || blockEnd === null) {
      return false;
    }
    return windowOverlapsQuietBlock(start, dur, blockStart, blockEnd);
  });
};

const findQuietHourMatchesForDate = (settingsDoc, dueDate, durationMinutes, timeZone) => {
  const tz = timeZone && String(timeZone).trim() ? timeZone : "UTC";
  const dtf = new Intl.DateTimeFormat("en-GB", {
    timeZone: tz,
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  });
  const parts = dtf.formatToParts(new Date(dueDate));
  const map = {};
  for (const p of parts) {
    if (p.type !== "literal") {
      map[p.type] = p.value;
    }
  }
  const timeValue = `${map.hour}:${map.minute}`;
  return findQuietHourMatches(settingsDoc, timeValue, durationMinutes);
};

const formatQuietHourLabels = (blocks) => {
  const labels = (blocks || [])
    .map((block) => String(block.label || "").replace(/_/g, " ").trim())
    .filter(Boolean);
  if (labels.length === 0) {
    return "quiet hours";
  }
  if (labels.length === 1) {
    return labels[0];
  }
  if (labels.length === 2) {
    return `${labels[0]} and ${labels[1]}`;
  }
  return `${labels.slice(0, -1).join(", ")}, and ${labels[labels.length - 1]}`;
};

const quietHourLearningConflictMessage = (conflicts) => {
  const first = conflicts[0] || {};
  const scheduleLabel = first.schedule_label || "Learning schedule";
  const slot = first.slot || {};
  const quiet = first.quiet_hour || {};
  const dayNames = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
  ];
  const dayName = dayNames[slot.day] || `day ${slot.day}`;
  const quietLabel = quiet.label || "quiet hours";
  const extra = conflicts.length > 1 ? ` (${conflicts.length} overlaps)` : "";
  return (
    `Learning schedule "${scheduleLabel}" (${dayName} ${slot.time || ""}) overlaps `
    + `your "${quietLabel}" quiet hours${extra}. `
    + "Adjust the schedule or quiet hours so they do not overlap."
  );
};

module.exports = {
  findLearningSlotQuietHourConflicts,
  findQuietHourLearningConflicts,
  findQuietHourMatches,
  findQuietHourMatchesForDate,
  formatQuietHourLabels,
  normalizeQuietHourBlocksFromSettings,
  quietHourLearningConflictMessage,
  windowOverlapsQuietBlock,
  weeklySlotOverlapsQuietHours,
};

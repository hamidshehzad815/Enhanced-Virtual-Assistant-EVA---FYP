const WEEKDAY_LONG_TO_MON0 = {
  Monday: 0,
  Tuesday: 1,
  Wednesday: 2,
  Thursday: 3,
  Friday: 4,
  Saturday: 5,
  Sunday: 6,
};

const DEFAULT_SLOT_DURATION = 90;
const DEFAULT_TASK_DURATION = 120;

const parseMinutes = (hhmm) => {
  const [h, m] = String(hhmm || "").split(":").map((x) => Number.parseInt(x, 10));
  return h * 60 + m;
};

const minutesSinceMidnightInZone = (dueDate, timeZone) => {
  const tz = timeZone && String(timeZone).trim() ? timeZone : "UTC";
  const dtf = new Intl.DateTimeFormat("en-GB", {
    timeZone: tz,
    weekday: "long",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  });
  const parts = dtf.formatToParts(dueDate);
  const map = {};
  for (const p of parts) {
    if (p.type !== "literal") {
      map[p.type] = p.value;
    }
  }
  const wd = WEEKDAY_LONG_TO_MON0[map.weekday];
  const hour = Number.parseInt(map.hour, 10);
  const minute = Number.parseInt(map.minute, 10);
  return { weekday: wd, minutes: hour * 60 + minute };
};

/**
 * Recurring weekly slot vs a concrete task datetime (interval overlap on matching weekday).
 */
function dueDatetimeOverlapsSlot(
  dueDate,
  timeZone,
  slotDay,
  slotTimeHHmm,
  slotDurationMinutes = DEFAULT_SLOT_DURATION,
  taskDurationMinutes = DEFAULT_TASK_DURATION,
) {
  const { weekday, minutes: taskStart } = minutesSinceMidnightInZone(dueDate, timeZone);
  if (weekday === undefined || weekday !== slotDay) {
    return false;
  }
  const taskDur = Math.max(1, Number(taskDurationMinutes) || DEFAULT_TASK_DURATION);
  const slotDur = Math.max(1, Number(slotDurationMinutes) || DEFAULT_SLOT_DURATION);
  const taskEnd = taskStart + taskDur;
  const slotStart = parseMinutes(slotTimeHHmm);
  const slotEnd = slotStart + slotDur;
  return taskStart < slotEnd && taskEnd > slotStart;
}

/** Exact same weekday and clock start (legacy helper for tests). */
function dueDatetimeMatchesSlot(dueDate, timeZone, slotDay, slotTimeHHmm) {
  const { weekday, minutes } = minutesSinceMidnightInZone(dueDate, timeZone);
  if (weekday === undefined || weekday !== slotDay) {
    return false;
  }
  return minutes === parseMinutes(slotTimeHHmm);
}

/**
 * @param {string|import("mongoose").Types.ObjectId} userId
 * @param {{ day: number, time: string, duration_minutes?: number }[]} schedule normalized slots
 * @param {string} timeZone
 * @param {typeof import("mongoose").default.Model} TaskModel
 * @returns {Promise<{ slot: object, task: object }[]>}
 */
async function findLearningScheduleTaskConflicts(userId, schedule, timeZone, TaskModel) {
  const tasks = await TaskModel.find({
    owner_id: userId,
    is_deleted: false,
    status: { $ne: "complete" },
  })
    .select("_id title due_datetime status duration")
    .lean();

  const conflicts = [];
  for (const slot of schedule) {
    const slotDur = slot.duration_minutes ?? DEFAULT_SLOT_DURATION;
    for (const task of tasks) {
      if (!task.due_datetime) {
        continue;
      }
      const due = new Date(task.due_datetime);
      const taskDur = task.duration ?? DEFAULT_TASK_DURATION;
      if (
        dueDatetimeOverlapsSlot(
          due,
          timeZone,
          slot.day,
          slot.time,
          slotDur,
          taskDur,
        )
      ) {
        conflicts.push({
          slot: { day: slot.day, time: slot.time, duration_minutes: slotDur },
          task: {
            _id: String(task._id),
            title: task.title,
            due_datetime: task.due_datetime,
            status: task.status,
            duration: taskDur,
          },
        });
      }
    }
  }
  return conflicts;
}

/**
 * Proposed task vs all labeled learning schedules in Settings.
 * @param {Date} dueDate
 * @param {number} taskDurationMinutes
 * @param {{ id: string, label: string, slots: object[] }[]} schedules
 * @param {string} timeZone
 */
function findTaskConflictsWithLearningSchedules(
  dueDate,
  taskDurationMinutes,
  schedules,
  timeZone,
) {
  const conflicts = [];
  for (const schedule of schedules || []) {
    const scheduleId = String(schedule.id || "").trim();
    const label = String(schedule.label || "Learning schedule").trim();
    for (const slot of schedule.slots || []) {
      const slotDur = slot.duration_minutes ?? DEFAULT_SLOT_DURATION;
      if (
        dueDatetimeOverlapsSlot(
          dueDate,
          timeZone,
          slot.day,
          slot.time,
          slotDur,
          taskDurationMinutes,
        )
      ) {
        conflicts.push({
          schedule_id: scheduleId,
          schedule_label: label,
          slot: {
            day: slot.day,
            time: slot.time,
            duration_minutes: slotDur,
          },
        });
      }
    }
  }
  return conflicts;
}

module.exports = {
  dueDatetimeMatchesSlot,
  dueDatetimeOverlapsSlot,
  findLearningScheduleTaskConflicts,
  findTaskConflictsWithLearningSchedules,
  WEEKDAY_LONG_TO_MON0,
};

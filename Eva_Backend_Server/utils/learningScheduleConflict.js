/**
 * Detect conflicts between preferred_learning_schedule slots and existing tasks.
 * Schedule weekday: 0 = Monday … 6 = Sunday (matches Python date.weekday() / EVA schemas).
 */

const WEEKDAY_LONG_TO_MON0 = {
  Monday: 0,
  Tuesday: 1,
  Wednesday: 2,
  Thursday: 3,
  Friday: 4,
  Saturday: 5,
  Sunday: 6,
};

/**
 * @param {Date} dueDate
 * @param {string} timeZone IANA zone (e.g. Asia/Karachi)
 * @param {number} slotDay 0–6 (Mon–Sun)
 * @param {string} slotTimeHHmm "HH:mm"
 */
function dueDatetimeMatchesSlot(dueDate, timeZone, slotDay, slotTimeHHmm) {
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
  if (wd === undefined) {
    return false;
  }
  const hour = String(map.hour || "").padStart(2, "0");
  const minute = String(map.minute || "").padStart(2, "0");
  const clock = `${hour}:${minute}`;
  return wd === slotDay && clock === slotTimeHHmm;
}

/**
 * @param {string|import("mongoose").Types.ObjectId} userId
 * @param {{ day: number, time: string }[]} schedule normalized slots
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
    .select("_id title due_datetime status")
    .lean();

  const conflicts = [];
  for (const slot of schedule) {
    for (const task of tasks) {
      if (!task.due_datetime) {
        continue;
      }
      const due = new Date(task.due_datetime);
      if (dueDatetimeMatchesSlot(due, timeZone, slot.day, slot.time)) {
        conflicts.push({
          slot: { day: slot.day, time: slot.time },
          task: {
            _id: String(task._id),
            title: task.title,
            due_datetime: task.due_datetime,
            status: task.status,
          },
        });
      }
    }
  }
  return conflicts;
}

module.exports = {
  dueDatetimeMatchesSlot,
  findLearningScheduleTaskConflicts,
  WEEKDAY_LONG_TO_MON0,
};

/**
 * Backfill owned incomplete tasks to Google Calendar when sync is enabled.
 */
const { Task, User, UserSetting, Integration } = require("../models");
const logger = require("../config/logger");
const { resolveGoogleCalendarSync } = require("../utils/googleCalendarSync");
const { createEvent, updateEvent } = require("./googleCalendar.service");

const SYNCABLE_TASK_FILTER = {
  is_deleted: false,
  status: { $nin: ["complete", "completed"] },
};

const buildTaskPayload = (task, timezone) => ({
  title: task.title,
  due_datetime: task.due_datetime,
  duration_minutes: task.duration,
  timezone,
  description: task.description || `Priority: ${task.priority || "medium"}`,
});

const backfillUserTasksToGoogleCalendar = async (userId) => {
  const settings = await UserSetting.findOne({ user_id: userId }).lean();
  const integration = await resolveGoogleCalendarSync(userId, settings);
  if (!integration) {
    return {
      skipped: true,
      reason: "google_calendar_not_configured",
      total: 0,
      created: 0,
      updated: 0,
      failed: 0,
    };
  }

  const user = await User.findById(userId).select("timezone").lean();
  const timezone = user?.timezone || "UTC";
  const accessToken = String(integration.access_token || "").trim();
  const calendarId = String(integration.calendar_id || "primary").trim() || "primary";

  const tasks = await Task.find({
    owner_id: userId,
    ...SYNCABLE_TASK_FILTER,
  })
    .select(
      "_id title description due_datetime duration priority status google_calendar_event_id",
    )
    .sort({ due_datetime: 1 })
    .lean();

  const summary = {
    skipped: false,
    total: tasks.length,
    created: 0,
    updated: 0,
    failed: 0,
  };

  for (const task of tasks) {
    const taskData = buildTaskPayload(task, timezone);
    const existingEventId = String(task.google_calendar_event_id || "").trim();

    try {
      if (existingEventId) {
        const updated = await updateEvent(
          accessToken,
          calendarId,
          existingEventId,
          taskData,
        );
        if (updated) {
          summary.updated += 1;
        } else {
          summary.failed += 1;
        }
        continue;
      }

      const eventId = await createEvent(accessToken, calendarId, taskData);
      if (!eventId) {
        summary.failed += 1;
        continue;
      }

      await Task.updateOne(
        { _id: task._id, owner_id: userId },
        { $set: { google_calendar_event_id: eventId } },
      );
      summary.created += 1;
    } catch (error) {
      summary.failed += 1;
      logger.warn("Google Calendar backfill task failed", {
        service: "eva-backend",
        user_id: String(userId),
        task_id: String(task._id),
        error: error.message,
      });
    }
  }

  if (integration._id) {
    await Integration.updateOne(
      { _id: integration._id },
      { $set: { last_synced_at: new Date(), updated_at: new Date() } },
    );
  }

  logger.info("Google Calendar backfill completed", {
    service: "eva-backend",
    user_id: String(userId),
    ...summary,
  });

  return summary;
};

const scheduleGoogleCalendarBackfill = (userId) => {
  setImmediate(() => {
    backfillUserTasksToGoogleCalendar(userId).catch((error) => {
      logger.warn("Google Calendar backfill failed", {
        service: "eva-backend",
        user_id: String(userId),
        error: error.message,
      });
    });
  });
};

module.exports = {
  SYNCABLE_TASK_FILTER,
  backfillUserTasksToGoogleCalendar,
  scheduleGoogleCalendarBackfill,
};

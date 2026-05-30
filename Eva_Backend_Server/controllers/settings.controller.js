/**
 * Settings Controller
 * Provides authenticated settings read/update endpoints with quiet-hours support.
 */

const { User, UserSetting, Task, LearningGoal } = require("../models");
const {
  BadRequestError,
  ConflictError,
  NotFoundError,
} = require("../middleware/errorHandler");
const {
  findLearningScheduleTaskConflicts,
} = require("../utils/learningScheduleConflict");
const {
  MAX_SCHEDULES,
  normalizePreferredLearningSchedules,
  normalizeSingleLearningSchedule,
  getSchedulesFromSettingsDoc,
  listSchedulesFromSettings,
  findScheduleIndex,
  findCrossScheduleSlotConflicts,
  crossScheduleConflictMessage,
  assertUniqueLabelAmong,
  applyLearningSchedules,
} = require("../utils/learningSchedules");
const { callAIInternal } = require("../services/ai.service");

const TIME_PATTERN = /^([01]?[0-9]|2[0-3]):[0-5][0-9]$/;

const parseBoolean = (value, fieldName) => {
  if (value === undefined) {
    return undefined;
  }

  if (typeof value === "boolean") {
    return value;
  }

  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (normalized === "true") {
      return true;
    }
    if (normalized === "false") {
      return false;
    }
  }

  throw new BadRequestError(`${fieldName} must be boolean`);
};

const normalizeTime = (value, fieldName) => {
  if (value === undefined) {
    return undefined;
  }

  const normalized = String(value || "").trim();
  if (!TIME_PATTERN.test(normalized)) {
    throw new BadRequestError(`${fieldName} must be in HH:mm format`);
  }

  return normalized;
};

const wrapBadRequest = (fn, value, ...args) => {
  try {
    return fn(value, ...args);
  } catch (err) {
    throw new BadRequestError(err.message);
  }
};

const normalizeQuietHours = (blocks) => {
  if (blocks === undefined) {
    return undefined;
  }

  if (blocks === null) {
    return [];
  }

  if (!Array.isArray(blocks)) {
    throw new BadRequestError("quiet_hours must be an array");
  }

  return blocks.map((block, index) => {
    if (!block || typeof block !== "object" || Array.isArray(block)) {
      throw new BadRequestError(
        `quiet_hours[${index}] must be an object with label, start, and end`,
      );
    }

    const start = normalizeTime(block.start, `quiet_hours[${index}].start`);
    const end = normalizeTime(block.end, `quiet_hours[${index}].end`);
    const enabled = parseBoolean(block.enabled, `quiet_hours[${index}].enabled`);
    const label = String(block.label || "quiet hours").trim();

    if (!label) {
      throw new BadRequestError(`quiet_hours[${index}].label is required`);
    }

    return {
      label,
      start,
      end,
      enabled: enabled === undefined ? true : enabled,
    };
  });
};

const normalizePushToken = (value, fieldName) => {
  if (value === undefined) {
    return undefined;
  }

  const token = String(value || "").trim();
  if (!token) {
    throw new BadRequestError(`${fieldName} cannot be empty`);
  }

  if (token.length > 4096) {
    throw new BadRequestError(`${fieldName} is too long`);
  }

  return token;
};

const normalizeString = (value) => {
  if (value === undefined) {
    return undefined;
  }
  return String(value || "").trim();
};

const normalizeInteger = (value, fieldName) => {
  if (value === undefined) {
    return undefined;
  }

  const parsed =
    typeof value === "number" ? value : Number.parseInt(String(value).trim(), 10);

  if (!Number.isInteger(parsed)) {
    throw new BadRequestError(`${fieldName} must be an integer`);
  }

  return parsed;
};

const ensureUserSettings = async (userId) => {
  let settings = await UserSetting.findOne({ user_id: userId });
  if (!settings) {
    settings = await UserSetting.createDefaultSettings(userId);
  }
  return settings;
};

const defaultLearningDuration = (settings) =>
  Number(settings.preferred_learning_duration) > 0
    ? Number(settings.preferred_learning_duration)
    : 90;

const userTimeZone = (req) => (req.user && req.user.timezone) || "UTC";

const assertNoCrossScheduleSlotConflicts = (entry, existingSchedules, excludeScheduleId = null) => {
  const crossConflicts = findCrossScheduleSlotConflicts(
    entry.slots,
    existingSchedules,
    excludeScheduleId,
  );
  if (crossConflicts.length > 0) {
    throw new ConflictError(
      crossScheduleConflictMessage(entry.label, crossConflicts),
      {
        conflicts: crossConflicts,
        schedule_id: entry.id,
        schedule_label: entry.label,
      },
    );
  }
};

const assertNoSlotConflicts = async (userId, entry, timeZone) => {
  const conflicts = await findLearningScheduleTaskConflicts(
    userId,
    entry.slots,
    timeZone,
    Task,
  );
  if (conflicts.length > 0) {
    throw new ConflictError(
      `Learning schedule "${entry.label}" conflicts with existing tasks`,
      { conflicts, schedule_id: entry.id, schedule_label: entry.label },
    );
  }
};

const schedulesArrayFromDoc = (settings) => {
  const existing = listSchedulesFromSettings(settings);
  if (existing.length > 0) {
    return existing;
  }
  return [];
};

/**
 * GET /api/settings
 * Return the authenticated user's settings document.
 */
const getSettings = async (req, res, next) => {
  try {
    const settings = await ensureUserSettings(req.userId);
    const plain = settings.toObject ? settings.toObject() : settings;
    const schedulesView = getSchedulesFromSettingsDoc(plain);

    res.json({
      status: "success",
      data: {
        settings,
        preferred_learning_schedules: schedulesView,
      },
    });
  } catch (error) {
    next(error);
  }
};

/**
 * PATCH /api/settings/learning-schedule
 * Replace all learning schedules (bulk). Prefer CRUD routes for single-schedule edits.
 */
const patchLearningSchedule = async (req, res, next) => {
  try {
    const settings = await ensureUserSettings(req.userId);
    const defaultDur = defaultLearningDuration(settings);

    if (req.body.preferred_learning_schedules === undefined) {
      throw new BadRequestError("preferred_learning_schedules is required");
    }

    let firstScheduleIdProvided = true;
    const rawSchedules = req.body.preferred_learning_schedules;
    if (Array.isArray(rawSchedules) && rawSchedules.length > 0) {
      firstScheduleIdProvided = Boolean(String(rawSchedules[0]?.id || "").trim());
    }
    const schedules = wrapBadRequest(
      normalizePreferredLearningSchedules,
      rawSchedules,
      defaultDur,
    );

    if (!schedules.length) {
      throw new BadRequestError("At least one labeled learning schedule is required");
    }

    const existingPrimary = Array.isArray(settings.preferred_learning_schedules)
      ? settings.preferred_learning_schedules[0]
      : null;
    if (existingPrimary && schedules[0] && !firstScheduleIdProvided) {
      schedules[0].id = String(existingPrimary.id || schedules[0].id || "default");
    }

    const timeZone = (req.user && req.user.timezone) || "UTC";
    for (const entry of schedules) {
      const conflicts = await findLearningScheduleTaskConflicts(
        req.userId,
        entry.slots,
        timeZone,
        Task,
      );
      if (conflicts.length > 0) {
        throw new ConflictError(
          `Learning schedule "${entry.label}" conflicts with existing tasks`,
          { conflicts, schedule_id: entry.id, schedule_label: entry.label },
        );
      }
    }

    applyLearningSchedules(settings, schedules);
    await settings.save();

    // Non-blocking: trigger AI schedule rebuild after learning schedule update.
    let rebuildSummary = null;
    try {
      const primarySlots =
        Array.isArray(schedules) && schedules[0] ? schedules[0].slots : [];
      rebuildSummary = await callAIInternal("/internal/rebuild-schedule", {
        user_id: String(req.userId),
        new_schedule: primarySlots,
      });
    } catch (err) {
      rebuildSummary = { status: "error", message: err.message };
    }

    res.json({
      status: "success",
      message: "Learning schedules updated",
      data: {
        settings,
        preferred_learning_schedules: schedules,
        rebuild: rebuildSummary,
      },
    });
  } catch (error) {
    next(error);
  }
};

/**
 * PATCH /api/settings
 * Update user settings (quiet-hours + notification toggles) for the authenticated user.
 */
const updateSettings = async (req, res, next) => {
  try {
    const settings = await ensureUserSettings(req.userId);
    const update = {};

    const notificationsEnabled = parseBoolean(
      req.body.notifications_enabled,
      "notifications_enabled",
    );
    const pushNotificationsEnabled = parseBoolean(
      req.body.push_notifications_enabled,
      "push_notifications_enabled",
    );
    const emailNotificationsEnabled = parseBoolean(
      req.body.email_notifications_enabled,
      "email_notifications_enabled",
    );
    const quietHoursEnabled = parseBoolean(
      req.body.quiet_hours_enabled,
      "quiet_hours_enabled",
    );
    const quietHours = normalizeQuietHours(req.body.quiet_hours);
    const pushToken = normalizePushToken(req.body.push_token, "push_token");
    const removePushToken = normalizePushToken(
      req.body.remove_push_token,
      "remove_push_token",
    );
    const theme = normalizeString(req.body.theme);
    const language = normalizeString(req.body.language);
    const defaultReminderMinutes = normalizeInteger(
      req.body.default_reminder_minutes,
      "default_reminder_minutes",
    );
    const defaultTopicReminderMinutes = normalizeInteger(
      req.body.default_topic_reminder_minutes,
      "default_topic_reminder_minutes",
    );
    const defaultTaskPriority = normalizeString(req.body.default_task_priority);
    const defaultTaskDuration = normalizeInteger(
      req.body.default_task_duration,
      "default_task_duration",
    );
    const behavioralAnalyticsEnabled = parseBoolean(
      req.body.behavioral_analytics_enabled,
      "behavioral_analytics_enabled",
    );
    const analyticsMinTasksThreshold = normalizeInteger(
      req.body.analytics_min_tasks_threshold,
      "analytics_min_tasks_threshold",
    );
    const analyticsMinTasksPerDay = normalizeInteger(
      req.body.analytics_min_tasks_per_day,
      "analytics_min_tasks_per_day",
    );
    const preferredLearningDuration = normalizeInteger(
      req.body.preferred_learning_duration,
      "preferred_learning_duration",
    );
    const preferredLearningDurationForSched =
      preferredLearningDuration !== undefined
        ? preferredLearningDuration
        : Number(settings.preferred_learning_duration) || 90;

    let preferredLearningSchedules;
    let firstScheduleIdProvided = true;
    if (req.body.preferred_learning_schedules !== undefined) {
      const rawSchedules = req.body.preferred_learning_schedules;
      if (Array.isArray(rawSchedules) && rawSchedules.length > 0) {
        firstScheduleIdProvided = Boolean(
          String(rawSchedules[0]?.id || "").trim(),
        );
      }
      preferredLearningSchedules = wrapBadRequest(
        normalizePreferredLearningSchedules,
        rawSchedules,
        preferredLearningDurationForSched,
      );
    }

    const googleCalendarSyncEnabled = parseBoolean(
      req.body.google_calendar_sync_enabled,
      "google_calendar_sync_enabled",
    );
    const allowFriendRequests = normalizeString(req.body.allow_friend_requests);
    const showLastActive = parseBoolean(req.body.show_last_active, "show_last_active");

    if (notificationsEnabled !== undefined) {
      update.notifications_enabled = notificationsEnabled;
    }

    if (pushNotificationsEnabled !== undefined) {
      update.push_notifications_enabled = pushNotificationsEnabled;
    }

    if (emailNotificationsEnabled !== undefined) {
      update.email_notifications_enabled = emailNotificationsEnabled;
    }

    if (quietHoursEnabled !== undefined) {
      update.quiet_hours_enabled = quietHoursEnabled;
    }

    if (quietHours !== undefined) {
      update.quiet_hours = quietHours;
      // If user clears all quiet-hour blocks, disable quiet-hours unless explicitly set.
      if (quietHours.length === 0 && quietHoursEnabled === undefined) {
        update.quiet_hours_enabled = false;
      }
    }

    if (theme !== undefined) {
      update.theme = theme;
    }

    if (language !== undefined) {
      update.language = language;
    }

    if (defaultReminderMinutes !== undefined) {
      update.default_reminder_minutes = defaultReminderMinutes;
    }

    if (defaultTopicReminderMinutes !== undefined) {
      update.default_topic_reminder_minutes = defaultTopicReminderMinutes;
    }

    if (defaultTaskPriority !== undefined) {
      update.default_task_priority = defaultTaskPriority;
    }

    if (defaultTaskDuration !== undefined) {
      update.default_task_duration = defaultTaskDuration;
    }

    if (behavioralAnalyticsEnabled !== undefined) {
      update.behavioral_analytics_enabled = behavioralAnalyticsEnabled;
    }

    if (analyticsMinTasksThreshold !== undefined) {
      update.analytics_min_tasks_threshold = analyticsMinTasksThreshold;
    }
    if (analyticsMinTasksPerDay !== undefined) {
      update.analytics_min_tasks_per_day = analyticsMinTasksPerDay;
    }

    if (preferredLearningDuration !== undefined) {
      update.preferred_learning_duration = preferredLearningDuration;
    }

    if (preferredLearningSchedules !== undefined) {
      const existingPrimary = Array.isArray(settings.preferred_learning_schedules)
        ? settings.preferred_learning_schedules[0]
        : null;
      if (existingPrimary && preferredLearningSchedules[0] && !firstScheduleIdProvided) {
        preferredLearningSchedules[0].id = String(
          existingPrimary.id || preferredLearningSchedules[0].id || "default",
        );
      }
      update.preferred_learning_schedules = preferredLearningSchedules;
    }

    if (googleCalendarSyncEnabled !== undefined) {
      update.google_calendar_sync_enabled = googleCalendarSyncEnabled;
    }

    if (allowFriendRequests !== undefined) {
      update.allow_friend_requests = allowFriendRequests;
    }

    if (showLastActive !== undefined) {
      update.show_last_active = showLastActive;
    }

    const hasPushTokenMutation =
      pushToken !== undefined || removePushToken !== undefined;

    if (Object.keys(update).length === 0 && !hasPushTokenMutation) {
      throw new BadRequestError("No valid settings fields provided");
    }

    if (Object.keys(update).length > 0) {
      Object.assign(settings, update);
      await settings.save();
    }

    // Non-blocking: when preferred_learning_schedules updated, ask AI to rebuild pending sessions.
    let rebuildSummary = null;
    if (update.preferred_learning_schedules !== undefined) {
      try {
        const primarySlots =
          Array.isArray(update.preferred_learning_schedules) &&
          update.preferred_learning_schedules[0]
            ? update.preferred_learning_schedules[0].slots
            : [];
        rebuildSummary = await callAIInternal("/internal/rebuild-schedule", {
          user_id: String(req.userId),
          new_schedule: primarySlots,
        });
      } catch (err) {
        rebuildSummary = { status: "error", message: err.message };
      }
    }

    if (pushToken !== undefined) {
      await User.updateOne(
        { _id: req.userId },
        {
          $addToSet: {
            push_tokens: pushToken,
          },
        },
      );
    }

    if (removePushToken !== undefined) {
      await User.updateOne(
        { _id: req.userId },
        {
          $pull: {
            push_tokens: removePushToken,
          },
        },
      );
    }

    res.json({
      status: "success",
      message: "Settings updated",
      data: {
        settings,
        ...(rebuildSummary ? { rebuild: rebuildSummary } : {}),
      },
    });
  } catch (error) {
    next(error);
  }
};

/**
 * GET /api/settings/learning-schedules
 */
const listLearningSchedules = async (req, res, next) => {
  try {
    const settings = await ensureUserSettings(req.userId);
    const schedules = schedulesArrayFromDoc(settings);
    res.json({
      status: "success",
      data: { preferred_learning_schedules: schedules },
    });
  } catch (error) {
    next(error);
  }
};

/**
 * POST /api/settings/learning-schedules
 * Body: { label, slots, id? }
 */
const createLearningSchedule = async (req, res, next) => {
  try {
    const settings = await ensureUserSettings(req.userId);
    const defaultDur = defaultLearningDuration(settings);
    const current = schedulesArrayFromDoc(settings);

    if (current.length >= MAX_SCHEDULES) {
      throw new BadRequestError(
        `You can save at most ${MAX_SCHEDULES} learning schedules. Delete one before adding another.`,
      );
    }

    let entry;
    try {
      entry = normalizeSingleLearningSchedule(req.body, defaultDur, {
        pathPrefix: "schedule",
      });
    } catch (err) {
      throw new BadRequestError(err.message);
    }

    if (findScheduleIndex(current, entry.id) >= 0) {
      throw new BadRequestError("A schedule with this id already exists");
    }

    try {
      assertUniqueLabelAmong(current, entry.label);
    } catch (err) {
      throw new BadRequestError(err.message);
    }

    assertNoCrossScheduleSlotConflicts(entry, current);
    await assertNoSlotConflicts(req.userId, entry, userTimeZone(req));

    const updated = [...current, entry];
    applyLearningSchedules(settings, updated);
    await settings.save();

    res.status(201).json({
      status: "success",
      message: "Learning schedule created",
      data: { schedule: entry, preferred_learning_schedules: updated },
    });
  } catch (error) {
    next(error);
  }
};

/**
 * PATCH /api/settings/learning-schedules/:scheduleId
 * Body: { label?, slots? }
 */
const updateLearningSchedule = async (req, res, next) => {
  try {
    const scheduleId = String(req.params.scheduleId || "").trim();
    if (!scheduleId) {
      throw new BadRequestError("scheduleId is required");
    }

    const settings = await ensureUserSettings(req.userId);
    const defaultDur = defaultLearningDuration(settings);
    const current = schedulesArrayFromDoc(settings);
    const index = findScheduleIndex(current, scheduleId);
    if (index < 0) {
      throw new NotFoundError("Learning schedule not found");
    }

    const existing = current[index];
    const merged = {
      id: existing.id,
      label:
        req.body.label !== undefined
          ? String(req.body.label || "").trim()
          : existing.label,
      slots: req.body.slots !== undefined ? req.body.slots : existing.slots,
    };

    let entry;
    try {
      entry = normalizeSingleLearningSchedule(merged, defaultDur, {
        pathPrefix: "schedule",
        allowMissingId: false,
      });
    } catch (err) {
      throw new BadRequestError(err.message);
    }
    entry.id = existing.id;

    try {
      assertUniqueLabelAmong(current, entry.label, existing.id);
    } catch (err) {
      throw new BadRequestError(err.message);
    }

    assertNoCrossScheduleSlotConflicts(entry, current, existing.id);
    await assertNoSlotConflicts(req.userId, entry, userTimeZone(req));

    const updated = [...current];
    updated[index] = entry;
    applyLearningSchedules(settings, updated);
    await settings.save();

    res.json({
      status: "success",
      message: "Learning schedule updated",
      data: { schedule: entry, preferred_learning_schedules: updated },
    });
  } catch (error) {
    next(error);
  }
};

/**
 * DELETE /api/settings/learning-schedules/:scheduleId
 */
const deleteLearningSchedule = async (req, res, next) => {
  try {
    const scheduleId = String(req.params.scheduleId || "").trim();
    if (!scheduleId) {
      throw new BadRequestError("scheduleId is required");
    }

    const inUse = await LearningGoal.exists({
      user_id: req.userId,
      learning_schedule_id: scheduleId,
      status: "active",
    });
    if (inUse) {
      throw new ConflictError(
        "This schedule is linked to an active learning plan. Pause or complete that plan before deleting the schedule.",
        { schedule_id: scheduleId },
      );
    }

    const settings = await ensureUserSettings(req.userId);
    const current = schedulesArrayFromDoc(settings);
    const index = findScheduleIndex(current, scheduleId);
    if (index < 0) {
      throw new NotFoundError("Learning schedule not found");
    }

    const updated = current.filter((_, i) => i !== index);
    applyLearningSchedules(settings, updated);
    await settings.save();

    res.json({
      status: "success",
      message: "Learning schedule deleted",
      data: { preferred_learning_schedules: updated },
    });
  } catch (error) {
    next(error);
  }
};

module.exports = {
  getSettings,
  updateSettings,
  patchLearningSchedule,
  listLearningSchedules,
  createLearningSchedule,
  updateLearningSchedule,
  deleteLearningSchedule,
};

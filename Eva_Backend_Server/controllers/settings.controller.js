/**
 * Settings Controller
 * Provides authenticated settings read/update endpoints with quiet-hours support.
 */

const { User, UserSetting } = require("../models");
const { BadRequestError } = require("../middleware/errorHandler");

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

/**
 * GET /api/settings
 * Return the authenticated user's settings document.
 */
const getSettings = async (req, res, next) => {
  try {
    const settings = await ensureUserSettings(req.userId);

    res.json({
      status: "success",
      data: {
        settings,
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
    const hasQuietHours = parseBoolean(req.body.has_quiet_hours, "has_quiet_hours");
    const quietHoursEnabled = parseBoolean(
      req.body.quiet_hours_enabled,
      "quiet_hours_enabled",
    );
    const quietHoursStart = normalizeTime(
      req.body.quiet_hours_start,
      "quiet_hours_start",
    );
    const quietHoursEnd = normalizeTime(req.body.quiet_hours_end, "quiet_hours_end");
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
    const preferredLearningDuration = normalizeInteger(
      req.body.preferred_learning_duration,
      "preferred_learning_duration",
    );
    const preferredLearningTime = normalizeString(req.body.preferred_learning_time);
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

    if (hasQuietHours !== undefined) {
      update.has_quiet_hours = hasQuietHours;
    }

    if (quietHoursEnabled !== undefined) {
      update.quiet_hours_enabled = quietHoursEnabled;
    }

    if (quietHoursStart !== undefined) {
      update.quiet_hours_start = quietHoursStart;
    }

    if (quietHoursEnd !== undefined) {
      update.quiet_hours_end = quietHoursEnd;
    }

    if (quietHours !== undefined) {
      update.quiet_hours = quietHours;

      if (quietHours.length > 0) {
        update.has_quiet_hours =
          hasQuietHours !== undefined ? hasQuietHours : true;
        update.quiet_hours_enabled =
          quietHoursEnabled !== undefined ? quietHoursEnabled : true;
        update.quiet_hours_start =
          quietHoursStart !== undefined ? quietHoursStart : quietHours[0].start;
        update.quiet_hours_end =
          quietHoursEnd !== undefined ? quietHoursEnd : quietHours[0].end;
      } else {
        update.has_quiet_hours =
          hasQuietHours !== undefined ? hasQuietHours : false;
        update.quiet_hours_enabled =
          quietHoursEnabled !== undefined ? quietHoursEnabled : false;
      }
    }

    if (
      update.has_quiet_hours === false &&
      update.quiet_hours_enabled === undefined
    ) {
      update.quiet_hours_enabled = false;
    }

    if (
      update.quiet_hours_enabled === false &&
      update.has_quiet_hours === undefined
    ) {
      update.has_quiet_hours = false;
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

    if (preferredLearningDuration !== undefined) {
      update.preferred_learning_duration = preferredLearningDuration;
    }

    if (preferredLearningTime !== undefined) {
      update.preferred_learning_time = preferredLearningTime;
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
      },
    });
  } catch (error) {
    next(error);
  }
};

module.exports = {
  getSettings,
  updateSettings,
};

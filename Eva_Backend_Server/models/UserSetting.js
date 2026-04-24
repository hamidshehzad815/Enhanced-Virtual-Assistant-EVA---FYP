/**
 * UserSetting Model
 * Stores user preferences and settings
 */

const mongoose = require("mongoose");

const quietHourBlockSchema = new mongoose.Schema(
  {
    label: {
      type: String,
      trim: true,
      maxlength: [50, "Quiet hour label cannot exceed 50 characters"],
      default: "quiet_hours",
    },
    start: {
      type: String,
      required: true,
      match: [
        /^([01]?[0-9]|2[0-3]):[0-5][0-9]$/,
        "Invalid quiet hour start format (HH:mm)",
      ],
    },
    end: {
      type: String,
      required: true,
      match: [
        /^([01]?[0-9]|2[0-3]):[0-5][0-9]$/,
        "Invalid quiet hour end format (HH:mm)",
      ],
    },
    enabled: {
      type: Boolean,
      default: true,
    },
  },
  { _id: false },
);

const userSettingSchema = new mongoose.Schema(
  {
    user_id: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
      unique: true,
    },
    theme: {
      type: String,
      enum: ["light", "dark"],
      default: "light",
    },
    language: {
      type: String,
      default: "en",
    },
    notifications_enabled: {
      type: Boolean,
      default: true,
    },
    push_notifications_enabled: {
      type: Boolean,
      default: true,
    },
    email_notifications_enabled: {
      type: Boolean,
      default: false,
    },
    quiet_hours_enabled: {
      type: Boolean,
      default: false,
    },
    quiet_hours: {
      type: [quietHourBlockSchema],
      default: [],
    },
    default_reminder_minutes: {
      type: Number,
      default: 30,
      min: [5, "Reminder must be at least 5 minutes"],
      max: [1440, "Reminder cannot exceed 24 hours"],
    },
    default_topic_reminder_minutes: {
      type: Number,
      default: 15,
      min: [5, "Reminder must be at least 5 minutes"],
      max: [1440, "Reminder cannot exceed 24 hours"],
    },
    default_task_priority: {
      type: String,
      enum: ["low", "medium", "high"],
      default: "medium",
    },
    default_task_duration: {
      type: Number,
      default: 120,
      min: [5, "Duration must be at least 5 minutes"],
      max: [480, "Duration cannot exceed 8 hours"],
    },
    behavioral_analytics_enabled: {
      type: Boolean,
      default: true,
    },
    analytics_min_tasks_threshold: {
      type: Number,
      default: 10,
      min: [1, "Threshold must be at least 1"],
      max: [100, "Threshold cannot exceed 100"],
    },
    preferred_learning_duration: {
      type: Number,
      default: 90,
      min: [15, "Learning duration must be at least 15 minutes"],
      max: [240, "Learning duration cannot exceed 4 hours"],
    },
    preferred_learning_time: {
      type: String,
      enum: ["morning", "afternoon", "evening"],
      default: "afternoon",
    },
    google_calendar_sync_enabled: {
      type: Boolean,
      default: false,
    },
    allow_friend_requests: {
      type: String,
      enum: ["everyone", "nobody"],
      default: "everyone",
    },
    show_last_active: {
      type: Boolean,
      default: true,
    },
  },
  {
    timestamps: {
      createdAt: "created_at",
      updatedAt: "updated_at",
    },
  },
);

// Note: user_id already has index from unique: true

/**
 * Create default settings for a user
 * @param {ObjectId} userId - User ID
 * @returns {Promise<UserSetting>}
 */
userSettingSchema.statics.createDefaultSettings = async function (userId) {
  return this.create({ user_id: userId });
};

const UserSetting = mongoose.model("UserSetting", userSettingSchema);

module.exports = UserSetting;

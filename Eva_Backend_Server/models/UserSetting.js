/**
 * UserSetting Model
 * Stores user preferences and settings
 */

const mongoose = require("mongoose");

const learningScheduleSlotSchema = new mongoose.Schema(
  {
    day: {
      type: Number,
      required: true,
      min: [0, "Learning schedule day must be 0–6 (Mon–Sun)"],
      max: [6, "Learning schedule day must be 0–6 (Mon–Sun)"],
    },
    time: {
      type: String,
      required: true,
      match: [
        /^([01]?[0-9]|2[0-3]):[0-5][0-9]$/,
        "Invalid learning schedule time (HH:mm)",
      ],
    },
    duration_minutes: {
      type: Number,
      min: [15, "Session duration must be at least 15 minutes"],
      max: [240, "Session duration cannot exceed 4 hours"],
    },
  },
  { _id: false },
);

const labeledLearningScheduleSchema = new mongoose.Schema(
  {
    id: {
      type: String,
      required: true,
      trim: true,
      maxlength: [64, "Schedule id cannot exceed 64 characters"],
    },
    label: {
      type: String,
      required: true,
      trim: true,
      maxlength: [80, "Schedule label cannot exceed 80 characters"],
    },
    slots: {
      type: [learningScheduleSlotSchema],
      default: [],
      validate: {
        validator(arr) {
          return Array.isArray(arr) && arr.length > 0;
        },
        message: "Each schedule must include at least one weekday slot",
      },
    },
  },
  { _id: false },
);

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
    default_learning_reminder_minutes: {
      type: Number,
      default: 15,
      min: [5, "Learning reminder must be at least 5 minutes"],
      max: [1440, "Learning reminder cannot exceed 24 hours"],
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
    // Labeled schedules: [{ id, label, slots: [{ day, time, duration_minutes }] }]
    preferred_learning_schedules: {
      type: [labeledLearningScheduleSchema],
      default: [],
      validate: {
        validator(arr) {
          return !Array.isArray(arr) || arr.length <= 20;
        },
        message: "At most 20 learning schedules are allowed per user",
      },
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

/**
 * Notification Model
 * Stores in-app/push/email notification records.
 */

const mongoose = require("mongoose");

const notificationSchema = new mongoose.Schema(
  {
    user_id: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
      index: true,
    },
    sender_id: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      default: null,
    },
    type: {
      type: String,
      enum: [
        "task_scheduled",
        "task_deleted",
        "task_reminder",
        "topic_reminder",
        "overdue_alert",
        "collaboration_invite",
        "learning_collaboration_invite",
        "learning_plan_created",
        "friend_request",
        "friend_accepted",
        "behavioral_suggestion",
        "goal_progress",
      ],
      required: true,
    },
    title: {
      type: String,
      required: [true, "Notification title is required"],
      trim: true,
      maxlength: [120, "Title cannot exceed 120 characters"],
    },
    message: {
      type: String,
      required: [true, "Notification message is required"],
      trim: true,
      maxlength: [500, "Message cannot exceed 500 characters"],
    },
    reference_type: {
      type: String,
      enum: ["task", "learning_goal", "topic", "friend"],
      default: null,
    },
    reference_id: {
      type: mongoose.Schema.Types.ObjectId,
      default: null,
    },
    is_read: {
      type: Boolean,
      default: false,
      index: true,
    },
    action_required: {
      type: Boolean,
      default: false,
    },
    action_taken: {
      type: String,
      enum: ["accepted", "rejected", null],
      default: null,
    },
    delivery_channel: {
      type: [
        {
          type: String,
          enum: ["push", "in_app", "email"],
        },
      ],
      default: ["in_app"],
    },
    scheduled_at: {
      type: Date,
      default: null,
    },
    sent_at: {
      type: Date,
      default: null,
    },
    expires_at: {
      type: Date,
      default: null,
    },
  },
  {
    timestamps: {
      createdAt: "created_at",
      updatedAt: "updated_at",
    },
  },
);

notificationSchema.index({ user_id: 1, created_at: -1 });
notificationSchema.index({ user_id: 1, is_read: 1, created_at: -1 });

const Notification = mongoose.model("Notification", notificationSchema);

module.exports = Notification;

/**
 * Task Model
 * Stores user scheduling tasks for dashboard/task pages.
 */

const mongoose = require("mongoose");

const collaboratorSchema = new mongoose.Schema(
  {
    user_id: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
    },
    status: {
      type: String,
      enum: ["pending", "accepted", "rejected"],
      default: "pending",
    },
  },
  { _id: false },
);

const taskSchema = new mongoose.Schema(
  {
    owner_id: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
      index: true,
    },
    title: {
      type: String,
      required: [true, "Task title is required"],
      trim: true,
      maxlength: [200, "Task title cannot exceed 200 characters"],
    },
    description: {
      type: String,
      trim: true,
      maxlength: [1000, "Task description cannot exceed 1000 characters"],
      default: null,
    },
    due_datetime: {
      type: Date,
      required: true,
      index: true,
    },
    duration: {
      type: Number,
      default: 120,
      min: [5, "Duration must be at least 5 minutes"],
      max: [1440, "Duration cannot exceed 24 hours"],
    },
    priority: {
      type: String,
      enum: ["low", "medium", "high"],
      default: "medium",
      index: true,
    },
    status: {
      type: String,
      // Stored values: pending | complete. "ongoing" kept for legacy documents only.
      enum: ["pending", "ongoing", "complete"],
      default: "pending",
      index: true,
    },
    source: {
      type: String,
      enum: ["eva", "manual"],
      default: "eva",
    },
    scheduled_by: {
      type: String,
      enum: ["manual", "behavioral_analytics"],
      default: "manual",
    },
    dependency_task_id: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "Task",
      default: null,
    },
    collaborators: {
      type: [collaboratorSchema],
      default: [],
    },
    learning_plan_id: {
      type: mongoose.Schema.Types.ObjectId,
      default: null,
    },
    learning_topic_id: {
      type: mongoose.Schema.Types.ObjectId,
      default: null,
    },
    google_calendar_event_id: {
      type: String,
      default: null,
    },
    reminder_minutes_before: {
      type: Number,
      default: 30,
      min: [0, "Reminder minutes cannot be negative"],
      max: [10080, "Reminder minutes cannot exceed 7 days"],
    },
    reminder_sent_at: {
      type: Date,
      default: null,
      index: true,
    },
    overdue_notified_at: {
      type: Date,
      default: null,
      index: true,
    },
    completed_at: {
      type: Date,
      default: null,
    },
    is_deleted: {
      type: Boolean,
      default: false,
      index: true,
    },
    deleted_at: {
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

taskSchema.index({ owner_id: 1, due_datetime: 1 });
taskSchema.index({ owner_id: 1, status: 1, due_datetime: 1 });
taskSchema.index({
  status: 1,
  is_deleted: 1,
  reminder_sent_at: 1,
  due_datetime: 1,
});
taskSchema.index({
  status: 1,
  is_deleted: 1,
  overdue_notified_at: 1,
  due_datetime: 1,
});

const Task = mongoose.model("Task", taskSchema);

module.exports = Task;

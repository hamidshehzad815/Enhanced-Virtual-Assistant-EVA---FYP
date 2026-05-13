/**
 * Roadmap topic — one session within a learning goal (ordered, with resources).
 */

const mongoose = require("mongoose");

const resourceItemSchema = new mongoose.Schema(
  {
    title: {
      type: String,
      required: true,
      trim: true,
      maxlength: [500, "Resource title cannot exceed 500 characters"],
    },
    url: {
      type: String,
      required: true,
      trim: true,
      maxlength: [2048, "Resource URL cannot exceed 2048 characters"],
    },
    thumbnail: {
      type: String,
      default: null,
      maxlength: [2048, "Thumbnail URL cannot exceed 2048 characters"],
    },
    channel_name: {
      type: String,
      default: null,
      trim: true,
      maxlength: [200, "Channel name cannot exceed 200 characters"],
    },
  },
  { _id: false },
);

const roadmapTopicSchema = new mongoose.Schema(
  {
    goal_id: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "LearningGoal",
      required: true,
      index: true,
    },
    task_id: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "Task",
      default: null,
    },
    title: {
      type: String,
      required: [true, "Roadmap topic title is required"],
      trim: true,
      maxlength: [500, "Title cannot exceed 500 characters"],
    },
    description: {
      type: String,
      trim: true,
      maxlength: [2000, "Description cannot exceed 2000 characters"],
      default: null,
    },
    order: {
      type: Number,
      required: true,
      min: [1, "order must be at least 1"],
    },
    scheduled_date: {
      type: Date,
      required: true,
    },
    estimated_duration: {
      type: Number,
      default: 90,
      min: [5, "estimated_duration must be at least 5 minutes"],
      max: [480, "estimated_duration cannot exceed 8 hours"],
    },
    status: {
      type: String,
      enum: ["pending", "ongoing", "completed", "skipped"],
      default: "pending",
      index: true,
    },
    resources: {
      type: [resourceItemSchema],
      default: [],
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
    collection: "roadmap_topics",
    timestamps: { createdAt: "created_at", updatedAt: "updated_at" },
  },
);

roadmapTopicSchema.index({ goal_id: 1, order: 1 });
roadmapTopicSchema.index({ goal_id: 1, status: 1 });

const RoadmapTopic = mongoose.model("RoadmapTopic", roadmapTopicSchema);

module.exports = RoadmapTopic;

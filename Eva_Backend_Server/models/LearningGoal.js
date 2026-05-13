/**
 * Learning goal model — roadmap-based learning plans (AI server writes; Node reads for API).
 */

const mongoose = require("mongoose");

const goalCollaboratorSchema = new mongoose.Schema(
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

const learningGoalSchema = new mongoose.Schema(
  {
    user_id: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
      index: true,
    },
    title: {
      type: String,
      required: [true, "Learning goal title is required"],
      trim: true,
      maxlength: [200, "Title cannot exceed 200 characters"],
    },
    description: {
      type: String,
      trim: true,
      maxlength: [2000, "Description cannot exceed 2000 characters"],
      default: null,
    },
    subject: {
      type: String,
      trim: true,
      lowercase: true,
      maxlength: [120, "Subject cannot exceed 120 characters"],
      default: null,
    },
    /** Roadmap level key: general, basics, intermediate, advanced, or specific subtopic key */
    roadmap_key: {
      type: String,
      required: [true, "roadmap_key is required"],
      trim: true,
      maxlength: [120, "roadmap_key cannot exceed 120 characters"],
    },
    start_date: {
      type: Date,
      required: true,
    },
    end_date: {
      type: Date,
      required: true,
    },
    /** Calendar span chosen by user (e.g. 14 for two weeks) */
    duration_days: {
      type: Number,
      required: true,
      min: [1, "duration_days must be at least 1"],
    },
    status: {
      type: String,
      enum: ["active", "completed", "paused", "cancelled"],
      default: "active",
      index: true,
    },
    paused_at: {
      type: Date,
      default: null,
    },
    total_topics: {
      type: Number,
      default: 0,
      min: 0,
    },
    completed_topics: {
      type: Number,
      default: 0,
      min: 0,
    },
    collaborators: {
      type: [goalCollaboratorSchema],
      default: [],
      validate: {
        validator(arr) {
          return !arr || arr.length <= 2;
        },
        message: "At most 2 collaborators allowed",
      },
    },
    generated_by: {
      type: String,
      enum: ["eva", "manual"],
      default: "eva",
    },
    started_at: {
      type: Date,
      default: null,
    },
    completed_at: {
      type: Date,
      default: null,
    },
    time_taken_days: {
      type: Number,
      default: null,
      min: [0, "time_taken_days cannot be negative"],
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
    collection: "learning_goals",
    timestamps: { createdAt: "created_at", updatedAt: "updated_at" },
  },
);

learningGoalSchema.index({ user_id: 1, status: 1 });
learningGoalSchema.index({ user_id: 1, is_deleted: 1, status: 1 });

const LearningGoal = mongoose.model("LearningGoal", learningGoalSchema);

module.exports = LearningGoal;

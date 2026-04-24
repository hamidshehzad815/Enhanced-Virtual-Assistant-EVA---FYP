/**
 * ConversationHistory Model
 * Stores chat messages exchanged between user and EVA.
 */

const mongoose = require("mongoose");

const conversationHistorySchema = new mongoose.Schema(
  {
    session_id: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "ChatSession",
      required: true,
      index: true,
    },
    role: {
      type: String,
      enum: ["user", "eva"],
      required: true,
    },
    content: {
      type: String,
      required: [true, "Message content is required"],
      trim: true,
    },
    transcribed_text: {
      type: String,
      default: null,
    },
    input_type: {
      type: String,
      enum: ["text", "voice"],
      default: "text",
    },
    intent: {
      type: String,
      default: null,
    },
    entities: {
      type: mongoose.Schema.Types.Mixed,
      default: null,
    },
    status: {
      type: String,
      enum: ["processed", "failed", "pending"],
      default: "processed",
    },
    error_message: {
      type: String,
      default: null,
    },
    response_time_ms: {
      type: Number,
      default: null,
    },
    is_deleted: {
      type: Boolean,
      default: false,
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

conversationHistorySchema.index({ session_id: 1, created_at: -1 });

const ConversationHistory = mongoose.model(
  "ConversationHistory",
  conversationHistorySchema,
);

module.exports = ConversationHistory;

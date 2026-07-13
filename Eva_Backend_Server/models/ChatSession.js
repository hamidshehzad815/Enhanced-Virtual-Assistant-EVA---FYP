/**
 * ChatSession Model
 * Stores chat session metadata for each user.
 */

const mongoose = require("mongoose");

const chatSessionSchema = new mongoose.Schema(
  {
    user_id: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
      index: true,
    },
    title: {
      type: String,
      trim: true,
      maxlength: [120, "Title cannot exceed 120 characters"],
      default: "New chat",
    },
    last_message_preview: {
      type: String,
      trim: true,
      maxlength: [200, "Preview cannot exceed 200 characters"],
      default: "",
    },
    last_message_at: {
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
    collection: "chatsessions", // canonical name — matches Node + AI server
  },
);

chatSessionSchema.index({ user_id: 1, last_message_at: -1 });

const ChatSession = mongoose.model("ChatSession", chatSessionSchema);

module.exports = ChatSession;

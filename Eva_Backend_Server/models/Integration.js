/**
 * Integration Model
 * Stores external integrations like Google Calendar per user.
 */

const mongoose = require("mongoose");

const integrationSchema = new mongoose.Schema(
  {
    user_id: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
      index: true,
    },
    provider: {
      type: String,
      enum: ["google_calendar"],
      required: true,
      index: true,
    },
    access_token: {
      type: String,
      required: true,
      select: false,
    },
    refresh_token: {
      type: String,
      default: null,
      select: false,
    },
    token_expires: {
      type: Date,
      default: null,
    },
    scope: {
      type: String,
      default: null,
    },
    calendar_id: {
      type: String,
      default: "primary",
    },
    last_synced_at: {
      type: Date,
      default: null,
    },
    is_active: {
      type: Boolean,
      default: true,
      index: true,
    },
  },
  {
    timestamps: {
      createdAt: "created_at",
      updatedAt: "updated_at",
    },
  },
);

integrationSchema.index({ user_id: 1, provider: 1 }, { unique: true });

const Integration = mongoose.model("Integration", integrationSchema);

module.exports = Integration;

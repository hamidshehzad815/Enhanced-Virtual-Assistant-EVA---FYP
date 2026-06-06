/**
 * Friend Model
 * Stores relationship state between two users.
 */

const mongoose = require("mongoose");

const FRIEND_STATUS = ["pending", "accepted", "rejected", "blocked"];

const friendSchema = new mongoose.Schema(
  {
    requester_id: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
      index: true,
    },
    recipient_id: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
      index: true,
    },
    pair_key: {
      type: String,
      required: true,
      unique: true,
      index: true,
    },
    status: {
      type: String,
      enum: FRIEND_STATUS,
      default: "pending",
      index: true,
    },
    responded_at: {
      type: Date,
      default: null,
    },
    blocked_by: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
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

friendSchema.pre("validate", function preValidate(next) {
  if (!this.requester_id || !this.recipient_id) {
    return next();
  }

  const a = String(this.requester_id);
  const b = String(this.recipient_id);
  this.pair_key = [a, b].sort().join(":");
  next();
});

friendSchema.statics.buildPairKey = function buildPairKey(userAId, userBId) {
  return [String(userAId), String(userBId)].sort().join(":");
};

const Friend = mongoose.model("Friend", friendSchema);

module.exports = Friend;

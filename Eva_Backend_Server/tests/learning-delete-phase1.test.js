process.env.NODE_ENV = "test";

const mongoose = require("mongoose");
const Notification = require("../models/Notification");

describe("learning delete phase 1 — schema", () => {
  test("learning_goal_deleted is a valid notification type", () => {
    const doc = new Notification({
      user_id: new mongoose.Types.ObjectId(),
      sender_id: new mongoose.Types.ObjectId(),
      type: "learning_goal_deleted",
      title: "Shared learning plan removed",
      message:
        "Ali removed Python basics from their plan. Your copy is unaffected.",
      reference_type: "learning_goal",
      reference_id: new mongoose.Types.ObjectId(),
      action_required: false,
      delivery_channel: ["push", "in_app"],
    });

    const error = doc.validateSync();
    expect(error).toBeUndefined();
  });

  test("invalid notification type is rejected", () => {
    const doc = new Notification({
      user_id: new mongoose.Types.ObjectId(),
      type: "learning_goal_removed_invalid",
      title: "Test",
      message: "Test message",
    });

    const error = doc.validateSync();
    expect(error).toBeDefined();
    expect(error.errors.type).toBeDefined();
  });
});

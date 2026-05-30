/**
 * Phase 1 schema verification for learning_update.
 * Confirms LearningGoal, RoadmapTopic, and notification types required by update flow.
 */

process.env.NODE_ENV = "test";

const mongoose = require("mongoose");
const LearningGoal = require("../models/LearningGoal");
const RoadmapTopic = require("../models/RoadmapTopic");
const Notification = require("../models/Notification");

const now = new Date();
const goalId = new mongoose.Types.ObjectId();
const userId = new mongoose.Types.ObjectId();

describe("learning update phase 1 — schema", () => {
  test("LearningGoal accepts pause/resume/complete tracking fields", () => {
    const doc = new LearningGoal({
      user_id: userId,
      title: "Python basics",
      subject: "python",
      roadmap_key: "basics",
      start_date: now,
      end_date: new Date(now.getTime() + 14 * 24 * 60 * 60 * 1000),
      duration_days: 14,
      status: "paused",
      paused_at: now,
      started_at: now,
      completed_at: null,
      time_taken_days: null,
      total_topics: 8,
      completed_topics: 3,
      is_deleted: false,
    });

    const error = doc.validateSync();
    expect(error).toBeUndefined();
    expect(doc.status).toBe("paused");
    expect(doc.paused_at).toBeInstanceOf(Date);
    expect(doc.started_at).toBeInstanceOf(Date);
  });

  test("LearningGoal completed state with time_taken_days", () => {
    const started = new Date(now.getTime() - 10 * 24 * 60 * 60 * 1000);
    const doc = new LearningGoal({
      user_id: userId,
      title: "Python basics",
      subject: "python",
      roadmap_key: "basics",
      start_date: started,
      end_date: now,
      duration_days: 14,
      status: "completed",
      started_at: started,
      completed_at: now,
      time_taken_days: 10,
      total_topics: 8,
      completed_topics: 8,
    });

    const error = doc.validateSync();
    expect(error).toBeUndefined();
    expect(doc.time_taken_days).toBe(10);
  });

  test("RoadmapTopic accepts session lifecycle fields", () => {
    const doc = new RoadmapTopic({
      goal_id: goalId,
      title: "Variables and types",
      order: 1,
      scheduled_date: now,
      status: "pending",
      completed_at: null,
      is_deleted: false,
      estimated_duration: 90,
    });

    const error = doc.validateSync();
    expect(error).toBeUndefined();
    expect(doc.status).toBe("pending");
  });

  test("RoadmapTopic accepts skipped and completed statuses", () => {
    for (const status of ["completed", "skipped", "ongoing"]) {
      const doc = new RoadmapTopic({
        goal_id: goalId,
        title: `Session ${status}`,
        order: 2,
        scheduled_date: now,
        status,
        completed_at: status === "completed" ? now : null,
      });
      expect(doc.validateSync()).toBeUndefined();
    }
  });

  test("RoadmapTopic rejects invalid status", () => {
    const doc = new RoadmapTopic({
      goal_id: goalId,
      title: "Bad status",
      order: 1,
      scheduled_date: now,
      status: "archived",
    });
    const error = doc.validateSync();
    expect(error).toBeDefined();
    expect(error.errors.status).toBeDefined();
  });

  test("topic_reminder is a valid notification type", () => {
    const doc = new Notification({
      user_id: userId,
      type: "topic_reminder",
      title: "Python session reminder",
      message: "Your Python session starts in 30 minutes, Ali.",
      reference_type: "topic",
      reference_id: new mongoose.Types.ObjectId(),
      delivery_channel: ["push", "in_app"],
    });
    expect(doc.validateSync()).toBeUndefined();
  });

  test("goal_progress is a valid notification type", () => {
    const doc = new Notification({
      user_id: userId,
      type: "goal_progress",
      title: "Learning goal completed",
      message: "Congratulations Ali — you finished Python basics!",
      reference_type: "learning_goal",
      reference_id: goalId,
      delivery_channel: ["push", "in_app"],
    });
    expect(doc.validateSync()).toBeUndefined();
  });

  test("serialized LearningGoal returns all update tracking fields", () => {
    const started = new Date(now.getTime() - 5 * 24 * 60 * 60 * 1000);
    const doc = new LearningGoal({
      user_id: userId,
      title: "Python basics",
      subject: "python",
      roadmap_key: "basics",
      start_date: started,
      end_date: now,
      duration_days: 14,
      status: "active",
      paused_at: null,
      started_at: started,
      completed_at: null,
      time_taken_days: null,
      total_topics: 8,
      completed_topics: 3,
    });

    const plain = doc.toObject();
    expect(plain.status).toBe("active");
    expect(plain.paused_at).toBeNull();
    expect(plain.started_at).toEqual(started);
    expect(plain.completed_at).toBeNull();
    expect(plain.time_taken_days).toBeNull();
    expect(plain.completed_topics).toBe(3);
    expect(plain.total_topics).toBe(8);
  });
});

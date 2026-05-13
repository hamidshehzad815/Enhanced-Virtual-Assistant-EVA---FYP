/**
 * Learning goals & roadmap topics (read + pause/resume/cancel).
 */

const mongoose = require("mongoose");
const { LearningGoal, RoadmapTopic, Task } = require("../models");
const { BadRequestError, NotFoundError } = require("../middleware/errorHandler");

const PATCH_STATUS = new Set(["active", "paused", "cancelled"]);

const toObjectId = (value) => {
  try {
    return new mongoose.Types.ObjectId(value);
  } catch {
    return null;
  }
};

const assertValidGoalId = (id) => {
  const oid = toObjectId(id);
  if (!oid) {
    throw new BadRequestError("Invalid learning goal id");
  }
  return oid;
};

const loadOwnedGoal = async (goalId, userId) => {
  const oid = assertValidGoalId(goalId);
  const goal = await LearningGoal.findOne({
    _id: oid,
    user_id: userId,
    is_deleted: false,
  }).lean();

  if (!goal) {
    throw new NotFoundError("Learning goal not found");
  }
  return { oid, goal };
};

/**
 * GET /api/learning — ongoing goals (active + paused) for the authenticated user.
 */
const getAllGoals = async (req, res, next) => {
  try {
    const goals = await LearningGoal.find({
      user_id: req.userId,
      is_deleted: false,
      status: { $in: ["active", "paused"] },
    })
      .sort({ created_at: -1 })
      .lean();

    res.json({
      status: "success",
      data: { goals },
    });
  } catch (error) {
    next(error);
  }
};

/**
 * GET /api/learning/:id — single goal with simple progress fields.
 */
const getGoal = async (req, res, next) => {
  try {
    const { oid, goal } = await loadOwnedGoal(req.params.id, req.userId);
    const total = Number(goal.total_topics || 0);
    const done = Number(goal.completed_topics || 0);
    const progress =
      total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0;

    res.json({
      status: "success",
      data: {
        goal: {
          ...goal,
          progress_percent: progress,
        },
      },
    });
  } catch (error) {
    next(error);
  }
};

/**
 * GET /api/learning/:id/topics — ordered roadmap topics (resources included).
 */
const getTopics = async (req, res, next) => {
  try {
    const { oid } = await loadOwnedGoal(req.params.id, req.userId);

    const topics = await RoadmapTopic.find({
      goal_id: oid,
      is_deleted: false,
    })
      .sort({ order: 1 })
      .lean();

    res.json({
      status: "success",
      data: { topics },
    });
  } catch (error) {
    next(error);
  }
};

/**
 * PATCH /api/learning/:id/status
 * Body: { "status": "active" | "paused" | "cancelled" }
 * "active" resumes a paused plan. "completed" is not allowed (AI-only).
 */
/**
 * POST /api/learning/:id/topics/:topicId/complete
 * Marks roadmap topic completed, syncs linked task, increments goal progress.
 */
const completeTopic = async (req, res, next) => {
  try {
    const { oid: goalOid, goal } = await loadOwnedGoal(req.params.id, req.userId);

    if (goal.status !== "active") {
      throw new BadRequestError("Only active learning plans accept topic completion.");
    }

    const topicOid = toObjectId(req.params.topicId);
    if (!topicOid) {
      throw new BadRequestError("Invalid topic id");
    }

    const topic = await RoadmapTopic.findOne({
      _id: topicOid,
      goal_id: goalOid,
      is_deleted: false,
    }).lean();

    if (!topic) {
      throw new NotFoundError("Roadmap topic not found");
    }
    if (topic.status === "completed") {
      throw new BadRequestError("This topic is already completed.");
    }
    if (!["pending", "ongoing"].includes(topic.status)) {
      throw new BadRequestError("This topic cannot be marked complete from its current status.");
    }

    const now = new Date();

    await RoadmapTopic.findOneAndUpdate(
      { _id: topicOid, goal_id: goalOid, is_deleted: false },
      { $set: { status: "completed", completed_at: now, updated_at: now } },
    );

    if (!goal.started_at) {
      await LearningGoal.updateOne(
        { _id: goalOid, user_id: req.userId, started_at: null, is_deleted: false },
        { $set: { started_at: now, updated_at: now } },
      );
    }

    const afterInc = await LearningGoal.findOneAndUpdate(
      { _id: goalOid, user_id: req.userId, is_deleted: false },
      { $inc: { completed_topics: 1 }, $set: { updated_at: now } },
      { new: true },
    ).lean();

    let savedGoal = afterInc;
    const total = Number(savedGoal.total_topics || 0);
    const done = Number(savedGoal.completed_topics || 0);

    if (total > 0 && done >= total) {
      const completedAt = now;
      const started = savedGoal.started_at ? new Date(savedGoal.started_at) : null;
      const timeTaken =
        started && !Number.isNaN(started.getTime())
          ? Math.max(0, Math.floor((completedAt - started) / 86400000))
          : null;

      savedGoal = await LearningGoal.findOneAndUpdate(
        { _id: goalOid, user_id: req.userId },
        {
          $set: {
            status: "completed",
            completed_at: completedAt,
            time_taken_days: timeTaken,
            updated_at: now,
          },
        },
        { new: true },
      ).lean();
    }

    if (topic.task_id) {
      await Task.updateOne(
        {
          _id: topic.task_id,
          owner_id: req.userId,
          is_deleted: { $ne: true },
        },
        {
          $set: {
            status: "complete",
            completed_at: now,
            updated_at: now,
          },
        },
      );
    }

    const progressPct =
      total > 0
        ? Math.min(100, Math.round((Number(savedGoal.completed_topics || 0) / total) * 100))
        : 0;

    res.json({
      status: "success",
      message: "Topic marked complete",
      data: {
        topic: {
          ...topic,
          status: "completed",
          completed_at: now,
        },
        goal: {
          ...savedGoal,
          progress_percent: progressPct,
        },
      },
    });
  } catch (error) {
    next(error);
  }
};

const updateStatus = async (req, res, next) => {
  try {
    const raw = String(req.body?.status || "")
      .trim()
      .toLowerCase();
    if (!PATCH_STATUS.has(raw)) {
      throw new BadRequestError(
        'status must be one of: "active", "paused", "cancelled"',
      );
    }

    const { oid, goal } = await loadOwnedGoal(req.params.id, req.userId);

    if (goal.status === "completed") {
      throw new BadRequestError("Completed learning plans cannot be changed here.");
    }

    if (raw === "active" && goal.status !== "paused") {
      throw new BadRequestError('Only paused plans can be resumed (set status to "active").');
    }

    if (raw === "paused" && goal.status !== "active") {
      throw new BadRequestError('Only active plans can be paused.');
    }

    const now = new Date();
    const update = { updated_at: now };

    if (raw === "paused") {
      update.status = "paused";
      update.paused_at = now;
    } else if (raw === "active") {
      update.status = "active";
      update.paused_at = null;
    } else if (raw === "cancelled") {
      update.status = "cancelled";
      update.paused_at = null;
    }

    const saved = await LearningGoal.findOneAndUpdate(
      { _id: oid, user_id: req.userId, is_deleted: false },
      { $set: update },
      { new: true },
    ).lean();

    if (raw === "cancelled") {
      await Task.updateMany(
        {
          owner_id: req.userId,
          learning_plan_id: oid,
          is_deleted: { $ne: true },
        },
        {
          $set: {
            is_deleted: true,
            deleted_at: now,
            updated_at: now,
          },
        },
      );
    }

    res.json({
      status: "success",
      message: "Learning goal updated",
      data: { goal: saved },
    });
  } catch (error) {
    next(error);
  }
};

module.exports = {
  getAllGoals,
  getGoal,
  getTopics,
  completeTopic,
  updateStatus,
};

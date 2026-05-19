/**
 * Learning goals & roadmap topics (read + pause/resume/cancel).
 */

const mongoose = require("mongoose");
const jwt = require("jsonwebtoken");
const { LearningGoal, RoadmapTopic, Task } = require("../models");
const {
  BadRequestError,
  ConflictError,
  NotFoundError,
} = require("../middleware/errorHandler");
const { applyLearningCollaborationAction } = require("../services/learningCollaboration.service");

const PATCH_STATUS = new Set(["active", "paused", "cancelled"]);

const getCollaborationTokenSecret = () =>
  process.env.COLLAB_ACTION_SECRET || process.env.JWT_ACCESS_SECRET || "";

const verifyCollaborationToken = (token) => {
  const secret = getCollaborationTokenSecret();
  if (!secret) {
    throw new BadRequestError("Collaboration response is not configured");
  }
  try {
    return jwt.verify(token, secret);
  } catch (_error) {
    throw new BadRequestError("Invalid or expired collaboration response link");
  }
};

const normalizeCollaborationAction = (value) => {
  const action = String(value || "").trim().toLowerCase();
  if (action === "accept" || action === "reject") {
    return action;
  }
  return null;
};

const renderCollaborationHtml = ({ title, message }) => `
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>${title}</title>
    <style>
      body { font-family: Arial, sans-serif; background:#f5f7fb; padding:24px; color:#111827; }
      .card { max-width:620px; margin:0 auto; background:#fff; border-radius:10px; padding:24px; box-shadow:0 8px 28px rgba(0,0,0,0.08); }
      h1 { margin:0 0 10px; font-size:22px; }
      p { margin:0; color:#374151; line-height:1.5; }
    </style>
  </head>
  <body>
    <div class="card">
      <h1>${title}</h1>
      <p>${message}</p>
    </div>
  </body>
</html>
`;

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

/**
 * POST /api/learning/:id/collaborators/respond
 * Body: { "action": "accept" | "reject" }
 */
const respondToLearningCollaborationInvite = async (req, res, next) => {
  try {
    const action = normalizeCollaborationAction(req.body?.action);
    if (!action) {
      throw new BadRequestError('action must be "accept" or "reject"');
    }

    const result = await applyLearningCollaborationAction({
      goalId: req.params.id,
      collaboratorUserId: req.userId,
      action,
    });

    const verb = action === "accept" ? "accepted" : "rejected";
    const message = result.already_responded
      ? `Invite already ${String(result.current_status || "").toLowerCase()}.`
      : `Learning plan invite ${verb}.`;

    res.json({
      status: "success",
      message,
      data: {
        goal_id: String(result.goal._id),
        collaborator_goal_id: result.collaborator_goal_id
          ? String(result.collaborator_goal_id)
          : null,
        collaboration_status: result.current_status,
        already_responded: result.already_responded,
      },
    });
  } catch (error) {
    next(error);
  }
};

/**
 * GET /api/learning/collaboration/respond?token=...
 */
const respondToLearningCollaborationInviteViaLink = async (req, res, next) => {
  try {
    const token = String(req.query?.token || "").trim();
    if (!token) {
      throw new BadRequestError("Missing response token");
    }

    const payload = verifyCollaborationToken(token);
    const action = normalizeCollaborationAction(payload?.action);
    if (!action) {
      throw new BadRequestError("Invalid action in response token");
    }

    const goalId = String(payload?.reference_id || payload?.task_id || "");
    const userId = String(payload?.user_id || "");
    const notificationId = payload?.notification_id ? String(payload.notification_id) : null;

    const result = await applyLearningCollaborationAction({
      goalId,
      collaboratorUserId: userId,
      action,
      notificationId,
    });

    const verbPast = action === "accept" ? "accepted" : "rejected";
    let successMessage = result.already_responded
      ? `This invitation was already ${String(result.current_status || "").toLowerCase()}.`
      : `You have ${verbPast} this learning plan invite successfully.`;

    if (
      !result.already_responded
      && action === "accept"
      && result.collaborator_goal_id
    ) {
      successMessage += " Your own copy of the learning plan is ready in EVA.";
    }

    const html = renderCollaborationHtml({
      title: result.already_responded ? "Already Responded" : "Response Saved",
      message: successMessage,
    });

    res.status(200).type("html").send(html);
  } catch (error) {
    if (
      error instanceof BadRequestError
      || error instanceof NotFoundError
      || error instanceof ConflictError
    ) {
      const html = renderCollaborationHtml({
        title: "Unable to Process Invite",
        message: error.message,
      });
      return res.status(error.statusCode || 400).type("html").send(html);
    }
    return next(error);
  }
};

module.exports = {
  getAllGoals,
  getGoal,
  getTopics,
  completeTopic,
  updateStatus,
  respondToLearningCollaborationInvite,
  respondToLearningCollaborationInviteViaLink,
};

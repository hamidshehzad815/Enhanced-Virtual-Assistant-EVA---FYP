/**
 * Learning goals & roadmap topics (read + pause/resume/cancel).
 */

const mongoose = require("mongoose");
const jwt = require("jsonwebtoken");
const { LearningGoal, RoadmapTopic, Task, UserSetting } = require("../models");
const {
  BadRequestError,
  ConflictError,
  NotFoundError,
} = require("../middleware/errorHandler");
const { applyLearningCollaborationAction } = require("../services/learningCollaboration.service");
const { softDeleteLearningGoalById } = require("../services/learningDelete.service");
const { insert_and_dispatch } = require("../services/notification.service");
const { callAIInternal } = require("../services/ai.service");
const { validateTopicAction } = require("../utils/learningSessionState");
const { localizeApiPayload, withApiTimezone } = require("../utils/apiDateTime");

const buildApiData = (req, payload) => {
  const timezone = req.user?.timezone || "UTC";
  return withApiTimezone(localizeApiPayload(payload, timezone), timezone);
};

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
      data: buildApiData(req, { goals }),
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
      data: buildApiData(req, {
        goal: {
          ...goal,
          progress_percent: progress,
        },
      }),
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
      data: buildApiData(req, { topics }),
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

    const goalTopics = await RoadmapTopic.find({
      goal_id: goalOid,
      is_deleted: false,
    })
      .sort({ order: 1 })
      .lean();

    const completeBlock = validateTopicAction({
      topics: goalTopics,
      topicId: topicOid,
      action: "complete",
    });
    if (completeBlock) {
      throw new ConflictError(completeBlock.message);
    }

    // AI server performs all DB writes for learning update flows.
    const aiResult = await callAIInternal("/internal/auto-complete-topic", {
      topic_id: String(topicOid),
      goal_id: String(goalOid),
      user_id: String(req.userId),
    });

    const topic = await RoadmapTopic.findOne({
      _id: topicOid,
      goal_id: goalOid,
      is_deleted: false,
    }).lean();
    const savedGoal = await LearningGoal.findOne({
      _id: goalOid,
      user_id: req.userId,
      is_deleted: false,
    }).lean();

    const total = Number(savedGoal?.total_topics || 0);
    const progressPct =
      total > 0
        ? Math.min(
            100,
            Math.round((Number(savedGoal?.completed_topics || 0) / total) * 100),
          )
        : 0;

    res.json({
      status: "success",
      message: "Topic marked complete",
      data: buildApiData(req, {
        ai: aiResult || null,
        topic,
        goal: savedGoal ? { ...savedGoal, progress_percent: progressPct } : null,
      }),
    });
  } catch (error) {
    next(error);
  }
};

/**
 * POST /api/learning/:id/topics/:topicId/skip
 * Skips a roadmap topic via AI internal endpoint (cascades future sessions).
 */
const skipTopic = async (req, res, next) => {
  try {
    const { oid: goalOid, goal } = await loadOwnedGoal(req.params.id, req.userId);
    if (goal.status !== "active") {
      throw new BadRequestError("Only active learning plans accept skipping topics.");
    }

    const topicOid = toObjectId(req.params.topicId);
    if (!topicOid) {
      throw new BadRequestError("Invalid topic id");
    }

    const goalTopics = await RoadmapTopic.find({
      goal_id: goalOid,
      is_deleted: false,
    })
      .sort({ order: 1 })
      .lean();

    const skipBlock = validateTopicAction({
      topics: goalTopics,
      topicId: topicOid,
      action: "skip",
    });
    if (skipBlock) {
      throw new ConflictError(skipBlock.message);
    }

    const aiResult = await callAIInternal("/internal/skip-topic", {
      topic_id: String(topicOid),
      goal_id: String(goalOid),
      user_id: String(req.userId),
    });

    const topic = await RoadmapTopic.findOne({
      _id: topicOid,
      goal_id: goalOid,
      is_deleted: false,
    }).lean();
    const savedGoal = await LearningGoal.findOne({
      _id: goalOid,
      user_id: req.userId,
      is_deleted: false,
    }).lean();

    res.json({
      status: "success",
      message: "Topic skipped",
      data: buildApiData(req, { ai: aiResult || null, topic, goal: savedGoal }),
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
      const { goal, notifications } = await softDeleteLearningGoalById(
        req.params.id,
        req.userId,
      );

      let notificationSummary = {
        requested: 0,
        inserted: 0,
        dispatched_push: 0,
        dispatched_email: 0,
        failed: 0,
        results: [],
      };
      if (notifications.length > 0) {
        notificationSummary = await insert_and_dispatch(notifications);
      }

      return res.json({
        status: "success",
        message: "Learning goal removed",
        data: buildApiData(req, { goal, notifications: notificationSummary }),
      });
    }

    const saved = await LearningGoal.findOneAndUpdate(
      { _id: oid, user_id: req.userId, is_deleted: false },
      { $set: update },
      { new: true },
    ).lean();

    // On resume, ask AI to rebase sessions (non-blocking).
    let rebuildSummary = null;
    if (raw === "active") {
      try {
        const query = UserSetting.findOne({ user_id: req.userId });
        const settingsDoc = query && typeof query.lean === "function"
          ? await query.lean()
          : await query;
        const schedules = Array.isArray(settingsDoc?.preferred_learning_schedules)
          ? settingsDoc.preferred_learning_schedules
          : [];
        const primarySlots = schedules[0]?.slots || [];
        rebuildSummary = await callAIInternal("/internal/rebuild-schedule", {
          user_id: String(req.userId),
          new_schedule: primarySlots,
        });
      } catch (err) {
        rebuildSummary = { status: "error", message: err.message };
      }
    }

    res.json({
      status: "success",
      message: "Learning goal updated",
      data: buildApiData(req, {
        goal: saved,
        ...(rebuildSummary ? { rebuild: rebuildSummary } : {}),
      }),
    });
  } catch (error) {
    next(error);
  }
};

/**
 * DELETE /api/learning/:id — soft-delete goal (UI); same rules as chat learning_delete.
 */
const deleteGoal = async (req, res, next) => {
  try {
    const { goal, notifications } = await softDeleteLearningGoalById(
      req.params.id,
      req.userId,
    );

    let notificationSummary = {
      requested: 0,
      inserted: 0,
      dispatched_push: 0,
      dispatched_email: 0,
      failed: 0,
      results: [],
    };
    if (notifications.length > 0) {
      notificationSummary = await insert_and_dispatch(notifications);
    }

    res.json({
      status: "success",
      message: "Learning goal removed",
      data: buildApiData(req, {
        goal,
        notifications: notificationSummary,
      }),
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
  skipTopic,
  updateStatus,
  deleteGoal,
  respondToLearningCollaborationInvite,
  respondToLearningCollaborationInviteViaLink,
};

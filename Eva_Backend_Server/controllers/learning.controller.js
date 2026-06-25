/**
 * Learning goals — session mutations and plan status (reads use /api/roadmaps).
 */

const mongoose = require("mongoose");
const jwt = require("jsonwebtoken");
const { LearningGoal, RoadmapTopic, UserSetting } = require("../models");
const {
  BadRequestError,
  ConflictError,
  NotFoundError,
} = require("../middleware/errorHandler");
const { applyLearningCollaborationAction } = require("../services/learningCollaboration.service");
const { softDeleteLearningGoalById } = require("../services/learningDelete.service");
const { insert_and_dispatch } = require("../services/notification.service");
const { callAIInternal } = require("../services/ai.service");
const { buildRoadmapMutationPayload, buildSessionDetailPayload } = require("../services/userRoadmaps.service");
const { validateTopicAction } = require("../utils/learningSessionState");
const { localizeApiPayload, withApiTimezone } = require("../utils/apiDateTime");

const buildApiData = (req, payload) => {
  const timezone = req.user?.timezone || "UTC";
  return withApiTimezone(localizeApiPayload(payload, timezone), timezone);
};

const PATCH_STATUS = new Set(["active", "paused", "cancelled"]);
const SESSION_PATCH_FIELDS = new Set(["scheduled_date", "status"]);
const SESSION_STATUS_VALUES = new Set(["completed", "skipped"]);
const TERMINAL_TOPIC_STATUSES = new Set(["completed", "skipped"]);
const DATE_ONLY_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

const hasOwn = (obj, key) => Object.prototype.hasOwnProperty.call(obj, key);

const userTimezone = (req) => req.user?.timezone || "UTC";

const assertAiSuccess = (aiResult, fallbackMessage = "Learning update failed") => {
  if (!aiResult || aiResult.status === "error") {
    const message = aiResult?.message || fallbackMessage;
    if (/overlap|locked|learning day|past/i.test(message)) {
      throw new ConflictError(message);
    }
    throw new BadRequestError(message);
  }
};

const buildMutationData = async (req, goalDoc, sessionId = null) =>
  buildApiData(
    req,
    await buildRoadmapMutationPayload(req.userId, goalDoc, userTimezone(req), {
      sessionId,
    }),
  );

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

const loadOwnedTopic = async (goalOid, topicId, userId) => {
  const topicOid = toObjectId(topicId);
  if (!topicOid) {
    throw new BadRequestError("Invalid session id");
  }

  const topic = await RoadmapTopic.findOne({
    _id: topicOid,
    goal_id: goalOid,
    is_deleted: false,
  }).lean();

  if (!topic) {
    throw new NotFoundError("Session not found");
  }

  return { topicOid, topic };
};

/**
 * GET /api/learning/:goalId/sessions/:sessionId
 * Single session detail for roadmap session popup / detail screen.
 */
const getSession = async (req, res, next) => {
  try {
    const { oid: goalOid, goal } = await loadOwnedGoal(req.params.goalId, req.userId);
    await loadOwnedTopic(goalOid, req.params.sessionId, req.userId);

    const payload = await buildSessionDetailPayload(
      goal,
      String(req.params.sessionId),
      userTimezone(req),
    );

    if (!payload.session) {
      throw new NotFoundError("Session not found");
    }

    res.json({
      status: "success",
      data: buildApiData(req, payload),
    });
  } catch (error) {
    next(error);
  }
};

/**
 * PATCH /api/learning/:goalId/sessions/:sessionId
 * Body: { scheduled_date?: "YYYY-MM-DD", status?: "completed" | "skipped" }
 */
const updateSession = async (req, res, next) => {
  try {
    const body = req.body || {};
    const incomingKeys = Object.keys(body);
    const invalidKeys = incomingKeys.filter((key) => !SESSION_PATCH_FIELDS.has(key));
    if (invalidKeys.length > 0) {
      throw new BadRequestError(
        `Invalid session fields: ${invalidKeys.join(", ")}`,
      );
    }
    if (incomingKeys.length === 0) {
      throw new BadRequestError("No valid session fields provided");
    }

    const { oid: goalOid, goal } = await loadOwnedGoal(req.params.goalId, req.userId);
    const { topicOid, topic } = await loadOwnedTopic(
      goalOid,
      req.params.sessionId,
      req.userId,
    );

    if (TERMINAL_TOPIC_STATUSES.has(String(topic.status || "").toLowerCase())) {
      throw new BadRequestError("Completed or skipped sessions cannot be changed.");
    }

    if (hasOwn(body, "scheduled_date")) {
      if (goal.status !== "active") {
        throw new BadRequestError("Only active learning plans accept session date changes.");
      }

      const scheduledDate = String(body.scheduled_date || "").trim();
      if (!DATE_ONLY_PATTERN.test(scheduledDate)) {
        throw new BadRequestError("scheduled_date must be YYYY-MM-DD");
      }

      const aiResult = await callAIInternal("/internal/reschedule-topic", {
        topic_id: String(topicOid),
        goal_id: String(goalOid),
        user_id: String(req.userId),
        scheduled_date: scheduledDate,
      });
      assertAiSuccess(aiResult, "Could not reschedule session");
    }

    if (hasOwn(body, "status")) {
      const status = String(body.status || "").trim().toLowerCase();
      if (!SESSION_STATUS_VALUES.has(status)) {
        throw new BadRequestError('status must be "completed" or "skipped"');
      }

      if (goal.status !== "active") {
        throw new BadRequestError("Only active learning plans accept session status changes.");
      }

      const goalTopics = await RoadmapTopic.find({
        goal_id: goalOid,
        is_deleted: false,
      })
        .sort({ order: 1 })
        .lean();

      const action = status === "completed" ? "complete" : "skip";
      const actionBlock = validateTopicAction({
        topics: goalTopics,
        topicId: topicOid,
        action,
      });
      if (actionBlock) {
        throw new ConflictError(actionBlock.message);
      }

      if (status === "completed") {
        const aiResult = await callAIInternal("/internal/auto-complete-topic", {
          topic_id: String(topicOid),
          goal_id: String(goalOid),
          user_id: String(req.userId),
        });
        assertAiSuccess(aiResult, "Could not complete session");
      } else {
        const aiResult = await callAIInternal("/internal/skip-topic", {
          topic_id: String(topicOid),
          goal_id: String(goalOid),
          user_id: String(req.userId),
        });
        assertAiSuccess(aiResult, "Could not skip session");
      }
    }

    const savedGoal = await LearningGoal.findOne({
      _id: goalOid,
      user_id: req.userId,
      is_deleted: false,
    }).lean();

    res.json({
      status: "success",
      message: "Session updated",
      data: await buildMutationData(req, savedGoal, String(topicOid)),
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

    const { oid, goal } = await loadOwnedGoal(req.params.goalId, req.userId);

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
        req.params.goalId,
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
      goalId: req.params.goalId,
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
  getSession,
  updateSession,
  updateStatus,
  respondToLearningCollaborationInvite,
  respondToLearningCollaborationInviteViaLink,
};

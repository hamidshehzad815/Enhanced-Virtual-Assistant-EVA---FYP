/**
 * Soft-delete a learning goal and related pending items (mirrors AI server learning_delete).
 */

const mongoose = require("mongoose");
const {
  LearningGoal,
  RoadmapTopic,
  Task,
  User,
  ActivityLog,
} = require("../models");
const { NotFoundError } = require("../middleware/errorHandler");

const toObjectId = (value) => {
  try {
    return new mongoose.Types.ObjectId(value);
  } catch {
    return null;
  }
};

const buildCollaboratorNotifications = (goal, ownerUserId, ownerName) => {
  const goalId = String(goal._id);
  const senderName = ownerName || "Your collaborator";
  const subject = String(goal.subject || goal.title || "learning plan").trim();
  const roadmapKey = String(goal.roadmap_key || "").trim();
  const levelPart = roadmapKey && roadmapKey !== "general" ? ` ${roadmapKey}` : "";

  const notifications = [];
  const seen = new Set();

  for (const collaborator of goal.collaborators || []) {
    if (!collaborator || collaborator.status !== "accepted") {
      continue;
    }

    const collaboratorId = String(collaborator.user_id || "");
    if (!collaboratorId || collaboratorId === String(ownerUserId)) {
      continue;
    }

    const dedupeKey = `${collaboratorId}:${goalId}`;
    if (seen.has(dedupeKey)) {
      continue;
    }
    seen.add(dedupeKey);

    notifications.push({
      user_id: collaboratorId,
      sender_id: String(ownerUserId),
      type: "learning_goal_deleted",
      reference_type: "learning_goal",
      reference_id: goalId,
      title: "Shared learning plan removed",
      message: (
        `${senderName} removed ${subject}${levelPart} from their plan. `
        + "Your copy is unaffected."
      ),
      action_required: false,
      delivery_channel: ["push", "in_app"],
    });
  }

  return notifications;
};

/**
 * Soft-delete one owned learning goal, pending topics/tasks, log, and notify collaborators.
 *
 * @returns {{ goal: object, notifications: object[] }}
 */
const softDeleteLearningGoalById = async (goalId, ownerUserId) => {
  const goalOid = toObjectId(goalId);
  const ownerOid = toObjectId(ownerUserId);

  if (!goalOid || !ownerOid) {
    throw new NotFoundError("Learning goal not found");
  }

  const goal = await LearningGoal.findOne({
    _id: goalOid,
    user_id: ownerOid,
    is_deleted: false,
  }).lean();

  if (!goal) {
    throw new NotFoundError("Learning goal not found");
  }

  const now = new Date();

  await LearningGoal.updateOne(
    { _id: goalOid, user_id: ownerOid, is_deleted: false },
    {
      $set: {
        is_deleted: true,
        deleted_at: now,
        updated_at: now,
      },
    },
  );

  await RoadmapTopic.updateMany(
    {
      goal_id: goalOid,
      status: { $in: ["pending", "ongoing"] },
      is_deleted: false,
    },
    {
      $set: {
        is_deleted: true,
        deleted_at: now,
        updated_at: now,
      },
    },
  );

  await Task.updateMany(
    {
      learning_plan_id: goalOid,
      status: { $in: ["pending", "ongoing"] },
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

  try {
    await ActivityLog.create({
      user_id: ownerOid,
      action_type: "goal_deleted",
      subject: goal.subject || null,
      source: "learning_module",
      action_timestamp: now,
    });
  } catch (error) {
    // Non-blocking — same as AI server behavior for log failures.
    console.error("[learningDelete] Activity log insert failed:", error.message);
  }

  const owner = await User.findById(ownerOid).select("name").lean();
  const notifications = buildCollaboratorNotifications(
    goal,
    ownerUserId,
    owner?.name,
  );

  return {
    goal: {
      ...goal,
      is_deleted: true,
      deleted_at: now,
      updated_at: now,
    },
    notifications,
  };
};

module.exports = {
  softDeleteLearningGoalById,
  buildCollaboratorNotifications,
};

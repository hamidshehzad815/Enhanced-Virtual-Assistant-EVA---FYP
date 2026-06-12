/**
 * Learning plan collaboration invites (accept / reject).
 */

const mongoose = require("mongoose");
const { LearningGoal, RoadmapTopic, Task, User, Notification } = require("../models");
const {
  BadRequestError,
  ConflictError,
  NotFoundError,
} = require("../middleware/errorHandler");
const {
  notifyOwnerOfCollaborationResponse,
} = require("./collaborationNotifications");
const {
  findUserCalendarConflicts,
  formatCollaboratorConflictMessage,
  resolveUserTimezone,
} = require("../utils/userCalendarConflicts");

const sameObjectId = (a, b) => String(a) === String(b);

const validateCollaboratorCanAcceptPlan = async (ownerGoal, collaboratorUserId) => {
  const goalOid = ownerGoal._id;
  const collabOid = new mongoose.Types.ObjectId(collaboratorUserId);
  const topics = await RoadmapTopic.find({
    goal_id: goalOid,
    is_deleted: false,
  })
    .sort({ order: 1 })
    .lean();

  const collabUser = await User.findById(collabOid).select("name username").lean();
  const collabName =
    (collabUser && (collabUser.name || collabUser.username)) || "Collaborator";
  const tz = await resolveUserTimezone(collabOid);

  for (const topic of topics) {
    if (!topic.task_id) {
      continue;
    }
    const ownerTask = await Task.findOne({
      _id: topic.task_id,
      is_deleted: { $ne: true },
    }).lean();
    if (!ownerTask || !ownerTask.due_datetime) {
      continue;
    }
    const duration = ownerTask.duration || 120;
    const conflict = await findUserCalendarConflicts(
      collabOid,
      ownerTask.due_datetime,
      duration,
      tz,
    );
    if (conflict) {
      throw new ConflictError(
        formatCollaboratorConflictMessage(collabName, conflict, {
          forLearningPlan: true,
        }),
        { conflict, collaborator_user_id: String(collaboratorUserId) },
      );
    }
  }
};

const markLearningCollaborationNotificationHandled = async ({
  userId,
  goalId,
  action,
  notificationId = null,
}) => {
  const query = {
    user_id: userId,
    type: "learning_collaboration_invite",
    reference_type: "learning_goal",
    reference_id: goalId,
  };

  if (notificationId && mongoose.Types.ObjectId.isValid(notificationId)) {
    query._id = new mongoose.Types.ObjectId(notificationId);
  }

  await Notification.findOneAndUpdate(
    query,
    {
      $set: {
        is_read: true,
        action_taken: action === "accept" ? "accepted" : "rejected",
        action_required: false,
        updated_at: new Date(),
      },
    },
    { sort: { created_at: -1 } },
  );
};

const cloneLearningPlanForCollaborator = async (ownerGoal, collaboratorUserId) => {
  const goalOid = ownerGoal._id;
  const collabOid = new mongoose.Types.ObjectId(collaboratorUserId);
  const now = new Date();

  const topics = await RoadmapTopic.find({
    goal_id: goalOid,
    is_deleted: false,
  })
    .sort({ order: 1 })
    .lean();

  const collabGoal = await LearningGoal.create({
    user_id: collabOid,
    title: ownerGoal.title,
    description: ownerGoal.description,
    subject: ownerGoal.subject,
    roadmap_key: ownerGoal.roadmap_key,
    learning_schedule_id: ownerGoal.learning_schedule_id,
    start_date: ownerGoal.start_date,
    end_date: ownerGoal.end_date,
    duration_days: ownerGoal.duration_days,
    total_topics: ownerGoal.total_topics,
    completed_topics: 0,
    status: "active",
    collaborators: [],
    generated_by: ownerGoal.generated_by || "eva",
    started_at: null,
    completed_at: null,
    time_taken_days: null,
    is_deleted: false,
    created_at: now,
    updated_at: now,
  });

  for (const topic of topics) {
    const newTopic = await RoadmapTopic.create({
      goal_id: collabGoal._id,
      title: topic.title,
      description: topic.description,
      order: topic.order,
      scheduled_date: topic.scheduled_date,
      estimated_duration: topic.estimated_duration,
      resources: topic.resources || [],
      status: "pending",
      completed_at: null,
      is_deleted: false,
    });

    if (!topic.task_id) {
      continue;
    }

    const ownerTask = await Task.findOne({
      _id: topic.task_id,
      is_deleted: { $ne: true },
    }).lean();

    if (!ownerTask) {
      continue;
    }

    const newTask = await Task.create({
      owner_id: collabOid,
      title: ownerTask.title,
      description: ownerTask.description,
      due_datetime: ownerTask.due_datetime,
      duration: ownerTask.duration,
      priority: ownerTask.priority,
      status: "pending",
      source: ownerTask.source || "eva",
      scheduled_by: ownerTask.scheduled_by || "manual",
      collaborators: [],
      learning_plan_id: collabGoal._id,
      learning_topic_id: newTopic._id,
      reminder_minutes_before: ownerTask.reminder_minutes_before,
      is_deleted: false,
      created_at: now,
      updated_at: now,
    });

    await RoadmapTopic.updateOne(
      { _id: newTopic._id },
      { $set: { task_id: newTask._id, updated_at: now } },
    );
  }

  return collabGoal;
};

/**
 * Accept or reject a learning plan collaboration invite.
 */
const applyLearningCollaborationAction = async ({
  goalId,
  collaboratorUserId,
  action,
  notificationId = null,
}) => {
  if (!mongoose.Types.ObjectId.isValid(goalId)) {
    throw new BadRequestError("Invalid learning goal id");
  }

  if (!mongoose.Types.ObjectId.isValid(collaboratorUserId)) {
    throw new BadRequestError("Invalid collaborator id");
  }

  const goalObjectId = new mongoose.Types.ObjectId(goalId);
  const collaboratorObjectId = new mongoose.Types.ObjectId(collaboratorUserId);
  const newStatus = action === "accept" ? "accepted" : "rejected";

  const goal = await LearningGoal.findOne({
    _id: goalObjectId,
    is_deleted: false,
    collaborators: {
      $elemMatch: {
        user_id: collaboratorObjectId,
      },
    },
  }).lean();

  if (!goal) {
    throw new NotFoundError("Learning plan not found for this collaborator");
  }

  const collaboratorRow = Array.isArray(goal.collaborators)
    ? goal.collaborators.find((row) => sameObjectId(row.user_id, collaboratorObjectId))
    : null;

  if (!collaboratorRow) {
    throw new NotFoundError("Collaborator record not found");
  }

  if (String(collaboratorRow.status || "").toLowerCase() !== "pending") {
    await markLearningCollaborationNotificationHandled({
      userId: collaboratorObjectId,
      goalId: goalObjectId,
      action,
      notificationId,
    });
    return {
      goal,
      collaborator_goal_id: null,
      already_responded: true,
      current_status: collaboratorRow.status,
    };
  }

  const updatedGoal = await LearningGoal.findOneAndUpdate(
    {
      _id: goalObjectId,
      is_deleted: false,
      collaborators: {
        $elemMatch: {
          user_id: collaboratorObjectId,
          status: "pending",
        },
      },
    },
    {
      $set: {
        "collaborators.$.status": newStatus,
        updated_at: new Date(),
      },
    },
    { new: true },
  ).lean();

  if (!updatedGoal) {
    throw new ConflictError("This learning invite was already handled");
  }

  let collaboratorGoalId = null;
  if (action === "accept") {
    await validateCollaboratorCanAcceptPlan(updatedGoal, collaboratorUserId);
    const collabGoal = await cloneLearningPlanForCollaborator(
      updatedGoal,
      collaboratorUserId,
    );
    collaboratorGoalId = collabGoal._id;
  }

  await markLearningCollaborationNotificationHandled({
    userId: collaboratorObjectId,
    goalId: goalObjectId,
    action,
    notificationId,
  });

  await notifyOwnerOfCollaborationResponse({
    ownerId: updatedGoal.user_id,
    collaboratorUserId,
    action,
    referenceType: "learning_goal",
    referenceId: goalObjectId,
    itemTitle: updatedGoal.title,
  });

  return {
    goal: updatedGoal,
    collaborator_goal_id: collaboratorGoalId,
    already_responded: false,
    current_status: newStatus,
  };
};

module.exports = {
  applyLearningCollaborationAction,
  cloneLearningPlanForCollaborator,
};

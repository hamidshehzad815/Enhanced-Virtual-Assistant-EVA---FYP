/**
 * Soft-delete a user account: deactivate, anonymize PII, and clean up related data.
 */

const {
  User,
  UserSetting,
  LearningGoal,
  RoadmapTopic,
  Task,
  ChatSession,
  ConversationHistory,
  Friend,
  Integration,
} = require("../models");
const { deleteProfilePicture } = require("./cloudinary.service");
const logger = require("../config/logger");

const buildDeletedIdentity = (userId) => {
  const id = String(userId);
  return {
    email: `del_${id}@deleted.eva`,
    username: `del_${id}`,
    name: "Deleted User",
  };
};

/**
 * @param {import("../models/User")} user - Mongoose user document (may include +profile_picture_public_id)
 */
const softDeleteUserAccount = async (user) => {
  const userId = user._id;
  const now = new Date();
  const identity = buildDeletedIdentity(userId);

  const publicId = String(user.profile_picture_public_id || "").trim();
  if (publicId) {
    try {
      await deleteProfilePicture(publicId);
    } catch (error) {
      logger.warn("Account delete: avatar cleanup failed", {
        userId,
        error: error.message,
      });
    }
  }

  const goalIds = await LearningGoal.find({
    user_id: userId,
    is_deleted: false,
  }).distinct("_id");

  if (goalIds.length > 0) {
    await LearningGoal.updateMany(
      { user_id: userId, is_deleted: false },
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
        goal_id: { $in: goalIds },
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
        learning_plan_id: { $in: goalIds },
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

  await Task.updateMany(
    {
      owner_id: userId,
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

  const sessionIds = await ChatSession.find({
    user_id: userId,
    is_deleted: false,
  }).distinct("_id");

  if (sessionIds.length > 0) {
    await ChatSession.updateMany(
      { user_id: userId, is_deleted: false },
      {
        $set: {
          is_deleted: true,
          deleted_at: now,
        },
      },
    );

    await ConversationHistory.updateMany(
      {
        session_id: { $in: sessionIds },
        is_deleted: false,
      },
      {
        $set: {
          is_deleted: true,
          deleted_at: now,
        },
      },
    );
  }

  await Friend.deleteMany({
    $or: [{ requester_id: userId }, { recipient_id: userId }],
  });

  await Integration.updateMany(
    { user_id: userId },
    { $set: { is_active: false } },
  );

  await UserSetting.updateOne(
    { user_id: userId },
    {
      $set: {
        notifications_enabled: false,
        push_notifications_enabled: false,
        email_notifications_enabled: false,
        google_calendar_sync_enabled: false,
      },
    },
  );

  await User.updateOne(
    { _id: userId },
    {
      $set: {
        ...identity,
        is_active: false,
        is_verified: false,
        profile_picture: null,
        profile_picture_public_id: null,
        bio: null,
        university: null,
        department: null,
        semester: null,
        push_tokens: [],
        refresh_token_hash: null,
        email_verification_token: null,
        email_verification_expires: null,
        password_reset_token: null,
        password_reset_expires: null,
      },
      $unset: {
        password_hash: "",
      },
    },
  );

  logger.info("User account soft-deleted", { userId });
};

module.exports = {
  softDeleteUserAccount,
  buildDeletedIdentity,
};

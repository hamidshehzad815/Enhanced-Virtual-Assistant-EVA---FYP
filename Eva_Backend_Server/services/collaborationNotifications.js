/**
 * Notify plan/task owners when a collaborator accepts or declines an invite.
 */

const { User } = require("../models");
const { insert_and_dispatch } = require("./notification.service");
const logger = require("../config/logger");

const MAX_TITLE_SNIPPET = 80;

const snippetTitle = (title, fallback = "your item") => {
  const trimmed = String(title || "").trim();
  if (!trimmed) {
    return fallback;
  }
  if (trimmed.length <= MAX_TITLE_SNIPPET) {
    return trimmed;
  }
  return `${trimmed.slice(0, MAX_TITLE_SNIPPET - 1)}…`;
};

const resolveCollaboratorDisplayName = (userDoc) => {
  if (!userDoc) {
    return "A collaborator";
  }
  const name = String(userDoc.name || "").trim();
  if (name) {
    return name;
  }
  const username = String(userDoc.username || "").trim();
  if (username) {
    return username;
  }
  const email = String(userDoc.email || "").trim();
  if (email.includes("@")) {
    return email.split("@")[0];
  }
  return "A collaborator";
};

const buildOwnerResponsePayload = ({
  ownerId,
  collaboratorUserId,
  collaboratorName,
  action,
  referenceType,
  referenceId,
  itemTitle,
}) => {
  const isLearning = referenceType === "learning_goal";
  const itemKind = isLearning ? "learning plan" : "task";
  const label = snippetTitle(itemTitle, isLearning ? "your learning plan" : "your task");
  const accepted = action === "accept";

  return {
    user_id: String(ownerId),
    sender_id: String(collaboratorUserId),
    type: isLearning ? "learning_collaboration_response" : "collaboration_response",
    reference_type: referenceType,
    reference_id: String(referenceId),
    title: accepted ? "Collaboration accepted" : "Collaboration declined",
    message: accepted
      ? `${collaboratorName} accepted your ${itemKind} invite for “${label}”.`
      : `${collaboratorName} declined your ${itemKind} invite for “${label}”.`,
    action_required: false,
    delivery_channel: ["push", "in_app", "email"],
    push_data: {
      collaboration_action: accepted ? "accepted" : "rejected",
    },
  };
};

/**
 * @param {object} params
 * @param {string|import('mongoose').Types.ObjectId} params.ownerId
 * @param {string|import('mongoose').Types.ObjectId} params.collaboratorUserId
 * @param {"accept"|"reject"} params.action
 * @param {"task"|"learning_goal"} params.referenceType
 * @param {string|import('mongoose').Types.ObjectId} params.referenceId
 * @param {string} [params.itemTitle]
 */
const notifyOwnerOfCollaborationResponse = async ({
  ownerId,
  collaboratorUserId,
  action,
  referenceType,
  referenceId,
  itemTitle = "",
}) => {
  if (!ownerId || !collaboratorUserId || !referenceId) {
    return { dispatched: false, reason: "missing_required_fields" };
  }

  if (String(ownerId) === String(collaboratorUserId)) {
    return { dispatched: false, reason: "owner_is_collaborator" };
  }

  const collaborator = await User.findById(collaboratorUserId)
    .select("name username email")
    .lean();
  const collaboratorName = resolveCollaboratorDisplayName(collaborator);

  try {
    const summary = await insert_and_dispatch([
      buildOwnerResponsePayload({
        ownerId,
        collaboratorUserId,
        collaboratorName,
        action,
        referenceType,
        referenceId,
        itemTitle,
      }),
    ]);

    return {
      dispatched: summary.inserted > 0,
      summary,
    };
  } catch (error) {
    logger.error("Failed to notify owner of collaboration response", {
      owner_id: String(ownerId),
      collaborator_user_id: String(collaboratorUserId),
      reference_type: referenceType,
      reference_id: String(referenceId),
      error: error.message,
    });
    return { dispatched: false, reason: error.message };
  }
};

module.exports = {
  notifyOwnerOfCollaborationResponse,
  buildOwnerResponsePayload,
  resolveCollaboratorDisplayName,
};

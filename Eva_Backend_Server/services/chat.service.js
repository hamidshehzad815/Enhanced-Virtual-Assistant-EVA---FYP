/**
 * Chat service helpers — session lifecycle and AI response shaping.
 */

const mongoose = require("mongoose");

const { ChatSession } = require("../models");

const CHAT_SESSION_COLLECTION = "chatsessions";
const CONVERSATION_COLLECTION = "conversation_history";

const getConversationCollection = () => {
  const db = mongoose.connection?.db;
  if (!db) {
    throw new Error("MongoDB not connected");
  }
  return db.collection(CONVERSATION_COLLECTION);
};

const DEFAULT_SESSION_TITLE = "New chat";
const MAX_TITLE_LENGTH = 60;
const MAX_PREVIEW_LENGTH = 200;

const DEFAULT_NOTIFICATION_SUMMARY = {
  requested: 0,
  inserted: 0,
  dispatched_push: 0,
  dispatched_email: 0,
  failed: 0,
  results: [],
};

const buildSessionIdVariants = (sessionId) => {
  const idStr = String(sessionId);
  const variants = [idStr];

  if (mongoose.Types.ObjectId.isValid(idStr)) {
    variants.push(new mongoose.Types.ObjectId(idStr));
  }

  return variants;
};

/** Match messages saved by Node (ObjectId) or AI server (string), with or without is_deleted. */
const buildSessionMessageFilter = (sessionId) => ({
  session_id: { $in: buildSessionIdVariants(sessionId) },
  is_deleted: { $ne: true },
});

const deriveSessionTitle = (message) => {
  const trimmed = String(message || "")
    .trim()
    .replace(/\s+/g, " ");
  if (!trimmed) {
    return DEFAULT_SESSION_TITLE;
  }
  if (trimmed.length <= MAX_TITLE_LENGTH) {
    return trimmed;
  }
  return `${trimmed.slice(0, MAX_TITLE_LENGTH - 3)}...`;
};

const extractProcessFields = (aiResponse = {}) => {
  const responseText =
    aiResponse.response_text ||
    aiResponse.route?.response_text ||
    "I processed your request.";

  const routeIntent =
    aiResponse.route?.intent ||
    aiResponse.intent_classification?.label ||
    null;

  const aiStatus = aiResponse.handler_status || aiResponse.status || null;

  const aiNotifications = Array.isArray(aiResponse.notifications)
    ? aiResponse.notifications
    : Array.isArray(aiResponse.route?.notifications)
      ? aiResponse.route.notifications
      : [];

  const learningGoalId =
    aiResponse.route?.learning_goal_id ||
    aiResponse.learning_goal_id ||
    null;

  let action = null;
  if (learningGoalId) {
    action = {
      type: "see_roadmap",
      id: String(learningGoalId),
      label: "See roadmap",
    };
  } else if (
    aiResponse.action &&
    typeof aiResponse.action === "object" &&
    !Array.isArray(aiResponse.action) &&
    aiResponse.action.type &&
    aiResponse.action.id
  ) {
    action = {
      type: String(aiResponse.action.type),
      id: String(aiResponse.action.id),
      label: String(aiResponse.action.label || "Open"),
    };
  }

  return {
    responseText,
    routeIntent,
    aiStatus,
    aiNotifications,
    action,
  };
};

const createChatSession = async (userId, { title } = {}) => {
  return ChatSession.create({
    user_id: userId,
    title: title?.trim() || DEFAULT_SESSION_TITLE,
  });
};

const resolveOwnedSession = async (sessionId, userId) =>
  ChatSession.findOne({
    _id: sessionId,
    user_id: userId,
    is_deleted: false,
  });

const touchSessionAfterMessage = async (
  session,
  { userMessage, responseText },
) => {
  const now = new Date();
  const preview = String(responseText || userMessage || "")
    .trim()
    .slice(0, MAX_PREVIEW_LENGTH);

  const updates = {
    last_message_preview: preview,
    last_message_at: now,
  };

  const currentTitle = String(session.title || "").trim();
  if (!currentTitle || currentTitle === DEFAULT_SESSION_TITLE) {
    updates.title = deriveSessionTitle(userMessage);
  }

  await ChatSession.findByIdAndUpdate(session._id, { $set: updates });
  return { ...session.toObject(), ...updates };
};

const toSessionSummary = (session) => ({
  id: String(session._id),
  title: session.title || DEFAULT_SESSION_TITLE,
  last_message_preview: session.last_message_preview || "",
  last_message_at: session.last_message_at || null,
  created_at: session.created_at || null,
  updated_at: session.updated_at || null,
});

const toMessageDto = (message) => ({
  id: String(message._id),
  role: message.role,
  content: message.content,
  input_type: message.input_type || "text",
  intent: message.intent || null,
  status: message.status || "processed",
  created_at: message.created_at || null,
  action: message.action || null,
});

const softDeleteSession = async (session) => {
  const now = new Date();

  await ChatSession.findByIdAndUpdate(session._id, {
    $set: { is_deleted: true, deleted_at: now },
  });

  await getConversationCollection().updateMany(buildSessionMessageFilter(session._id), {
    $set: { is_deleted: true, deleted_at: now },
  });
};

const roleSortOrder = (role) => (role === "user" ? 0 : 1);

const sortConversationMessages = (messages) =>
  [...messages].sort((left, right) => {
    const leftTime = left.created_at
      ? new Date(left.created_at).getTime()
      : 0;
    const rightTime = right.created_at
      ? new Date(right.created_at).getTime()
      : 0;

    if (leftTime !== rightTime) {
      return leftTime - rightTime;
    }

    const roleDiff = roleSortOrder(left.role) - roleSortOrder(right.role);
    if (roleDiff !== 0) {
      return roleDiff;
    }

    return String(left._id).localeCompare(String(right._id));
  });

const fetchSessionMessages = async (sessionId, limit = 100) => {
  const messages = await getConversationCollection()
    .find(buildSessionMessageFilter(sessionId))
    .sort({ created_at: 1, _id: 1 })
    .limit(limit)
    .toArray();

  return sortConversationMessages(messages);
};

const saveConversationTurn = async (
  sessionId,
  { userMessage, responseText, inputType = "text", intent = null, action = null },
) => {
  const sessionKey = String(sessionId);
  const now = new Date();
  const evaTime = new Date(now.getTime() + 1);

  const evaDoc = {
    session_id: sessionKey,
    role: "eva",
    content: responseText,
    input_type: "text",
    intent,
    status: "processed",
    created_at: evaTime,
  };
  if (action && typeof action === "object") {
    evaDoc.action = {
      type: String(action.type || ""),
      id: String(action.id || ""),
      label: String(action.label || "Open"),
    };
  }

  await getConversationCollection().insertMany([
    {
      session_id: sessionKey,
      role: "user",
      content: userMessage,
      input_type: inputType,
      intent,
      status: "processed",
      created_at: now,
    },
    evaDoc,
  ]);
};

const dedupeMessages = (messages) => {
  const seen = new Set();
  const deduped = [];

  for (const message of messages) {
    const key = [
      message.role,
      message.content,
      message.created_at
        ? new Date(message.created_at).toISOString().slice(0, 19)
        : "",
    ].join("|");

    if (seen.has(key)) {
      continue;
    }

    seen.add(key);
    deduped.push(message);
  }

  return deduped;
};

const softDeleteMessagesForSessions = async (sessionIds) => {
  if (!sessionIds?.length) {
    return;
  }

  const now = new Date();
  const filters = sessionIds.map((sessionId) =>
    buildSessionMessageFilter(sessionId),
  );

  await getConversationCollection().updateMany(
    { $or: filters },
    {
      $set: {
        is_deleted: true,
        deleted_at: now,
      },
    },
  );
};

module.exports = {
  CHAT_SESSION_COLLECTION,
  CONVERSATION_COLLECTION,
  DEFAULT_SESSION_TITLE,
  DEFAULT_NOTIFICATION_SUMMARY,
  deriveSessionTitle,
  extractProcessFields,
  createChatSession,
  resolveOwnedSession,
  touchSessionAfterMessage,
  buildSessionMessageFilter,
  softDeleteSession,
  fetchSessionMessages,
  saveConversationTurn,
  sortConversationMessages,
  dedupeMessages,
  softDeleteMessagesForSessions,
  toSessionSummary,
  toMessageDto,
};

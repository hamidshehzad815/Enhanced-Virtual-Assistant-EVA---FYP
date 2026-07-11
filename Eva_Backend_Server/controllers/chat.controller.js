/**
 * Chat Controller
 * Session lifecycle + AI message processing for the chat UI.
 */

const mongoose = require("mongoose");

const { ChatSession } = require("../models");
const { callAIServer } = require("../services/ai.service");
const { insert_and_dispatch } = require("../services/notification.service");
const {
  DEFAULT_NOTIFICATION_SUMMARY,
  createChatSession,
  extractProcessFields,
  resolveOwnedSession,
  touchSessionAfterMessage,
  buildSessionMessageFilter,
  softDeleteSession,
  fetchSessionMessages,
  saveConversationTurn,
  dedupeMessages,
  toMessageDto,
  toSessionSummary,
} = require("../services/chat.service");
const {
  BadRequestError,
  NotFoundError,
  InternalError,
} = require("../middleware/errorHandler");
const { localizeApiPayload, withApiTimezone } = require("../utils/apiDateTime");

const buildApiData = (req, payload) => {
  const timezone = req.user?.timezone || "UTC";
  return withApiTimezone(localizeApiPayload(payload, timezone), timezone);
};

const parseLimit = (value, fallback = 50, max = 100) => {
  if (value === undefined || value === null || value === "") {
    return fallback;
  }
  const parsed = Number.parseInt(String(value), 10);
  if (Number.isNaN(parsed) || parsed < 1) {
    throw new BadRequestError("limit must be a positive integer");
  }
  return Math.min(parsed, max);
};

/**
 * GET /api/chat/sessions
 * List conversations that have at least one saved message.
 */
const listSessions = async (req, res, next) => {
  try {
    const limit = parseLimit(req.query.limit, 50, 100);

    const sessions = await ChatSession.find({
      user_id: req.userId,
      is_deleted: false,
      last_message_at: { $ne: null },
    })
      .sort({ last_message_at: -1 })
      .limit(limit)
      .lean();

    res.json({
      status: "success",
      data: buildApiData(req, {
        sessions: sessions.map(toSessionSummary),
      }),
    });
  } catch (error) {
    next(error);
  }
};

/**
 * GET /api/chat/sessions/:sessionId/messages
 * Load message history for one owned session.
 */
const getSessionMessages = async (req, res, next) => {
  try {
    const { sessionId } = req.params;

    if (!sessionId || !mongoose.Types.ObjectId.isValid(sessionId)) {
      throw new BadRequestError("valid sessionId is required");
    }

    const session = await resolveOwnedSession(sessionId, req.userId);
    if (!session) {
      throw new NotFoundError("Chat session not found");
    }

    const limit = parseLimit(req.query.limit, 100, 200);

    const messages = await fetchSessionMessages(session._id, limit);

    res.json({
      status: "success",
      data: buildApiData(req, {
        session_id: String(session._id),
        title: session.title,
        messages: dedupeMessages(messages).map(toMessageDto),
      }),
    });
  } catch (error) {
    next(error);
  }
};

/**
 * POST /api/chat/process
 * Send a message to EVA. Creates a session on first message when session_id is omitted.
 */
const processChat = async (req, res, next) => {
  try {
    const { message, session_id: sessionIdRaw, input_type } = req.body;

    if (!message || typeof message !== "string" || !message.trim()) {
      throw new BadRequestError("message is required");
    }

    const normalizedInputType = input_type || "text";
    if (!["text", "voice"].includes(normalizedInputType)) {
      throw new BadRequestError("input_type must be text or voice");
    }

    let session;
    let sessionCreated = false;
    const trimmedMessage = message.trim();

    if (sessionIdRaw) {
      if (!mongoose.Types.ObjectId.isValid(sessionIdRaw)) {
        throw new BadRequestError("valid session_id is required");
      }

      session = await resolveOwnedSession(sessionIdRaw, req.userId);
      if (!session) {
        throw new NotFoundError("Chat session not found");
      }
    } else {
      session = await createChatSession(req.userId);
      sessionCreated = true;
    }

    const aiPayload = {
      message: trimmedMessage,
      user_id: String(req.userId),
      session_id: String(session._id),
      input_type: normalizedInputType,
      timestamp: new Date().toISOString(),
    };

    let aiResponse;
    try {
      aiResponse = await callAIServer(aiPayload);
    } catch (error) {
      if (sessionCreated) {
        await ChatSession.findByIdAndUpdate(session._id, {
          $set: { is_deleted: true, deleted_at: new Date() },
        });
      }
      throw new InternalError(
        `Failed to process message with AI server: ${error.message}`,
      );
    }

    const { responseText, routeIntent, aiStatus, aiNotifications } =
      extractProcessFields(aiResponse);

    let notificationSummary = DEFAULT_NOTIFICATION_SUMMARY;
    try {
      notificationSummary = await insert_and_dispatch(aiNotifications);
    } catch (error) {
      throw new InternalError(
        `Failed to dispatch notifications: ${error.message}`,
      );
    }

    const updatedSession = await touchSessionAfterMessage(session, {
      userMessage: trimmedMessage,
      responseText,
    });

    try {
      await saveConversationTurn(session._id, {
        userMessage: trimmedMessage,
        responseText,
        inputType: normalizedInputType,
        intent: routeIntent,
      });
    } catch (error) {
      throw new InternalError(
        `Failed to save conversation history: ${error.message}`,
      );
    }

    res.json({
      status: "success",
      session_id: String(session._id),
      session_created: sessionCreated,
      title: updatedSession.title,
      response_text: responseText,
      intent: routeIntent,
      ai_status: aiStatus,
      notifications: notificationSummary,
    });
  } catch (error) {
    next(error);
  }
};

/**
 * DELETE /api/chat/sessions/:sessionId
 * Soft-delete one owned chat and its messages.
 */
const deleteSession = async (req, res, next) => {
  try {
    const { sessionId } = req.params;

    if (!sessionId || !mongoose.Types.ObjectId.isValid(sessionId)) {
      throw new BadRequestError("valid sessionId is required");
    }

    const session = await resolveOwnedSession(sessionId, req.userId);
    if (!session) {
      throw new NotFoundError("Chat session not found");
    }

    await softDeleteSession(session);

    res.json({
      status: "success",
      message: "Chat deleted successfully",
      data: buildApiData(req, {
        session_id: String(session._id),
      }),
    });
  } catch (error) {
    next(error);
  }
};

module.exports = {
  listSessions,
  getSessionMessages,
  processChat,
  deleteSession,
};

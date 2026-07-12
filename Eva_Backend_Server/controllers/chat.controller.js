/**
 * Chat Controller
 * Phase 3 endpoints for chat session creation and AI processing.
 */

const mongoose = require("mongoose");
const logger = require("../config/logger");

const { ChatSession, ConversationHistory } = require("../models");
const { callAIServer } = require("../services/ai.service");
const { insert_and_dispatch } = require("../services/notification.service");
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

/**
 * POST /api/chat/session
 * Create a new chat session for the authenticated user.
 */
const listSessions = async (req, res, next) => {
  try {
    const sessions = await ChatSession.find({
      user_id: req.userId,
      is_deleted: false,
    })
      .sort({ last_message_at: -1, created_at: -1 })
      .lean();

    res.json({
      status: "success",
      data: {
        sessions: sessions.map((session) => ({
          session_id: String(session._id),
          title: session.title,
          last_message_preview: session.last_message_preview,
          last_message_at: session.last_message_at,
          created_at: session.created_at,
        })),
      },
    });
  } catch (error) {
    next(error);
  }
};

const getSessionHistory = async (req, res, next) => {
  try {
    const { sessionId } = req.params;
    if (!mongoose.Types.ObjectId.isValid(sessionId)) {
      throw new BadRequestError("Invalid session id");
    }

    const session = await ChatSession.findOne({
      _id: sessionId,
      user_id: req.userId,
      is_deleted: false,
    }).lean();

    if (!session) {
      throw new NotFoundError("Chat session not found");
    }

    const history = await ConversationHistory.find({
      session_id: sessionId,
      is_deleted: false,
    })
      .sort({ created_at: 1 })
      .lean();

    res.json({
      status: "success",
      data: {
        session_id: String(session._id),
        messages: history.map((item) => ({
          id: String(item._id),
          role: item.role,
          content: item.content,
          input_type: item.input_type,
          intent: item.intent,
          created_at: item.created_at,
        })),
      },
    });
  } catch (error) {
    next(error);
  }
};

const createSession = async (req, res, next) => {
  try {
    const { title } = req.body;

    const chatSession = await ChatSession.create({
      user_id: req.userId,
      title: title?.trim() || "New chat",
    });

    res.status(201).json({
      status: "success",
      message: "Chat session created",
      data: buildApiData(req, {
        session_id: chatSession._id,
        session: chatSession.toObject ? chatSession.toObject() : chatSession,
      }),
    });
  } catch (error) {
    next(error);
  }
};

/**
 * POST /api/chat/process
 * Forward user message to AI server with minimal payload.
 */
const processChat = async (req, res, next) => {
  try {
    const { message, session_id, input_type } = req.body;

    if (!message || typeof message !== "string" || !message.trim()) {
      throw new BadRequestError("message is required");
    }

    if (!session_id || !mongoose.Types.ObjectId.isValid(session_id)) {
      throw new BadRequestError("valid session_id is required");
    }

    const normalizedInputType = input_type || "text";
    if (!["text", "voice"].includes(normalizedInputType)) {
      throw new BadRequestError("input_type must be text or voice");
    }

    const session = await ChatSession.findOne({
      _id: session_id,
      user_id: req.userId,
      is_deleted: false,
    });

    if (!session) {
      throw new NotFoundError("Chat session not found");
    }

    const aiPayload = {
      message: message.trim(),
      user_id: String(req.userId),
      session_id: String(session_id),
      input_type: normalizedInputType,
      timestamp: new Date().toISOString(),
    };

    const userMessageRecord = {
      session_id: session_id,
      role: 'user',
      content: message.trim(),
      input_type: normalizedInputType,
      intent: null,
      status: 'processed',
    };

    let aiResponse;
    const requestStart = Date.now();
    try {
      aiResponse = await callAIServer(aiPayload);
    } catch (error) {
      throw new InternalError(
        `Failed to process message with AI server: ${error.message}`,
      );
    }

    const responseText =
      aiResponse?.response_text ||
      aiResponse?.route?.response_text ||
      'I processed your request.';

    const routeIntent =
      aiResponse?.route?.intent ||
      aiResponse?.intent_classification?.label ||
      null;

    const evaMessageRecord = {
      session_id: session_id,
      role: 'eva',
      content: responseText,
      input_type: normalizedInputType,
      intent: routeIntent,
      status: 'processed',
      response_time_ms: Date.now() - requestStart,
    };

    const aiNotifications = Array.isArray(aiResponse?.notifications)
      ? aiResponse.notifications
      : Array.isArray(aiResponse?.route?.notifications)
        ? aiResponse.route.notifications
        : [];

    let notificationSummary;
    try {
      notificationSummary = await insert_and_dispatch(aiNotifications);
    } catch (error) {
      throw new InternalError(
        `Failed to dispatch notifications: ${error.message}`,
      );
    }

    try {
      await ConversationHistory.create([userMessageRecord, evaMessageRecord]);
    } catch (saveError) {
      logger.warn('Failed to persist chat history', {
        session_id,
        error: saveError.message,
      });
    }

    try {
      await ChatSession.findByIdAndUpdate(
        session_id,
        {
          last_message_preview: responseText.slice(0, 200),
          last_message_at: new Date(),
        },
        { new: true },
      );
    } catch (_updateError) {
      // Session recency update is best-effort and should not fail the request.
    }

    const localizedAiResponse = buildApiData(req, aiResponse || {});

    res.json({
      status: "success",
      response_text: responseText,
      session_id,
      intent: routeIntent,
      ai_status: aiResponse?.handler_status || aiResponse?.status || null,
      notifications: notificationSummary,
      data: localizedAiResponse,
    });
  } catch (error) {
    next(error);
  }
};

module.exports = {
  listSessions,
  getSessionHistory,
  createSession,
  processChat,
};

/**
 * Chat Controller
 * Phase 3 endpoints for chat session creation and AI processing.
 */

const mongoose = require("mongoose");

const { ChatSession } = require("../models");
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

    let aiResponse;
    try {
      aiResponse = await callAIServer(aiPayload);
    } catch (error) {
      throw new InternalError(
        `Failed to process message with AI server: ${error.message}`,
      );
    }

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

    const responseText =
      aiResponse?.response_text ||
      aiResponse?.route?.response_text ||
      "I processed your request.";

    const routeIntent =
      aiResponse?.route?.intent ||
      aiResponse?.intent_classification?.label ||
      null;

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
  createSession,
  processChat,
};

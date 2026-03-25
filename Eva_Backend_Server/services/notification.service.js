/**
 * Notification Service
 * Persists notifications and dispatches push/email channels.
 */

const nodemailer = require("nodemailer");
const mongoose = require("mongoose");

const logger = require("../config/logger");
const { Notification, User, UserSetting } = require("../models");

const SMTP_HOST = process.env.SMTP_HOST || process.env.EMAIL_HOST;
const SMTP_PORT = Number(process.env.SMTP_PORT || process.env.EMAIL_PORT || 587);
const SMTP_SECURE =
  String(process.env.SMTP_SECURE || "false").toLowerCase() === "true";
const SMTP_USER = process.env.SMTP_USER || process.env.EMAIL_USER;
const SMTP_PASS = process.env.SMTP_PASS || process.env.EMAIL_PASS;
const SMTP_FROM =
  process.env.SMTP_FROM ||
  process.env.EMAIL_FROM ||
  process.env.EMAIL_USER ||
  "no-reply@eva.local";

let cachedTransporter = null;

const toObjectId = (value) => {
  if (!value) {
    return null;
  }

  if (value instanceof mongoose.Types.ObjectId) {
    return value;
  }

  if (mongoose.Types.ObjectId.isValid(value)) {
    return new mongoose.Types.ObjectId(value);
  }

  return null;
};

const getTransporter = () => {
  if (cachedTransporter) {
    return cachedTransporter;
  }

  if (!SMTP_HOST || !SMTP_USER || !SMTP_PASS) {
    return null;
  }

  cachedTransporter = nodemailer.createTransport({
    host: SMTP_HOST,
    port: SMTP_PORT,
    secure: SMTP_SECURE,
    auth: {
      user: SMTP_USER,
      pass: SMTP_PASS,
    },
  });

  return cachedTransporter;
};

const normalizeChannels = (channels) => {
  if (!Array.isArray(channels) || channels.length === 0) {
    return ["in_app"];
  }

  const allowed = new Set(["push", "in_app", "email"]);
  const normalized = channels
    .map((channel) =>
      String(channel || "")
        .trim()
        .toLowerCase(),
    )
    .filter((channel) => allowed.has(channel));

  return normalized.length ? Array.from(new Set(normalized)) : ["in_app"];
};

const buildNotificationDoc = (payload) => {
  const userId = toObjectId(payload.user_id);
  if (!userId) {
    throw new Error("Invalid notification user_id");
  }

  const referenceId = toObjectId(payload.reference_id);
  const senderId = toObjectId(payload.sender_id);

  const doc = {
    user_id: userId,
    sender_id: senderId,
    type: payload.type,
    title: String(payload.title || "").trim(),
    message: String(payload.message || "").trim(),
    reference_type: payload.reference_type || null,
    reference_id: referenceId,
    action_required: Boolean(payload.action_required),
    delivery_channel: normalizeChannels(payload.delivery_channel),
    scheduled_at: payload.scheduled_at ? new Date(payload.scheduled_at) : null,
    expires_at: payload.expires_at ? new Date(payload.expires_at) : null,
  };

  if (!doc.type || !doc.title || !doc.message) {
    throw new Error("Notification type, title, and message are required");
  }

  return doc;
};

const dispatch_push = async (userId, notification) => {
  // Placeholder dispatch path until FCM tokens are introduced in schema.
  logger.info("Push dispatch queued", {
    user_id: String(userId),
    notification_type: notification.type,
    notification_id: String(notification._id),
  });

  return {
    dispatched: false,
    channel: "push",
    reason: "FCM integration not configured yet",
  };
};

const dispatch_email = async (userId, notification, userDoc) => {
  if (!userDoc?.email) {
    return {
      dispatched: false,
      channel: "email",
      reason: "Recipient email not available",
    };
  }

  const transporter = getTransporter();
  if (!transporter) {
    return {
      dispatched: false,
      channel: "email",
      reason: "SMTP not configured",
    };
  }

  try {
    await transporter.sendMail({
      from: SMTP_FROM,
      to: userDoc.email,
      subject: notification.title,
      text: notification.message,
    });

    return {
      dispatched: true,
      channel: "email",
    };
  } catch (error) {
    logger.error("Email dispatch failed", {
      user_id: String(userId),
      notification_id: String(notification._id),
      error: error.message,
    });

    return {
      dispatched: false,
      channel: "email",
      reason: error.message,
    };
  }
};

const insert_and_dispatch = async (notifications = []) => {
  if (!Array.isArray(notifications) || notifications.length === 0) {
    return {
      requested: 0,
      inserted: 0,
      dispatched_push: 0,
      dispatched_email: 0,
      failed: 0,
      results: [],
    };
  }

  const summary = {
    requested: notifications.length,
    inserted: 0,
    dispatched_push: 0,
    dispatched_email: 0,
    failed: 0,
    results: [],
  };

  for (const payload of notifications) {
    try {
      const doc = buildNotificationDoc(payload);
      const saved = await Notification.create(doc);
      summary.inserted += 1;

      const userSettings = await UserSetting.findOne({
        user_id: doc.user_id,
      }).lean();
      const userDoc = await User.findById(doc.user_id)
        .select("email name username")
        .lean();

      const channels = saved.delivery_channel || ["in_app"];
      const channelResults = [];

      if (channels.includes("push")) {
        const pushEnabled = userSettings?.push_notifications_enabled !== false;
        if (pushEnabled) {
          const result = await dispatch_push(doc.user_id, saved);
          channelResults.push(result);
          if (result.dispatched) {
            summary.dispatched_push += 1;
          }
        } else {
          channelResults.push({
            dispatched: false,
            channel: "push",
            reason: "User push notifications disabled",
          });
        }
      }

      if (channels.includes("email")) {
        const emailEnabled = userSettings?.email_notifications_enabled === true;
        if (emailEnabled) {
          const result = await dispatch_email(doc.user_id, saved, userDoc);
          channelResults.push(result);
          if (result.dispatched) {
            summary.dispatched_email += 1;
          }
        } else {
          channelResults.push({
            dispatched: false,
            channel: "email",
            reason: "User email notifications disabled",
          });
        }
      }

      saved.sent_at = new Date();
      await saved.save();

      summary.results.push({
        notification_id: String(saved._id),
        user_id: String(saved.user_id),
        channels,
        channel_results: channelResults,
      });
    } catch (error) {
      summary.failed += 1;
      summary.results.push({
        error: error.message,
        payload,
      });
      logger.error("Notification insert_and_dispatch item failed", {
        error: error.message,
      });
    }
  }

  return summary;
};

module.exports = {
  dispatch_push,
  dispatch_email,
  insert_and_dispatch,
};

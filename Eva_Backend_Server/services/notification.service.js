/**
 * Notification Service
 * Persists notifications and dispatches push/email channels.
 */

const mongoose = require("mongoose");
const fs = require("fs");
const path = require("path");
const jwt = require("jsonwebtoken");

const logger = require("../config/logger");
const { Notification, User, UserSetting } = require("../models");
const { buildTokenLink } = require("../utils/publicUrl");
const { sendEmail, isEmailConfigured } = require("./email.service");

let cachedFirebaseAdmin = undefined;

const getFirebaseAdmin = () => {
  if (cachedFirebaseAdmin !== undefined) {
    return cachedFirebaseAdmin;
  }

  let admin = null;
  try {
    admin = require("firebase-admin");
  } catch (_error) {
    cachedFirebaseAdmin = null;
    return null;
  }

  const credentialsSource =
    process.env.FIREBASE_SERVICE_ACCOUNT_JSON ||
    process.env.FIREBASE_CREDENTIALS ||
    "";
  if (!credentialsSource) {
    cachedFirebaseAdmin = null;
    return null;
  }

  let serviceAccount = null;
  const trimmed = credentialsSource.trim();
  try {
    if (trimmed.startsWith("{")) {
      serviceAccount = JSON.parse(trimmed);
    } else {
      const resolvedPath = path.isAbsolute(trimmed)
        ? trimmed
        : path.resolve(process.cwd(), trimmed);
      if (fs.existsSync(resolvedPath)) {
        const raw = fs.readFileSync(resolvedPath, "utf8");
        serviceAccount = JSON.parse(raw);
      }
    }
  } catch (_error) {
    cachedFirebaseAdmin = null;
    return null;
  }

  if (!serviceAccount) {
    cachedFirebaseAdmin = null;
    return null;
  }

  try {
    if (!admin.apps.length) {
      admin.initializeApp({
        credential: admin.credential.cert(serviceAccount),
      });
    }
    cachedFirebaseAdmin = admin;
    return admin;
  } catch (_error) {
    cachedFirebaseAdmin = null;
    return null;
  }
};

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

const getCollaborationTokenSecret = () =>
  process.env.COLLAB_ACTION_SECRET || process.env.JWT_ACCESS_SECRET || "";

const buildCollaborationActionLink = ({
  notificationId,
  referenceId,
  referenceType = "task",
  recipientId,
  action,
}) => {
  const secret = getCollaborationTokenSecret();
  if (!secret) {
    return null;
  }

  const refType = String(referenceType || "task").trim().toLowerCase();
  const refId = String(referenceId || "");

  const payload = {
    notification_id: String(notificationId),
    reference_type: refType,
    reference_id: refId,
    user_id: String(recipientId),
    action: String(action),
  };

  if (refType === "task") {
    payload.task_id = refId;
  }

  const token = jwt.sign(payload, secret, { expiresIn: "72h" });

  const path =
    refType === "learning_goal"
      ? "/api/learning/collaboration/respond"
      : "/api/tasks/collaboration/respond";

  return buildTokenLink(null, path, token);
};

const buildCollaborationInviteEmail = ({ notification, userDoc }) => {
  const isLearning = notification.type === "learning_collaboration_invite";
  const referenceType = isLearning ? "learning_goal" : "task";
  const refLabel = isLearning ? "Learning plan ID" : "Task ID";
  const refValue = String(notification.reference_id || "");

  const acceptLink = buildCollaborationActionLink({
    notificationId: notification._id,
    referenceId: notification.reference_id,
    referenceType,
    recipientId: notification.user_id,
    action: "accept",
  });
  const rejectLink = buildCollaborationActionLink({
    notificationId: notification._id,
    referenceId: notification.reference_id,
    referenceType,
    recipientId: notification.user_id,
    action: "reject",
  });

  const plainText = [
    `Hello ${userDoc?.name || "there"},`,
    "",
    notification.message,
    "",
    "Respond to this collaboration invite:",
    `Accept: ${acceptLink || "Link unavailable (missing COLLAB_ACTION_SECRET)"}`,
    `Reject: ${rejectLink || "Link unavailable (missing COLLAB_ACTION_SECRET)"}`,
    "",
    `${refLabel}: ${refValue}`,
  ].join("\n");

  const html = `
  <div style="font-family: Arial, sans-serif; line-height:1.5; max-width: 620px; margin:0 auto;">
    <h2 style="margin-bottom: 8px;">${notification.title}</h2>
    <p>${notification.message}</p>
    <p style="margin: 18px 0 10px;">Respond to this collaboration invite:</p>
    <div style="display:flex; gap:10px; margin-bottom: 16px;">
      ${
    acceptLink
      ? `<a href="${acceptLink}" style="background:#16a34a;color:#fff;text-decoration:none;padding:10px 16px;border-radius:8px;font-weight:600;">Accept</a>`
      : ""
  }
      ${
    rejectLink
      ? `<a href="${rejectLink}" style="background:#dc2626;color:#fff;text-decoration:none;padding:10px 16px;border-radius:8px;font-weight:600;">Reject</a>`
      : ""
  }
    </div>
    <p style="font-size:12px;color:#666;">${refLabel}: ${refValue}</p>
  </div>
  `;

  return {
    text: plainText,
    html,
  };
};

const isMasterNotificationsEnabled = (userSettings) =>
  userSettings?.notifications_enabled !== false;

const isPushEnabled = (userSettings) =>
  isMasterNotificationsEnabled(userSettings)
  && userSettings?.push_notifications_enabled !== false;

const isEmailEnabled = (userSettings, notificationType) => {
  if (!isMasterNotificationsEnabled(userSettings)) {
    return false;
  }

  const forceEmailForInvite = (
    notificationType === "collaboration_invite"
    || notificationType === "learning_collaboration_invite"
  );
  if (forceEmailForInvite) {
    return true;
  }

  return userSettings?.email_notifications_enabled === true;
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

const normalizePushTokens = (userDoc) => {
  if (!Array.isArray(userDoc?.push_tokens)) {
    return [];
  }

  return Array.from(
    new Set(
      userDoc.push_tokens
        .map((token) => String(token || "").trim())
        .filter((token) => token.length > 0),
    ),
  );
};

const removeInvalidPushTokens = async (userId, tokens) => {
  if (!tokens.length) {
    return;
  }

  await User.updateOne(
    { _id: userId },
    {
      $pull: {
        push_tokens: { $in: tokens },
      },
    },
  );
};

const dispatch_push = async (userId, notification, userDoc, extraPushData = {}) => {
  const admin = getFirebaseAdmin();
  if (!admin) {
    logger.warn("Push dispatch skipped: Firebase not configured", {
      user_id: String(userId),
      notification_id: String(notification?._id || ""),
    });
    return {
      dispatched: false,
      channel: "push",
      reason: "Firebase Admin SDK not configured",
    };
  }

  const tokens = normalizePushTokens(userDoc);
  if (!tokens.length) {
    logger.warn("Push dispatch skipped: no registered device tokens", {
      user_id: String(userId),
      notification_id: String(notification?._id || ""),
    });
    return {
      dispatched: false,
      channel: "push",
      reason: "No device push tokens registered",
    };
  }

  const baseData = {
    notification_id: String(notification._id),
    type: String(notification.type || ""),
    reference_type: String(notification.reference_type || ""),
    reference_id: String(notification.reference_id || ""),
  };
  const merged = { ...baseData };
  if (extraPushData && typeof extraPushData === "object") {
    Object.entries(extraPushData).forEach(([key, value]) => {
      if (value === undefined || value === null) {
        return;
      }
      merged[String(key)] = String(value);
    });
  }

  try {
    const response = await admin.messaging().sendEachForMulticast({
      tokens,
      notification: {
        title: notification.title,
        body: notification.message,
      },
      data: merged,
    });

    const invalidTokens = [];
    response.responses.forEach((result, index) => {
      if (result.success) {
        return;
      }
      const code = String(result.error?.code || "");
      logger.warn("Push token rejected by FCM", {
        user_id: String(userId),
        notification_id: String(notification?._id || ""),
        error_code: code,
        error_message: String(result.error?.message || ""),
      });
      if (
        code.includes("registration-token-not-registered")
        || code.includes("invalid-registration-token")
        || code.includes("mismatched-credential")
      ) {
        invalidTokens.push(tokens[index]);
      }
    });

    await removeInvalidPushTokens(userId, invalidTokens);

    if (response.successCount > 0) {
      logger.info("Push dispatched", {
        user_id: String(userId),
        notification_id: String(notification._id),
        success_count: response.successCount,
        failure_count: response.failureCount,
      });
    }

    return {
      dispatched: response.successCount > 0,
      channel: "push",
      success_count: response.successCount,
      failure_count: response.failureCount,
      reason:
        response.successCount > 0
          ? undefined
          : "FCM rejected all target tokens",
    };
  } catch (error) {
    logger.error("Push dispatch failed", {
      user_id: String(userId),
      notification_id: String(notification._id),
      error: error.message,
    });

    return {
      dispatched: false,
      channel: "push",
      reason: error.message,
    };
  }
};

const dispatch_email = async (userId, notification, userDoc) => {
  if (!userDoc?.email) {
    return {
      dispatched: false,
      channel: "email",
      reason: "Recipient email not available",
    };
  }

  if (!isEmailConfigured()) {
    return {
      dispatched: false,
      channel: "email",
      reason: "Email not configured",
    };
  }

  try {
    const messagePayload =
      notification?.type === "collaboration_invite"
      || notification?.type === "learning_collaboration_invite"
        ? buildCollaborationInviteEmail({ notification, userDoc })
        : {
          text: notification.message,
          html: `<p style="font-family: Arial, sans-serif; line-height:1.5;">${notification.message}</p>`,
        };

    const sent = await sendEmail({
      to: userDoc.email,
      subject: notification.title,
      text: messagePayload.text,
      html: messagePayload.html,
    });

    if (!sent) {
      return {
        dispatched: false,
        channel: "email",
        reason: "Email send failed",
      };
    }

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

const emptySummary = () => ({
  requested: 0,
  inserted: 0,
  dispatched_push: 0,
  dispatched_email: 0,
  skipped: 0,
  failed: 0,
  results: [],
});

const insert_and_dispatch = async (notifications = []) => {
  if (!Array.isArray(notifications) || notifications.length === 0) {
    return emptySummary();
  }

  const summary = {
    requested: notifications.length,
    inserted: 0,
    dispatched_push: 0,
    dispatched_email: 0,
    skipped: 0,
    failed: 0,
    results: [],
  };

  for (const payload of notifications) {
    try {
      const doc = buildNotificationDoc(payload);

      const userSettings = await UserSetting.findOne({
        user_id: doc.user_id,
      }).lean();

      if (!isMasterNotificationsEnabled(userSettings)) {
        summary.skipped += 1;
        summary.results.push({
          user_id: String(doc.user_id),
          skipped: true,
          reason: "User notifications disabled",
        });
        continue;
      }

      const saved = await Notification.create(doc);
      summary.inserted += 1;

      const userDoc = await User.findById(doc.user_id)
        .select("email name username push_tokens")
        .lean();

      const channels = saved.delivery_channel || ["in_app"];
      const channelResults = [];
      let anyChannelDispatched = channels.includes("in_app");

      if (channels.includes("push")) {
        if (isPushEnabled(userSettings)) {
          const result = await dispatch_push(
            doc.user_id,
            saved,
            userDoc,
            payload.push_data || {},
          );
          channelResults.push(result);
          if (result.dispatched) {
            summary.dispatched_push += 1;
            anyChannelDispatched = true;
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
        if (isEmailEnabled(userSettings, saved.type)) {
          const result = await dispatch_email(doc.user_id, saved, userDoc);
          channelResults.push(result);
          if (result.dispatched) {
            summary.dispatched_email += 1;
            anyChannelDispatched = true;
          }
        } else {
          channelResults.push({
            dispatched: false,
            channel: "email",
            reason: "User email notifications disabled",
          });
        }
      }

      if (anyChannelDispatched) {
        saved.sent_at = new Date();
        await saved.save();
      }

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
  isMasterNotificationsEnabled,
  isPushEnabled,
  isEmailEnabled,
};

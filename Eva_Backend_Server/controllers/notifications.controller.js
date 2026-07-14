/**
 * Notifications Controller
 * In-app notification inbox APIs for the authenticated user.
 *
 * Response shapes (for the Flutter client). Every endpoint is scoped to the
 * authenticated user (req.userId) — a user can only read/modify their own rows.
 *
 *   GET /api/notifications?limit&skip&unread_only
 *     { status, data: {
 *         notifications: [{ _id, type, title, message, reference_type, reference_id,
 *           is_read, action_required, action_taken, delivery_channel, sent_at,
 *           created_at, sender: { _id, name, username, profile_picture } | null }],
 *         pagination: { limit, skip, total, has_more },
 *         unread_count } }
 *
 *   GET /api/notifications/unread-count
 *     { status, data: { unread_count } }
 *
 *   PATCH /api/notifications/:id/read      -> { status, data: { notification } }
 *                                             (404 if the id isn't the user's)
 *   PATCH /api/notifications/read-all      -> { status, data: { marked_read } }
 */

const mongoose = require("mongoose");
const { Notification } = require("../models");
const { BadRequestError, NotFoundError } = require("../middleware/errorHandler");
const { localizeApiPayload, withApiTimezone } = require("../utils/apiDateTime");

const buildApiData = (req, payload) => {
  const timezone = (req.user && req.user.timezone) || "UTC";
  return withApiTimezone(localizeApiPayload(payload, timezone), timezone);
};

const mapNotification = (doc) => {
  const sender = doc.sender_id;
  const senderObj =
    sender && typeof sender === "object" && sender._id
      ? {
        _id: sender._id,
        name: sender.name,
        username: sender.username,
        profile_picture: sender.profile_picture || null,
      }
      : sender
        ? { _id: sender }
        : null;

  return {
    _id: doc._id,
    type: doc.type,
    title: doc.title,
    message: doc.message,
    reference_type: doc.reference_type || null,
    reference_id: doc.reference_id || null,
    is_read: Boolean(doc.is_read),
    action_required: Boolean(doc.action_required),
    action_taken: doc.action_taken || null,
    delivery_channel: doc.delivery_channel || ["in_app"],
    sent_at: doc.sent_at || null,
    created_at: doc.created_at,
    sender: senderObj,
  };
};

const parsePagination = (req) => {
  const limitRaw = Number.parseInt(String(req.query.limit || "20"), 10);
  const skipRaw = Number.parseInt(String(req.query.skip || "0"), 10);
  const limit = Number.isInteger(limitRaw) ? Math.max(1, Math.min(limitRaw, 100)) : 20;
  const skip = Number.isInteger(skipRaw) ? Math.max(0, skipRaw) : 0;
  return { limit, skip };
};

/**
 * GET /api/notifications
 * List notifications for the authenticated user.
 */
const listNotifications = async (req, res, next) => {
  try {
    const { limit, skip } = parsePagination(req);
    const unreadOnly =
      String(req.query.unread_only || req.query.unread || "false").toLowerCase()
      === "true";

    const query = { user_id: req.userId };
    if (unreadOnly) {
      query.is_read = false;
    }

    const [notifications, total, unreadCount] = await Promise.all([
      Notification.find(query)
        .sort({ created_at: -1 })
        .skip(skip)
        .limit(limit)
        .populate("sender_id", "name username profile_picture")
        .lean(),
      Notification.countDocuments(query),
      Notification.countDocuments({ user_id: req.userId, is_read: false }),
    ]);

    res.json({
      status: "success",
      data: buildApiData(req, {
        notifications: notifications.map(mapNotification),
        pagination: {
          limit,
          skip,
          total,
          has_more: skip + notifications.length < total,
        },
        unread_count: unreadCount,
      }),
    });
  } catch (error) {
    next(error);
  }
};

/**
 * GET /api/notifications/unread-count
 */
const getUnreadCount = async (req, res, next) => {
  try {
    const unreadCount = await Notification.countDocuments({
      user_id: req.userId,
      is_read: false,
    });

    res.json({
      status: "success",
      data: buildApiData(req, { unread_count: unreadCount }),
    });
  } catch (error) {
    next(error);
  }
};

/**
 * PATCH /api/notifications/:id/read
 */
const markNotificationRead = async (req, res, next) => {
  try {
    const notificationId = String(req.params.id || "").trim();
    if (!mongoose.Types.ObjectId.isValid(notificationId)) {
      throw new BadRequestError("Invalid notification id");
    }

    const updated = await Notification.findOneAndUpdate(
      {
        _id: notificationId,
        user_id: req.userId,
      },
      { $set: { is_read: true } },
      { new: true },
    )
      .populate("sender_id", "name username profile_picture")
      .lean();

    if (!updated) {
      throw new NotFoundError("Notification not found");
    }

    res.json({
      status: "success",
      data: buildApiData(req, {
        notification: mapNotification(updated),
      }),
    });
  } catch (error) {
    next(error);
  }
};

/**
 * PATCH /api/notifications/read-all
 */
const markAllNotificationsRead = async (req, res, next) => {
  try {
    const result = await Notification.updateMany(
      { user_id: req.userId, is_read: false },
      { $set: { is_read: true } },
    );

    res.json({
      status: "success",
      data: buildApiData(req, {
        marked_read: result.modifiedCount || 0,
      }),
    });
  } catch (error) {
    next(error);
  }
};

module.exports = {
  listNotifications,
  getUnreadCount,
  markNotificationRead,
  markAllNotificationsRead,
};

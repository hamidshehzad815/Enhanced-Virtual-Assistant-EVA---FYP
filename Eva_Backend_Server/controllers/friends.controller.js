/**
 * Friends Controller
 * Friend request and relationship management endpoints.
 */

const mongoose = require("mongoose");
const { User, UserSetting, Friend } = require("../models");
const {
  BadRequestError,
  NotFoundError,
  ConflictError,
  ForbiddenError,
} = require("../middleware/errorHandler");
const { localizeApiPayload, withApiTimezone } = require("../utils/apiDateTime");
const { insert_and_dispatch } = require("../services/notification.service");
const { isAcceptingFriendRequests } = require("../utils/friendSettings");

const buildApiData = (req, payload) => {
  const timezone = (req.user && req.user.timezone) || "UTC";
  return withApiTimezone(localizeApiPayload(payload, timezone), timezone);
};

const userTz = (req) => (req.user && req.user.timezone) || "UTC";
const mapForRequest = (req, friendship) =>
  mapRelationship(friendship, req.userId, userTz(req));

const ALLOWED_RESPONSES = new Set(["accept", "reject"]);
const ALLOWED_REQUEST_FILTERS = new Set(["incoming", "outgoing", "all"]);

const dispatchFriendNotification = async ({
  recipientId,
  senderId,
  type,
  friendshipId,
  title,
  message,
  actionRequired = false,
}) => {
  if (!recipientId || !senderId || String(recipientId) === String(senderId)) {
    return;
  }

  try {
    await insert_and_dispatch([
      {
        user_id: String(recipientId),
        sender_id: String(senderId),
        type,
        reference_type: "friend",
        reference_id: String(friendshipId),
        title,
        message,
        action_required: actionRequired,
        delivery_channel: ["push", "in_app"],
      },
    ]);
  } catch (_error) {
    // Friend request should succeed even if notification dispatch fails.
  }
};

const sanitizeUser = (userDoc) => {
  if (!userDoc) {
    return null;
  }

  return {
    _id: userDoc._id,
    name: userDoc.name,
    username: userDoc.username,
    email: userDoc.email,
    profile_picture: userDoc.profile_picture || null,
  };
};

const idString = (value) => {
  if (!value) {
    return "";
  }
  if (typeof value === "object" && value._id) {
    return String(value._id);
  }
  return String(value);
};

const isParticipant = (friendship, userId) =>
  idString(friendship.requester_id) === String(userId)
  || idString(friendship.recipient_id) === String(userId);

const mapRelationship = (friendship, currentUserId, timezone = "UTC") => {
  const requester = sanitizeUser(friendship.requester_id);
  const recipient = sanitizeUser(friendship.recipient_id);
  const isRequester = idString(requester?._id) === String(currentUserId);

  const row = {
    _id: friendship._id,
    status: friendship.status,
    responded_at: friendship.responded_at,
    blocked_by: friendship.blocked_by || null,
    created_at: friendship.created_at,
    updated_at: friendship.updated_at,
    requester,
    recipient,
    direction: isRequester ? "outgoing" : "incoming",
    friend: isRequester ? recipient : requester,
  };

  return localizeApiPayload(row, timezone);
};

const escapeRegExp = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

const loadRelationship = async (id) => {
  if (!mongoose.Types.ObjectId.isValid(id)) {
    throw new BadRequestError("Invalid friendship id");
  }

  const friendship = await Friend.findById(id)
    .populate("requester_id", "name username email profile_picture")
    .populate("recipient_id", "name username email profile_picture")
    .lean();

  if (!friendship) {
    throw new NotFoundError("Friendship not found");
  }

  return friendship;
};

const loadTargetUserById = async (userId) => {
  if (!mongoose.Types.ObjectId.isValid(userId)) {
    throw new BadRequestError("Invalid user id");
  }

  const targetUser = await User.findById(userId)
    .select("name username email profile_picture is_active")
    .lean();

  if (!targetUser || !targetUser.is_active) {
    throw new NotFoundError("Target user not found");
  }

  return targetUser;
};

const buildBlockedCounterpartyIdSet = (relationships, currentUserId) => {
  const blockedIds = new Set();
  for (const relationship of relationships) {
    const requesterId = idString(relationship.requester_id);
    const recipientId = idString(relationship.recipient_id);
    const otherId = requesterId === String(currentUserId) ? recipientId : requesterId;
    if (otherId) {
      blockedIds.add(otherId);
    }
  }
  return blockedIds;
};

/**
 * POST /api/friends/request
 * Send a friend request by username or email.
 */
const sendFriendRequest = async (req, res, next) => {
  try {
    const username = String(req.body.username || "").trim().toLowerCase();
    const email = String(req.body.email || "").trim().toLowerCase();

    if (!username && !email) {
      throw new BadRequestError("username or email is required");
    }

    const targetUser = await User.findOne(
      username ? { username } : { email },
    );

    if (!targetUser || !targetUser.is_active) {
      throw new NotFoundError("Target user not found");
    }

    if (String(targetUser._id) === String(req.userId)) {
      throw new BadRequestError("You cannot send a friend request to yourself");
    }

    const targetSettings = await UserSetting.findOne({ user_id: targetUser._id })
      .select("allow_friend_requests")
      .lean();

    if (!isAcceptingFriendRequests(targetSettings)) {
      throw new ForbiddenError("This user is not accepting friend requests");
    }

    const pairKey = Friend.buildPairKey(req.userId, targetUser._id);
    const existing = await Friend.findOne({ pair_key: pairKey });

    if (!existing) {
      const friendship = await Friend.create({
        requester_id: req.userId,
        recipient_id: targetUser._id,
        status: "pending",
      });

      const hydrated = await Friend.findById(friendship._id)
        .populate("requester_id", "name username email profile_picture")
        .populate("recipient_id", "name username email profile_picture")
        .lean();

      const requesterName = hydrated.requester_id?.name
        || hydrated.requester_id?.username
        || "Someone";
      await dispatchFriendNotification({
        recipientId: targetUser._id,
        senderId: req.userId,
        type: "friend_request",
        friendshipId: friendship._id,
        title: "New friend request",
        message: `${requesterName} sent you a friend request.`,
        actionRequired: true,
      });

      return res.status(201).json({
        status: "success",
        message: "Friend request sent",
        data: {
          friendship: mapForRequest(req, hydrated),
        },
      });
    }

    if (existing.status === "accepted") {
      throw new ConflictError("You are already friends");
    }

    if (existing.status === "blocked") {
      throw new ForbiddenError("Friend request cannot be sent due to block status");
    }

    if (existing.status === "pending") {
      if (String(existing.requester_id) === String(req.userId)) {
        throw new ConflictError("Friend request already sent");
      }

      throw new ConflictError("This user already sent you a friend request");
    }

    existing.requester_id = req.userId;
    existing.recipient_id = targetUser._id;
    existing.status = "pending";
    existing.responded_at = null;
    existing.blocked_by = null;
    await existing.save();

    const refreshed = await Friend.findById(existing._id)
      .populate("requester_id", "name username email profile_picture")
      .populate("recipient_id", "name username email profile_picture")
      .lean();

    const requesterName = refreshed.requester_id?.name
      || refreshed.requester_id?.username
      || "Someone";
    await dispatchFriendNotification({
      recipientId: targetUser._id,
      senderId: req.userId,
      type: "friend_request",
      friendshipId: existing._id,
      title: "New friend request",
      message: `${requesterName} sent you a friend request.`,
      actionRequired: true,
    });

    return res.json({
      status: "success",
      message: "Friend request sent",
      data: {
        friendship: mapForRequest(req, refreshed),
      },
    });
  } catch (error) {
    return next(error);
  }
};

/**
 * GET /api/friends
 * List accepted friends for current user.
 */
const listFriends = async (req, res, next) => {
  try {
    const relationships = await Friend.find({
      status: "accepted",
      $or: [
        { requester_id: req.userId },
        { recipient_id: req.userId },
      ],
    })
      .sort({ updated_at: -1 })
      .populate("requester_id", "name username email profile_picture")
      .populate("recipient_id", "name username email profile_picture")
      .lean();

    const friends = relationships.map((relationship) => {
      const mapped = mapForRequest(req, relationship);
      return {
        friendship_id: mapped._id,
        since: mapped.responded_at || mapped.created_at,
        friend: mapped.friend,
      };
    });

    res.json({
      status: "success",
      data: {
        friends,
      },
    });
  } catch (error) {
    next(error);
  }
};

/**
 * GET /api/friends/requests
 * List incoming/outgoing friend requests.
 */
const listFriendRequests = async (req, res, next) => {
  try {
    const type = String(req.query.type || "incoming").toLowerCase();
    if (!ALLOWED_REQUEST_FILTERS.has(type)) {
      throw new BadRequestError("type must be incoming, outgoing, or all");
    }

    const query = { status: "pending" };
    if (type === "incoming") {
      query.recipient_id = req.userId;
    } else if (type === "outgoing") {
      query.requester_id = req.userId;
    } else {
      query.$or = [
        { requester_id: req.userId },
        { recipient_id: req.userId },
      ];
    }

    const requests = await Friend.find(query)
      .sort({ created_at: -1 })
      .populate("requester_id", "name username email profile_picture")
      .populate("recipient_id", "name username email profile_picture")
      .lean();

    res.json({
      status: "success",
      data: {
        requests: requests.map((request) => mapForRequest(req, request)),
      },
    });
  } catch (error) {
    next(error);
  }
};

/**
 * GET /api/friends/blocked
 * List users blocked by the authenticated user.
 */
const listBlockedUsers = async (req, res, next) => {
  try {
    const relationships = await Friend.find({
      status: "blocked",
      blocked_by: req.userId,
      $or: [
        { requester_id: req.userId },
        { recipient_id: req.userId },
      ],
    })
      .sort({ updated_at: -1 })
      .populate("requester_id", "name username email profile_picture")
      .populate("recipient_id", "name username email profile_picture")
      .lean();

    const blocked = relationships.map((relationship) => {
      const mapped = mapForRequest(req, relationship);
      return {
        friendship_id: mapped._id,
        blocked_at: mapped.responded_at || mapped.updated_at,
        user: mapped.friend,
      };
    });

    res.json({
      status: "success",
      data: {
        blocked,
      },
    });
  } catch (error) {
    next(error);
  }
};

/**
 * GET /api/friends/search
 * Search users for friend requests. Blocked users are hidden.
 */
const searchUsers = async (req, res, next) => {
  try {
    const q = String(req.query.q || "").trim();
    const limitRaw = Number.parseInt(String(req.query.limit || "10"), 10);
    const limit = Number.isInteger(limitRaw) ? Math.max(1, Math.min(limitRaw, 50)) : 10;

    if (!q || q.length < 2) {
      throw new BadRequestError("q must be at least 2 characters");
    }

    const blockedRelationships = await Friend.find({
      status: "blocked",
      $or: [
        { requester_id: req.userId },
        { recipient_id: req.userId },
      ],
    })
      .select("requester_id recipient_id")
      .lean();

    const blockedIds = buildBlockedCounterpartyIdSet(blockedRelationships, req.userId);
    const escaped = escapeRegExp(q);
    const searchRegex = new RegExp(escaped, "i");

    const users = await User.find({
      _id: { $ne: req.userId },
      is_active: true,
      username: searchRegex,
    })
      .select("name username email profile_picture")
      .sort({ username: 1 })
      .limit(limit * 3)
      .lean();

    const notBlockedUsers = users.filter((user) => !blockedIds.has(String(user._id)));

    const candidateIds = notBlockedUsers.map((user) => user._id);
    let relationshipMap = new Map();

    if (candidateIds.length > 0) {
      const relationships = await Friend.find({
        $or: [
          { requester_id: req.userId, recipient_id: { $in: candidateIds } },
          { recipient_id: req.userId, requester_id: { $in: candidateIds } },
        ],
      })
        .select("requester_id recipient_id status")
        .lean();

      relationshipMap = new Map(
        relationships.map((relationship) => {
          const requesterId = idString(relationship.requester_id);
          const recipientId = idString(relationship.recipient_id);
          const otherId = requesterId === String(req.userId) ? recipientId : requesterId;
          return [otherId, relationship.status];
        }),
      );
    }

    let closedToRequestsIds = new Set();
    if (candidateIds.length > 0) {
      const closedSettings = await UserSetting.find({
        user_id: { $in: candidateIds },
        allow_friend_requests: "nobody",
      })
        .select("user_id")
        .lean();
      closedToRequestsIds = new Set(
        closedSettings.map((entry) => String(entry.user_id)),
      );
    }

    const visibleUsers = notBlockedUsers
      .filter((user) => {
        const userId = String(user._id);
        const relationshipStatus = relationshipMap.get(userId) || "none";
        if (relationshipStatus !== "none") {
          return true;
        }
        return !closedToRequestsIds.has(userId);
      })
      .slice(0, limit);

    res.json({
      status: "success",
      data: {
        users: visibleUsers.map((user) => ({
          _id: user._id,
          name: user.name,
          username: user.username,
          email: user.email,
          profile_picture: user.profile_picture || null,
          relationship_status: relationshipMap.get(String(user._id)) || "none",
        })),
      },
    });
  } catch (error) {
    next(error);
  }
};

/**
 * PATCH /api/friends/:id/respond
 * Accept or reject an incoming request.
 */
const respondToFriendRequest = async (req, res, next) => {
  try {
    const action = String(req.body.action || "").trim().toLowerCase();
    if (!ALLOWED_RESPONSES.has(action)) {
      throw new BadRequestError("action must be accept or reject");
    }

    const friendship = await loadRelationship(req.params.id);

    if (String(friendship.recipient_id._id) !== String(req.userId)) {
      throw new ForbiddenError("Only the recipient can respond to this request");
    }

    if (friendship.status !== "pending") {
      throw new ConflictError("This friend request is no longer pending");
    }

    const status = action === "accept" ? "accepted" : "rejected";
    const updated = await Friend.findByIdAndUpdate(
      friendship._id,
      {
        $set: {
          status,
          responded_at: new Date(),
          blocked_by: null,
        },
      },
      { new: true },
    )
      .populate("requester_id", "name username email profile_picture")
      .populate("recipient_id", "name username email profile_picture")
      .lean();

    if (action === "accept") {
      const accepterName = updated.recipient_id?.name
        || updated.recipient_id?.username
        || "Someone";
      await dispatchFriendNotification({
        recipientId: updated.requester_id._id,
        senderId: req.userId,
        type: "friend_accepted",
        friendshipId: updated._id,
        title: "Friend request accepted",
        message: `${accepterName} accepted your friend request.`,
      });
    }

    res.json({
      status: "success",
      message: `Friend request ${status}`,
      data: {
        friendship: mapForRequest(req, updated),
      },
    });
  } catch (error) {
    next(error);
  }
};

/**
 * POST /api/friends/block/:userId
 * Block a user by user id.
 */
const blockFriend = async (req, res, next) => {
  try {
    const targetUser = await loadTargetUserById(req.params.userId);
    if (String(targetUser._id) === String(req.userId)) {
      throw new BadRequestError("You cannot block yourself");
    }

    const pairKey = Friend.buildPairKey(req.userId, targetUser._id);
    const existing = await Friend.findOne({ pair_key: pairKey });

    let relationshipId;
    if (!existing) {
      const created = await Friend.create({
        requester_id: req.userId,
        recipient_id: targetUser._id,
        status: "blocked",
        blocked_by: req.userId,
        responded_at: new Date(),
      });
      relationshipId = created._id;
    } else {
      await Friend.updateOne(
        { _id: existing._id },
        {
          $set: {
            status: "blocked",
            blocked_by: req.userId,
            responded_at: new Date(),
          },
        },
      );
      relationshipId = existing._id;
    }

    const updated = await Friend.findById(relationshipId)
      .populate("requester_id", "name username email profile_picture")
      .populate("recipient_id", "name username email profile_picture")
      .lean();

    res.json({
      status: "success",
      message: "User blocked",
      data: {
        friendship: mapForRequest(req, updated),
      },
    });
  } catch (error) {
    next(error);
  }
};

/**
 * POST /api/friends/unblock/:userId
 * Unblock a user by user id.
 */
const unblockFriend = async (req, res, next) => {
  try {
    const targetUser = await loadTargetUserById(req.params.userId);
    const pairKey = Friend.buildPairKey(req.userId, targetUser._id);
    const friendship = await Friend.findOne({ pair_key: pairKey })
      .populate("requester_id", "name username email profile_picture")
      .populate("recipient_id", "name username email profile_picture")
      .lean();

    if (!friendship) {
      throw new NotFoundError("Relationship not found");
    }

    if (!isParticipant(friendship, req.userId)) {
      throw new ForbiddenError("You are not allowed to unblock this relationship");
    }

    if (friendship.status !== "blocked") {
      throw new ConflictError("Only blocked relationships can be unblocked");
    }

    if (idString(friendship.blocked_by) !== String(req.userId)) {
      throw new ForbiddenError("Only the user who blocked can unblock");
    }

    const updated = await Friend.findByIdAndUpdate(
      friendship._id,
      {
        $set: {
          status: "rejected",
          responded_at: new Date(),
          blocked_by: null,
        },
      },
      { new: true },
    )
      .populate("requester_id", "name username email profile_picture")
      .populate("recipient_id", "name username email profile_picture")
      .lean();

    res.json({
      status: "success",
      message: "User blocked",
      data: {
        friendship: mapForRequest(req, updated),
      },
    });
  } catch (error) {
    next(error);
  }
};

/**
 * DELETE /api/friends/:id
 * Unfriend by removing an accepted relationship.
 */
const unfriend = async (req, res, next) => {
  try {
    const friendship = await loadRelationship(req.params.id);

    if (!isParticipant(friendship, req.userId)) {
      throw new ForbiddenError("You are not allowed to unfriend this relationship");
    }

    if (friendship.status !== "accepted") {
      throw new ConflictError("Only accepted friendships can be unfriended");
    }

    await Friend.deleteOne({ _id: friendship._id });

    res.json({
      status: "success",
      message: "Friend removed",
      data: {
        friendship_id: friendship._id,
      },
    });
  } catch (error) {
    next(error);
  }
};

module.exports = {
  sendFriendRequest,
  listFriends,
  listFriendRequests,
  listBlockedUsers,
  searchUsers,
  respondToFriendRequest,
  blockFriend,
  unblockFriend,
  unfriend,
};

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

const ALLOWED_RESPONSES = new Set(["accept", "reject"]);
const ALLOWED_REQUEST_FILTERS = new Set(["incoming", "outgoing", "all"]);

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

const isParticipant = (friendship, userId) =>
  String(friendship.requester_id) === String(userId)
  || String(friendship.recipient_id) === String(userId);

const mapRelationship = (friendship, currentUserId) => {
  const requester = sanitizeUser(friendship.requester_id);
  const recipient = sanitizeUser(friendship.recipient_id);
  const isRequester = String(requester?._id) === String(currentUserId);

  return {
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
};

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

    if (
      targetSettings
      && targetSettings.allow_friend_requests === "nobody"
    ) {
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

      return res.status(201).json({
        status: "success",
        message: "Friend request sent",
        data: {
          friendship: mapRelationship(hydrated, req.userId),
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

    return res.json({
      status: "success",
      message: "Friend request sent",
      data: {
        friendship: mapRelationship(refreshed, req.userId),
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
      const mapped = mapRelationship(relationship, req.userId);
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
        requests: requests.map((request) => mapRelationship(request, req.userId)),
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

    res.json({
      status: "success",
      message: `Friend request ${status}`,
      data: {
        friendship: mapRelationship(updated, req.userId),
      },
    });
  } catch (error) {
    next(error);
  }
};

/**
 * POST /api/friends/:id/block
 * Block the other user in this relationship.
 */
const blockFriend = async (req, res, next) => {
  try {
    const friendship = await loadRelationship(req.params.id);

    if (!isParticipant(friendship, req.userId)) {
      throw new ForbiddenError("You are not allowed to block this relationship");
    }

    const updated = await Friend.findByIdAndUpdate(
      friendship._id,
      {
        $set: {
          status: "blocked",
          blocked_by: req.userId,
          responded_at: new Date(),
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
        friendship: mapRelationship(updated, req.userId),
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
  respondToFriendRequest,
  blockFriend,
};

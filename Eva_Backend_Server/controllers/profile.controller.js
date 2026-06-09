/**
 * Profile Controller
 * Authenticated user profile read/update endpoints.
 */

const { User } = require("../models");
const { BadRequestError, ConflictError } = require("../middleware/errorHandler");
const { localizeApiPayload, withApiTimezone } = require("../utils/apiDateTime");
const { replaceProfilePicture } = require("../services/cloudinary.service");

const buildApiData = (req, payload) => {
  const timezone = (req.user && req.user.timezone) || "UTC";
  return withApiTimezone(localizeApiPayload(payload, timezone), timezone);
};

const ALLOWED_UPDATES = new Set([
  "name",
  "username",
  "bio",
  "university",
  "department",
  "semester",
  "timezone",
]);

const hasOwn = (obj, key) => Object.prototype.hasOwnProperty.call(obj, key);

const normalizeOptionalString = (value) => {
  if (value === undefined) {
    return undefined;
  }
  if (value === null) {
    return null;
  }
  return String(value).trim();
};

const parseSemester = (value) => {
  if (value === undefined) {
    return undefined;
  }
  if (value === null || value === "") {
    return null;
  }

  const parsed = typeof value === "number"
    ? value
    : Number.parseInt(String(value).trim(), 10);

  if (!Number.isInteger(parsed)) {
    throw new BadRequestError("semester must be an integer");
  }

  return parsed;
};

/**
 * GET /api/profile
 * Return authenticated user's public profile.
 */
const getProfile = async (req, res, next) => {
  try {
    res.json({
      status: "success",
      data: buildApiData(req, {
        user: req.user.toPublicProfile(),
      }),
    });
  } catch (error) {
    next(error);
  }
};

/**
 * PATCH /api/profile
 * Update authenticated user's profile fields.
 * Profile pictures are updated via POST /api/profile/avatar only.
 */
const updateProfile = async (req, res, next) => {
  try {
    const update = {};

    const incomingKeys = Object.keys(req.body || {});
    const invalidKeys = incomingKeys.filter((key) => !ALLOWED_UPDATES.has(key));
    if (invalidKeys.length > 0) {
      throw new BadRequestError(
        `Invalid profile fields: ${invalidKeys.join(", ")}`,
      );
    }

    if (hasOwn(req.body, "name")) {
      const name = normalizeOptionalString(req.body.name);
      if (!name) {
        throw new BadRequestError("name is required");
      }
      update.name = name;
    }

    if (hasOwn(req.body, "username")) {
      const username = normalizeOptionalString(req.body.username);
      if (!username) {
        throw new BadRequestError("username is required");
      }
      update.username = username.toLowerCase();
    }

    if (hasOwn(req.body, "bio")) {
      const bio = normalizeOptionalString(req.body.bio);
      update.bio = bio || null;
    }

    if (hasOwn(req.body, "university")) {
      const university = normalizeOptionalString(req.body.university);
      update.university = university || null;
    }

    if (hasOwn(req.body, "department")) {
      const department = normalizeOptionalString(req.body.department);
      update.department = department || null;
    }

    if (hasOwn(req.body, "semester")) {
      update.semester = parseSemester(req.body.semester);
    }

    if (hasOwn(req.body, "timezone")) {
      const timezone = normalizeOptionalString(req.body.timezone);
      if (!timezone) {
        throw new BadRequestError("timezone is required");
      }
      update.timezone = timezone;
    }

    if (Object.keys(update).length === 0) {
      throw new BadRequestError("No valid profile fields provided");
    }

    if (
      update.username
      && update.username !== String(req.user.username || "").toLowerCase()
    ) {
      const existing = await User.findOne({
        username: update.username,
        _id: { $ne: req.userId },
      }).lean();
      if (existing) {
        throw new ConflictError("Username already taken");
      }
    }

    const updatedUser = await User.findByIdAndUpdate(
      req.userId,
      { $set: update },
      {
        new: true,
        runValidators: true,
      },
    );

    res.json({
      status: "success",
      message: "Profile updated",
      data: buildApiData(req, {
        user: updatedUser.toPublicProfile(),
      }),
    });
  } catch (error) {
    next(error);
  }
};

/**
 * POST /api/profile/avatar
 * Upload or replace the authenticated user's profile picture via Cloudinary.
 */
const uploadAvatar = async (req, res, next) => {
  try {
    if (!req.file) {
      throw new BadRequestError('avatar file is required (multipart field "avatar")');
    }

    const currentUser = await User.findById(req.userId).select(
      "+profile_picture_public_id",
    );
    if (!currentUser) {
      throw new BadRequestError("User not found");
    }

    const uploaded = await replaceProfilePicture(
      req.userId,
      req.file,
      currentUser.profile_picture_public_id,
    );

    const updatedUser = await User.findByIdAndUpdate(
      req.userId,
      {
        $set: {
          profile_picture: uploaded.secure_url,
          profile_picture_public_id: uploaded.public_id,
        },
      },
      {
        new: true,
        runValidators: true,
      },
    );

    res.json({
      status: "success",
      message: "Profile picture updated",
      data: buildApiData(req, {
        user: updatedUser.toPublicProfile(),
      }),
    });
  } catch (error) {
    next(error);
  }
};

module.exports = {
  getProfile,
  updateProfile,
  uploadAvatar,
};

/**
 * Cloudinary upload/delete helpers for user profile pictures.
 */
const logger = require("../config/logger");
const {
  ensureCloudinaryConfigured,
  getProfileFolder,
} = require("../config/cloudinary");
const { BadRequestError } = require("../middleware/errorHandler");

const AVATAR_SIZE = 400;

const uploadBuffer = (buffer, options = {}) =>
  new Promise((resolve, reject) => {
    const client = ensureCloudinaryConfigured();
    const stream = client.uploader.upload_stream(options, (error, result) => {
      if (error) {
        reject(error);
        return;
      }
      resolve(result);
    });
    stream.end(buffer);
  });

const uploadProfilePicture = async (userId, file) => {
  if (!file || !file.buffer) {
    throw new BadRequestError("avatar file is required");
  }

  const folder = getProfileFolder();
  const publicId = `${String(userId)}_${Date.now()}`;

  try {
    const result = await uploadBuffer(file.buffer, {
      folder,
      public_id: publicId,
      resource_type: "image",
      overwrite: false,
      transformation: [
        {
          width: AVATAR_SIZE,
          height: AVATAR_SIZE,
          crop: "fill",
          gravity: "auto",
        },
      ],
    });

    return {
      secure_url: result.secure_url,
      public_id: result.public_id,
    };
  } catch (error) {
    logger.error("Cloudinary profile upload failed", {
      userId: String(userId),
      message: error.message,
    });
    const uploadError = new Error("Failed to upload profile picture");
    uploadError.statusCode = 502;
    uploadError.isOperational = true;
    throw uploadError;
  }
};

const deleteProfilePicture = async (publicId) => {
  const normalized = String(publicId || "").trim();
  if (!normalized) {
    return;
  }

  try {
    const client = ensureCloudinaryConfigured();
    await client.uploader.destroy(normalized, { resource_type: "image" });
  } catch (error) {
    logger.warn("Cloudinary profile delete failed", {
      publicId: normalized,
      message: error.message,
    });
  }
};

const replaceProfilePicture = async (userId, file, previousPublicId) => {
  const uploaded = await uploadProfilePicture(userId, file);
  if (previousPublicId) {
    await deleteProfilePicture(previousPublicId);
  }
  return uploaded;
};

module.exports = {
  uploadProfilePicture,
  deleteProfilePicture,
  replaceProfilePicture,
};

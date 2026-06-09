/**
 * Cloudinary SDK configuration for profile picture uploads.
 */
const cloudinary = require("cloudinary").v2;

const getCloudinaryConfig = () => ({
  cloud_name: process.env.CLOUDINARY_CLOUD_NAME || "",
  api_key: process.env.CLOUDINARY_API_KEY || "",
  api_secret: process.env.CLOUDINARY_API_SECRET || "",
});

const isCloudinaryConfigured = () => {
  const { cloud_name, api_key, api_secret } = getCloudinaryConfig();
  return Boolean(cloud_name && api_key && api_secret);
};

let configured = false;

const ensureCloudinaryConfigured = () => {
  if (configured) {
    return cloudinary;
  }

  if (!isCloudinaryConfigured()) {
    const error = new Error("Cloudinary is not configured");
    error.statusCode = 503;
    error.isOperational = true;
    throw error;
  }

  cloudinary.config(getCloudinaryConfig());
  configured = true;
  return cloudinary;
};

const getProfileFolder = () =>
  String(process.env.CLOUDINARY_PROFILE_FOLDER || "eva/profile-pictures").trim();

module.exports = {
  cloudinary,
  ensureCloudinaryConfigured,
  isCloudinaryConfigured,
  getProfileFolder,
};

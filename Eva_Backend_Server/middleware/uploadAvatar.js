/**
 * Multer middleware for profile avatar uploads.
 */
const multer = require("multer");
const { BadRequestError } = require("./errorHandler");

const ALLOWED_MIME_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
]);

const maxSizeMb = Number.parseFloat(process.env.AVATAR_MAX_SIZE_MB || "2");
const maxFileSizeBytes = Math.max(1, maxSizeMb) * 1024 * 1024;

const storage = multer.memoryStorage();

const upload = multer({
  storage,
  limits: {
    files: 1,
    fileSize: maxFileSizeBytes,
  },
  fileFilter: (_req, file, callback) => {
    if (!ALLOWED_MIME_TYPES.has(file.mimetype)) {
      callback(
        new BadRequestError("avatar must be a JPEG, PNG, or WebP image"),
      );
      return;
    }
    callback(null, true);
  },
});

const uploadAvatarMiddleware = (req, res, next) => {
  upload.single("avatar")(req, res, (error) => {
    if (error) {
      next(error);
      return;
    }
    next();
  });
};

module.exports = {
  uploadAvatarMiddleware,
  maxFileSizeBytes,
};

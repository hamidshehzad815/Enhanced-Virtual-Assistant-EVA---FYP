/**
 * Profile Routes
 */

const express = require("express");
const rateLimit = require("express-rate-limit");

const router = express.Router();

const { protect } = require("../middleware/auth");
const { uploadAvatarMiddleware } = require("../middleware/uploadAvatar");
const {
  getProfile,
  updateProfile,
  uploadAvatar,
} = require("../controllers/profile.controller");

const avatarUploadLimiter = rateLimit({
  windowMs: 60 * 60 * 1000,
  max: 10,
  message: {
    status: "fail",
    message: "Too many profile picture uploads, please try again later",
  },
  standardHeaders: true,
  legacyHeaders: false,
});

router.get("/", protect, getProfile);
router.patch("/", protect, updateProfile);
router.post(
  "/avatar",
  protect,
  avatarUploadLimiter,
  uploadAvatarMiddleware,
  uploadAvatar,
);

module.exports = router;

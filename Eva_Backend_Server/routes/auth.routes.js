/**
 * Authentication Routes
 */

const express = require("express");
const router = express.Router();
const { protect } = require("../middleware/auth");
const {
  register,
  login,
  refresh,
  logout,
  getMe,
  verifyEmail,
  resendVerification,
} = require("../controllers/auth.controller");

// Public routes
router.post("/register", register);
router.post("/login", login);
router.post("/refresh", refresh);
router.get("/verify-email", verifyEmail);
router.post("/resend-verification", resendVerification);

// Protected routes
router.post("/logout", protect, logout);
router.get("/me", protect, getMe);

module.exports = router;

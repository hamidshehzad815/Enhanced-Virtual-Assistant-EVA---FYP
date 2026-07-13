/**
 * Authentication Routes
 */

const express = require("express");
const router = express.Router();
const { protect } = require("../middleware/auth");
const {
  register,
  login,
  googleAuth,
  refresh,
  logout,
  getMe,
  verifyEmail,
  resendVerification,
  forgotPassword,
  resetPassword,
  renderResetPasswordPage,
} = require("../controllers/auth.controller");

// Public routes
router.post("/register", register);
router.post("/login", login);
router.post("/google", googleAuth);
router.post("/refresh", refresh);
router.get("/verify-email", verifyEmail);
router.post("/resend-verification", resendVerification);
router.post("/forgot-password", forgotPassword);
// GET serves the reset-password web form; POST performs the reset.
router.get("/reset-password", renderResetPasswordPage);
router.post("/reset-password", resetPassword);

// Protected routes
router.post("/logout", protect, logout);
router.get("/me", protect, getMe);

module.exports = router;

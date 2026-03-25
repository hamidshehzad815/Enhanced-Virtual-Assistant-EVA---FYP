/**
 * Chat Routes
 */

const express = require("express");
const router = express.Router();

const { protect } = require("../middleware/auth");
const { createSession, processChat } = require("../controllers/chat.controller");

// Protected routes
router.post("/session", protect, createSession);
router.post("/process", protect, processChat);

module.exports = router;

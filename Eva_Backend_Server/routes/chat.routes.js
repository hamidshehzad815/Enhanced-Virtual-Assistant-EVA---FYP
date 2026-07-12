/**
 * Chat Routes
 */

const express = require("express");
const router = express.Router();

const { protect } = require("../middleware/auth");
const { createSession, processChat, listSessions, getSessionHistory } = require("../controllers/chat.controller");

// Protected routes
router.get("/sessions", protect, listSessions);
router.get("/sessions/:sessionId/history", protect, getSessionHistory);
router.post("/session", protect, createSession);
router.post("/process", protect, processChat);

module.exports = router;

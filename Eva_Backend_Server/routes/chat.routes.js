/**
 * Chat Routes
 */

const express = require("express");
const router = express.Router();

const { protect } = require("../middleware/auth");
const {
  listSessions,
  getSessionMessages,
  processChat,
  deleteSession,
} = require("../controllers/chat.controller");

// Protected routes
router.get("/sessions", protect, listSessions);
router.get("/sessions/:sessionId/messages", protect, getSessionMessages);
router.delete("/sessions/:sessionId", protect, deleteSession);
router.post("/process", protect, processChat);

module.exports = router;

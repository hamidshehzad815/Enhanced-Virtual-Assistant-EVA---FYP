/**
 * Learning goals API
 */

const express = require("express");
const router = express.Router();

const { protect } = require("../middleware/auth");
const {
  getSession,
  updateSession,
  updateStatus,
  respondToLearningCollaborationInvite,
  respondToLearningCollaborationInviteViaLink,
} = require("../controllers/learning.controller");

router.get("/collaboration/respond", respondToLearningCollaborationInviteViaLink);
router.post("/:goalId/collaborators/respond", protect, respondToLearningCollaborationInvite);
router.get("/:goalId/sessions/:sessionId", protect, getSession);
router.patch("/:goalId/sessions/:sessionId", protect, updateSession);
router.patch("/:goalId/status", protect, updateStatus);

module.exports = router;

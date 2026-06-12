/**
 * Learning goals API
 */

const express = require("express");
const router = express.Router();

const { protect } = require("../middleware/auth");
const {
  updateSession,
  completeTopic,
  skipTopic,
  updateStatus,
  deleteGoal,
  respondToLearningCollaborationInvite,
  respondToLearningCollaborationInviteViaLink,
} = require("../controllers/learning.controller");

router.get("/collaboration/respond", respondToLearningCollaborationInviteViaLink);
router.post("/:goalId/collaborators/respond", protect, respondToLearningCollaborationInvite);
router.patch("/:goalId/sessions/:sessionId", protect, updateSession);
router.post("/:goalId/topics/:topicId/complete", protect, completeTopic);
router.post("/:goalId/topics/:topicId/skip", protect, skipTopic);
router.delete("/:goalId", protect, deleteGoal);
router.patch("/:goalId/status", protect, updateStatus);

module.exports = router;

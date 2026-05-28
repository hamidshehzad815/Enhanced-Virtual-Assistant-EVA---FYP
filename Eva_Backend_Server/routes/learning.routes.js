/**
 * Learning goals API
 */

const express = require("express");
const router = express.Router();

const { protect } = require("../middleware/auth");
const {
  getAllGoals,
  getGoal,
  getTopics,
  completeTopic,
  updateStatus,
  deleteGoal,
  respondToLearningCollaborationInvite,
  respondToLearningCollaborationInviteViaLink,
} = require("../controllers/learning.controller");

router.get("/collaboration/respond", respondToLearningCollaborationInviteViaLink);
router.get("/", protect, getAllGoals);
router.post("/:id/collaborators/respond", protect, respondToLearningCollaborationInvite);
router.get("/:id/topics", protect, getTopics);
router.post("/:id/topics/:topicId/complete", protect, completeTopic);
router.get("/:id", protect, getGoal);
router.delete("/:id", protect, deleteGoal);
router.patch("/:id/status", protect, updateStatus);

module.exports = router;

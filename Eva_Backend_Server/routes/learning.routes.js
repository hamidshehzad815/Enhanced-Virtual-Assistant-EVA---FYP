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
} = require("../controllers/learning.controller");

router.get("/", protect, getAllGoals);
router.get("/:id/topics", protect, getTopics);
router.post("/:id/topics/:topicId/complete", protect, completeTopic);
router.get("/:id", protect, getGoal);
router.patch("/:id/status", protect, updateStatus);

module.exports = router;

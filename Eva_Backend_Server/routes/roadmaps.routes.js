/**
 * User roadmap routes (learning goals owned by the authenticated user).
 */

const express = require("express");
const router = express.Router();

const { protect } = require("../middleware/auth");
const {
  getUserRoadmapPlans,
  getUserRoadmapByGoalId,
} = require("../controllers/roadmaps.controller");

router.get("/plans", protect, getUserRoadmapPlans);
router.get("/:goalId", protect, getUserRoadmapByGoalId);

module.exports = router;

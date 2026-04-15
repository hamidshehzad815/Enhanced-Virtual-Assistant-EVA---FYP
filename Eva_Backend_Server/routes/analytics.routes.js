/**
 * Analytics Routes
 * Behavioral analytics dashboard APIs.
 */

const express = require("express");
const router = express.Router();

const { protect } = require("../middleware/auth");
const {
  getProductivity,
  getHoursDistribution,
  getDaysDistribution,
  getCompletionTrend,
} = require("../controllers/analytics.controller");

router.get("/productivity", protect, getProductivity);
router.get("/hours", protect, getHoursDistribution);
router.get("/days", protect, getDaysDistribution);
router.get("/completion-trend", protect, getCompletionTrend);

module.exports = router;

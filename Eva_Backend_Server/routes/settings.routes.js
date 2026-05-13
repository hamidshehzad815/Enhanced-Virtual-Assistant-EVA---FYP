/**
 * Settings Routes
 */

const express = require("express");
const router = express.Router();

const { protect } = require("../middleware/auth");
const {
  getSettings,
  updateSettings,
  patchLearningSchedule,
} = require("../controllers/settings.controller");

router.get("/", protect, getSettings);
router.patch("/learning-schedule", protect, patchLearningSchedule);
router.patch("/", protect, updateSettings);

module.exports = router;

/**
 * Settings Routes
 */

const express = require("express");
const router = express.Router();

const { protect } = require("../middleware/auth");
const {
  getSettings,
  updateSettings,
  listLearningSchedules,
  createLearningSchedule,
  updateLearningSchedule,
  deleteLearningSchedule,
} = require("../controllers/settings.controller");

router.get("/", protect, getSettings);
router.get("/learning-schedules", protect, listLearningSchedules);
router.post("/learning-schedules", protect, createLearningSchedule);
router.patch("/learning-schedules/:scheduleId", protect, updateLearningSchedule);
router.delete("/learning-schedules/:scheduleId", protect, deleteLearningSchedule);
router.patch("/", protect, updateSettings);

module.exports = router;

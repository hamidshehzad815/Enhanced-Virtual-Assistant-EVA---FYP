/**
 * Settings Routes
 */

const express = require("express");
const router = express.Router();

const { protect } = require("../middleware/auth");
const {
  getSettings,
  updateSettings,
} = require("../controllers/settings.controller");

router.get("/", protect, getSettings);
router.patch("/", protect, updateSettings);

module.exports = router;

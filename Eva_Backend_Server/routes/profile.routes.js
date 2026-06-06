/**
 * Profile Routes
 */

const express = require("express");
const router = express.Router();

const { protect } = require("../middleware/auth");
const {
  getProfile,
  updateProfile,
} = require("../controllers/profile.controller");

router.get("/", protect, getProfile);
router.patch("/", protect, updateProfile);

module.exports = router;

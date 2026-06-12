/**
 * User roadmap routes (learning goals owned by the authenticated user).
 */

const express = require("express");
const router = express.Router();

const { protect } = require("../middleware/auth");
const {
  getUserLanguages,
  getUserRoadmap,
} = require("../controllers/roadmaps.controller");

router.get("/languages", protect, getUserLanguages);
router.get("/", protect, getUserRoadmap);

module.exports = router;

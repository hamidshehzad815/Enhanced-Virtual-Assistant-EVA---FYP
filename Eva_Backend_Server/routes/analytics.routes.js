/**
 * Analytics Routes
 * Web analytics dashboard API.
 */

const express = require("express");
const router = express.Router();

const { protect } = require("../middleware/auth");
const { getDashboard } = require("../controllers/analytics.controller");

router.get("/dashboard", protect, getDashboard);

module.exports = router;

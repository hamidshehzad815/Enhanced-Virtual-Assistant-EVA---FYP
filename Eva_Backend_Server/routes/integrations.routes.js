/**
 * Integrations Routes
 * Phase 11 integration APIs.
 */

const express = require("express");
const router = express.Router();

const { protect } = require("../middleware/auth");
const {
  connectGoogleCalendar,
  getIntegrations,
} = require("../controllers/integrations.controller");

router.post("/google/connect", protect, connectGoogleCalendar);
router.get("/", protect, getIntegrations);

module.exports = router;

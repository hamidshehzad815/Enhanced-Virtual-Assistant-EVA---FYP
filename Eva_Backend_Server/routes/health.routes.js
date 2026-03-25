/**
 * Health Check Routes
 */

const express = require("express");
const router = express.Router();
const { getHealth, getRoot } = require("../controllers/health.controller");

// GET / - Root endpoint
router.get("/", getRoot);

// GET /health - Health check
router.get("/health", getHealth);

module.exports = router;

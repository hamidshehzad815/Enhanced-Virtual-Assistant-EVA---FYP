/**
 * Health Check Controller
 */

const { healthCheck: dbHealthCheck } = require("../config/db");
const axios = require("axios");
const logger = require("../config/logger");

/**
 * Check AI Server health
 * @returns {Promise<boolean>}
 */
const checkAIServer = async () => {
  try {
    const response = await axios.get(`${process.env.AI_SERVER_URL}/health`, {
      timeout: 5000,
    });
    return response.status === 200;
  } catch (error) {
    logger.warn("AI Server health check failed", { error: error.message });
    return false;
  }
};

/**
 * GET /health
 * Health check endpoint
 */
const getHealth = async (req, res) => {
  const mongodbHealthy = dbHealthCheck();
  const aiServerHealthy = await checkAIServer();

  const allHealthy = mongodbHealthy && aiServerHealthy;

  res.status(allHealthy ? 200 : 503).json({
    status: allHealthy ? "ok" : "degraded",
    service: "eva-backend",
    timestamp: new Date().toISOString(),
    connections: {
      mongodb: mongodbHealthy ? "connected" : "disconnected",
      ai_server: aiServerHealthy ? "connected" : "disconnected",
    },
  });
};

/**
 * GET /
 * Root endpoint
 */
const getRoot = (req, res) => {
  res.json({
    service: "EVA Backend Server",
    version: "1.0.0",
    status: "running",
  });
};

module.exports = {
  getHealth,
  getRoot,
};

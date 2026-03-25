/**
 * AI Service
 * Handles HTTP communication with EVA AI Server.
 */

const axios = require("axios");
const logger = require("../config/logger");

const AI_SERVER_URL = process.env.AI_SERVER_URL || "http://localhost:8080";
const AI_SERVER_TIMEOUT_MS = Number(process.env.AI_SERVER_TIMEOUT_MS || 15000);

const callAIServer = async (payload) => {
  try {
    const response = await axios.post(`${AI_SERVER_URL}/process`, payload, {
      timeout: AI_SERVER_TIMEOUT_MS,
    });

    return response.data;
  } catch (error) {
    if (error.response) {
      logger.error("AI server request failed", {
        status: error.response.status,
        data: error.response.data,
      });
      const message =
        error.response.data?.message ||
        `AI server error with status ${error.response.status}`;
      throw new Error(message);
    }

    if (error.request) {
      logger.error("AI server did not respond", {
        base_url: AI_SERVER_URL,
        timeout_ms: AI_SERVER_TIMEOUT_MS,
      });
      throw new Error("AI server unavailable");
    }

    logger.error("AI service unexpected error", { error: error.message });
    throw new Error(error.message || "Unexpected AI service error");
  }
};

module.exports = {
  callAIServer,
};

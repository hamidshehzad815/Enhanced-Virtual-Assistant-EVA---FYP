/**
 * Analytics Controller
 * Web analytics dashboard API.
 */

const { BadRequestError } = require("../middleware/errorHandler");
const { callAIAnalytics } = require("../services/ai.service");
const { parseRangeDays, buildDashboard } = require("../services/analyticsDashboard.service");

const resolveTimezone = (req) => req.user?.timezone || "UTC";

const fetchBehavioralPayload = async (userId) => {
  try {
    return await callAIAnalytics({
      userId,
      type: "full",
    });
  } catch (error) {
    return {
      status: "error",
      message: error.message,
      data: { has_enough_data: false },
    };
  }
};

/**
 * GET /api/analytics/dashboard
 * Unified analytics payload for the web dashboard.
 */
const getDashboard = async (req, res, next) => {
  try {
    const rangeDays = parseRangeDays(req.query.days);
    const behavioralPayload = await fetchBehavioralPayload(req.userId);

    const dashboard = await buildDashboard({
      userId: req.userId,
      timezone: resolveTimezone(req),
      rangeDays,
      behavioralPayload,
    });

    res.json({
      status: "success",
      data: dashboard,
    });
  } catch (error) {
    if (error.statusCode === 400) {
      return next(new BadRequestError(error.message));
    }
    next(error);
  }
};

module.exports = {
  getDashboard,
};

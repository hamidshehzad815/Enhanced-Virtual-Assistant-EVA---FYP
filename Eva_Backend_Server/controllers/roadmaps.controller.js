/**
 * User roadmap APIs — learning goals the user created (filter by language, status, track).
 */

const { BadRequestError } = require("../middleware/errorHandler");
const {
  listUserLanguages,
  listUserRoadmaps,
  GOAL_STATUSES,
} = require("../services/userRoadmaps.service");

const pickLanguageQuery = (req) =>
  req.query.language || req.query.lang || req.query.subject || "";

/**
 * GET /api/roadmaps/languages
 * Languages the user has at least one roadmap for (filter dropdown).
 */
const getUserLanguages = async (req, res, next) => {
  try {
    const languages = await listUserLanguages(req.userId);
    res.json({
      status: "success",
      data: { languages },
    });
  } catch (error) {
    next(error);
  }
};

/**
 * GET /api/roadmaps
 * Query: language, status (comma-separated), roadmap_key
 */
const getUserRoadmaps = async (req, res, next) => {
  try {
    const statusInput = req.query.status || req.query.statuses || "";
    if (statusInput) {
      const parts = String(statusInput)
        .split(",")
        .map((s) => s.trim().toLowerCase())
        .filter(Boolean);
      const invalid = parts.filter((s) => !GOAL_STATUSES.has(s));
      if (invalid.length) {
        throw new BadRequestError(
          `Invalid status value(s): ${invalid.join(", ")}. Use: ${[...GOAL_STATUSES].join(", ")}`,
        );
      }
    }

    const includeSessions =
      req.query.include_sessions !== "false" && req.query.include_sessions !== "0";

    const result = await listUserRoadmaps(req.userId, {
      languageInput: pickLanguageQuery(req),
      statusInput,
      roadmapKeyInput: req.query.roadmap_key || req.query.track || req.query.level || "",
      includeSessions,
    }, req.user?.timezone || "UTC");

    res.json({
      status: "success",
      data: result,
    });
  } catch (error) {
    next(error);
  }
};

module.exports = {
  getUserLanguages,
  getUserRoadmaps,
};

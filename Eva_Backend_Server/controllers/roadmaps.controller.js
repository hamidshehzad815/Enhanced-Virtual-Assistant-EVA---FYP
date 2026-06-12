/**
 * User roadmap APIs — language dropdown + single roadmap per selected language.
 */

const { BadRequestError } = require("../middleware/errorHandler");
const {
  listUserLanguages,
  getUserRoadmapForLanguage,
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
 * GET /api/roadmaps?language=python
 * Returns one roadmap for the language (active/paused preferred over completed).
 * Approach B: language is required — show placeholder until user selects.
 */
const getUserRoadmap = async (req, res, next) => {
  try {
    const languageInput = pickLanguageQuery(req);
    if (!languageInput) {
      throw new BadRequestError(
        "language query parameter is required (e.g. ?language=python)",
      );
    }

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

    const data = await getUserRoadmapForLanguage(
      req.userId,
      languageInput,
      req.user?.timezone || "UTC",
      { statusInput },
    );

    res.json({
      status: "success",
      data,
    });
  } catch (error) {
    next(error);
  }
};

module.exports = {
  getUserLanguages,
  getUserRoadmap,
};

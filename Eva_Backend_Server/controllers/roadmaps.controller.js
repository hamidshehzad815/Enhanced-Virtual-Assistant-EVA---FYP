/**
 * User roadmap APIs — plans list + single roadmap by goal id.
 */

const { BadRequestError } = require("../middleware/errorHandler");
const {
  listUserRoadmapPlans,
  getUserRoadmapForGoalId,
  getPlanScheduleDatesForGoal,
  listOverdueSessionsForUser,
  GOAL_STATUSES,
} = require("../services/userRoadmaps.service");

/**
 * GET /api/roadmaps/plans
 * All learning plans for the user (roadmap metadata only — no sessions[]).
 */
const getUserRoadmapPlans = async (req, res, next) => {
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

    const data = await listUserRoadmapPlans(
      req.userId,
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

/**
 * GET /api/roadmaps/:goalId
 * Returns one roadmap with all sessions for the given learning goal id.
 */
const getUserRoadmapByGoalId = async (req, res, next) => {
  try {
    const data = await getUserRoadmapForGoalId(
      req.userId,
      req.params.goalId,
      req.user?.timezone || "UTC",
    );

    res.json({
      status: "success",
      data,
    });
  } catch (error) {
    next(error);
  }
};

/**
 * GET /api/roadmaps/:goalId/schedule-dates
 * Calendar dates (learning weekdays only) eligible for session reschedule.
 */
const getPlanScheduleDates = async (req, res, next) => {
  try {
    const horizonRaw = req.query.horizon_weeks;
    const horizonWeeks =
      horizonRaw === undefined || horizonRaw === null || horizonRaw === ""
        ? undefined
        : Number.parseInt(String(horizonRaw), 10);

    const data = await getPlanScheduleDatesForGoal(
      req.userId,
      req.params.goalId,
      req.user?.timezone || "UTC",
      { horizonWeeks },
    );

    res.json({
      status: "success",
      data,
    });
  } catch (error) {
    next(error);
  }
};

/**
 * GET /api/roadmaps/overdue-sessions
 * Current session for each active goal, only where it's overdue.
 */
const getOverdueSessions = async (req, res, next) => {
  try {
    const data = await listOverdueSessionsForUser(
      req.userId,
      req.user?.timezone || "UTC",
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
  getUserRoadmapPlans,
  getUserRoadmapByGoalId,
  getPlanScheduleDates,
  getOverdueSessions,
};

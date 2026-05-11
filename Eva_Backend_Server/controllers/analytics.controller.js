/**
 * Analytics Controller
 * Behavioral analytics dashboard endpoints (non-chat APIs).
 */

const { ActivityLog } = require("../models");
const { BadRequestError } = require("../middleware/errorHandler");
const { toLocalDayRangeUtc } = require("../utils/timezone");
const { callAIAnalytics } = require("../services/ai.service");

const DAY_LABELS = {
  0: "Monday",
  1: "Tuesday",
  2: "Wednesday",
  3: "Thursday",
  4: "Friday",
  5: "Saturday",
  6: "Sunday",
};

const DAY_NAME_TO_NUMBER = {
  monday: 0,
  mon: 0,
  tuesday: 1,
  tue: 1,
  wednesday: 2,
  wed: 2,
  thursday: 3,
  thu: 3,
  friday: 4,
  fri: 4,
  saturday: 5,
  sat: 5,
  sunday: 6,
  sun: 6,
};

const roundTo = (value, digits) => {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
};

const buildOwnerIdFilter = (userId) => {
  const ownerIds = [userId, String(userId)];
  return [...new Set(ownerIds)];
};

const buildCompletionMatch = (userId, rangeQuery = null) => {
  const match = {
    user_id: { $in: buildOwnerIdFilter(userId) },
    action_type: "task_completed",
  };

  if (rangeQuery) {
    match.action_timestamp = rangeQuery;
  }

  return match;
};

const parseDayQuery = (dayInput) => {
  if (dayInput === undefined || dayInput === null || dayInput === "") {
    return null;
  }

  const normalized = String(dayInput).trim().toLowerCase();
  if (!normalized) {
    return null;
  }

  if (/^\d+$/.test(normalized)) {
    const numeric = Number.parseInt(normalized, 10);
    if (numeric >= 0 && numeric <= 6) {
      return numeric;
    }
    throw new BadRequestError("day must be between 0 and 6 or a weekday name");
  }

  if (DAY_NAME_TO_NUMBER[normalized] === undefined) {
    throw new BadRequestError("Invalid day query value");
  }

  return DAY_NAME_TO_NUMBER[normalized];
};

const parseWeeksQuery = (weeksInput) => {
  if (weeksInput === undefined || weeksInput === null || weeksInput === "") {
    return 4;
  }

  const parsed = Number.parseInt(String(weeksInput), 10);
  if (Number.isNaN(parsed) || parsed < 1 || parsed > 52) {
    throw new BadRequestError("weeks must be an integer between 1 and 52");
  }

  return parsed;
};

const mapDayRowsToFullWeek = (dayRows) => {
  const dayMap = {};
  dayRows.forEach((row) => {
    const dayNum = Number(row._id);
    const count = Number(row.count || 0);
    const onTimeCount = Number(row.on_time_count || 0);
    const rate = count > 0 ? roundTo(onTimeCount / count, 2) : 0.0;
    dayMap[dayNum] = {
      day_name: DAY_LABELS[dayNum] || String(dayNum),
      day_num: dayNum,
      count,
      on_time_rate: rate,
    };
  });

  const days = [];
  for (let dayNum = 0; dayNum <= 6; dayNum += 1) {
    days.push(
      dayMap[dayNum] || {
        day_name: DAY_LABELS[dayNum],
        day_num: dayNum,
        count: 0,
        on_time_rate: 0.0,
      },
    );
  }
  days.sort((a, b) => b.count - a.count || a.day_num - b.day_num);
  return days;
};

/**
 * GET /api/analytics/productivity
 * Returns completion metrics + day distribution.
 */
const getProductivity = async (req, res, next) => {
  try {
    const aiResponse = await callAIAnalytics({
      userId: req.userId,
      type: "full",
    });

    res.json(aiResponse);
  } catch (error) {
    next(error);
  }
};

/**
 * GET /api/analytics/hours
 * Returns hourly completion distribution, optionally filtered by day.
 */
const getHoursDistribution = async (req, res, next) => {
  try {
    if (req.query.day !== undefined && req.query.day !== null && req.query.day !== "") {
      // Validate day shape here to preserve clean 400 behavior.
      parseDayQuery(req.query.day);
    }
    const aiResponse = await callAIAnalytics({
      userId: req.userId,
      type: "hours",
      day: req.query.day,
    });

    res.json(aiResponse);
  } catch (error) {
    next(error);
  }
};

/**
 * GET /api/analytics/days
 * Returns day-of-week completion distribution.
 */
const getDaysDistribution = async (req, res, next) => {
  try {
    const aiResponse = await callAIAnalytics({
      userId: req.userId,
      type: "days",
    });

    res.json(aiResponse);
  } catch (error) {
    next(error);
  }
};

/**
 * GET /api/analytics/completion-trend
 * Returns last N weeks completion and on-time counts.
 */
const getCompletionTrend = async (req, res, next) => {
  try {
    const weeks = parseWeeksQuery(req.query.weeks);
    const match = {
      ...buildCompletionMatch(req.userId),
      week_number: { $gte: 1, $lte: 53 },
    };

    const trendRows = await ActivityLog.aggregate([
      { $match: match },
      {
        $group: {
          _id: "$week_number",
          count: { $sum: 1 },
          on_time: {
            $sum: {
              $cond: [{ $eq: ["$was_on_time", true] }, 1, 0],
            },
          },
        },
      },
      { $sort: { _id: -1 } },
      { $limit: weeks },
      { $sort: { _id: 1 } },
      {
        $project: {
          _id: 0,
          week: "$_id",
          count: 1,
          on_time: 1,
        },
      },
    ]);

    res.json({
      status: "success",
      data: {
        weeks,
        trend: trendRows.map((row) => ({
          week: Number(row.week),
          count: Number(row.count || 0),
          on_time: Number(row.on_time || 0),
        })),
      },
    });
  } catch (error) {
    next(error);
  }
};

module.exports = {
  getProductivity,
  getHoursDistribution,
  getDaysDistribution,
  getCompletionTrend,
};

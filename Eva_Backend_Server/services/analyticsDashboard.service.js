/**
 * Analytics dashboard aggregations for the web UI.
 * Combines ActivityLog, Task, and AI behavioral scores.
 */

const {
  ActivityLog,
  Task,
} = require("../models");
const {
  ANALYTICS_MIN_TASKS_PER_DAY,
  ANALYTICS_MIN_TASKS_THRESHOLD,
} = require("../utils/analyticsConstants");
const { normalizeTimezone } = require("../utils/timezone");

const HEATMAP_HOUR_START = 6;
const HEATMAP_HOUR_END = 23;
const COMPLETION_TREND_WEEKS = 3;

const DAY_LABELS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

const HOUR_LABELS = (hour) => {
  const h = Number(hour);
  if (!Number.isFinite(h) || h < 0 || h > 23) return String(hour);
  const suffix = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}${suffix}`;
};

const roundTo = (value, digits = 1) => {
  const factor = 10 ** digits;
  return Math.round(Number(value) * factor) / factor;
};

const buildOwnerIdFilter = (userId) => {
  const ownerIds = [userId, String(userId)];
  return [...new Set(ownerIds)];
};

const parseRangeDays = (value) => {
  if (value === undefined || value === null || value === "") {
    return 30;
  }
  const parsed = Number.parseInt(String(value), 10);
  if (![7, 30, 90].includes(parsed)) {
    const error = new Error("days must be 7, 30, or 90");
    error.statusCode = 400;
    throw error;
  }
  return parsed;
};

const localDateKey = (date, timezone) =>
  new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);

const localWeekday = (date, timezone) => {
  const name = new Intl.DateTimeFormat("en-US", {
    timeZone: timezone,
    weekday: "short",
  }).format(date);
  const map = { Mon: 0, Tue: 1, Wed: 2, Thu: 3, Fri: 4, Sat: 5, Sun: 6 };
  return map[name] ?? 0;
};

const startOfLocalWeekUtc = (referenceDate, timezone, weeksAgo = 0) => {
  const tz = normalizeTimezone(timezone);
  const anchor = new Date(referenceDate.getTime());
  anchor.setUTCDate(anchor.getUTCDate() - weeksAgo * 7);

  const weekday = localWeekday(anchor, tz);
  const dateKey = localDateKey(anchor, tz);
  const [y, m, d] = dateKey.split("-").map((part) => Number.parseInt(part, 10));
  const mondayOffset = weekday;
  const mondayDate = new Date(Date.UTC(y, m - 1, d - mondayOffset, 12, 0, 0));
  const mondayKey = localDateKey(mondayDate, tz);

  const start = localDayStartUtc(mondayKey, tz);
  const end = new Date(start.getTime() + 7 * 24 * 60 * 60 * 1000 - 1);
  return { start, end };
};

const localDayStartUtc = (dateKey, timezone) => {
  const [y, m, d] = dateKey.split("-").map((part) => Number.parseInt(part, 10));
  const guess = new Date(Date.UTC(y, m - 1, d, 0, 0, 0));
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  });
  const parts = formatter.formatToParts(guess);
  const map = {};
  parts.forEach((part) => {
    if (part.type !== "literal") map[part.type] = part.value;
  });
  const asUtc = Date.UTC(
    Number.parseInt(map.year, 10),
    Number.parseInt(map.month, 10) - 1,
    Number.parseInt(map.day, 10),
    Number.parseInt(map.hour, 10),
    Number.parseInt(map.minute, 10),
    Number.parseInt(map.second, 10),
  );
  const offset = asUtc - guess.getTime();
  return new Date(guess.getTime() - offset);
};

const countCompletionsInRange = async (userId, start, end) =>
  ActivityLog.countDocuments({
    user_id: { $in: buildOwnerIdFilter(userId) },
    action_type: "task_completed",
    action_timestamp: { $gte: start, $lte: end },
  });

const computeStreakDays = async (userId, timezone) => {
  const tz = normalizeTimezone(timezone);
  const rows = await ActivityLog.find({
    user_id: { $in: buildOwnerIdFilter(userId) },
    action_type: "task_completed",
  })
    .select("action_timestamp")
    .sort({ action_timestamp: -1 })
    .limit(500)
    .lean();

  if (!rows.length) return 0;

  const daySet = new Set(
    rows
      .map((row) => row.action_timestamp)
      .filter(Boolean)
      .map((ts) => localDateKey(new Date(ts), tz)),
  );

  let streak = 0;
  const cursor = new Date();
  for (let i = 0; i < 365; i += 1) {
    const key = localDateKey(cursor, tz);
    if (daySet.has(key)) {
      streak += 1;
      cursor.setUTCDate(cursor.getUTCDate() - 1);
    } else if (i === 0) {
      cursor.setUTCDate(cursor.getUTCDate() - 1);
    } else {
      break;
    }
  }
  return streak;
};

const getHeroSummary = async (userId, timezone) => {
  const now = new Date();
  const thisWeek = startOfLocalWeekUtc(now, timezone, 0);
  const lastWeek = startOfLocalWeekUtc(now, timezone, 1);

  const [completedThisWeek, completedLastWeek, streakDays, onTimeAgg] =
    await Promise.all([
      countCompletionsInRange(userId, thisWeek.start, thisWeek.end),
      countCompletionsInRange(userId, lastWeek.start, lastWeek.end),
      computeStreakDays(userId, timezone),
      ActivityLog.aggregate([
        {
          $match: {
            user_id: { $in: buildOwnerIdFilter(userId) },
            action_type: "task_completed",
          },
        },
        {
          $group: {
            _id: null,
            total: { $sum: 1 },
            on_time: {
              $sum: { $cond: [{ $eq: ["$was_on_time", true] }, 1, 0] },
            },
          },
        },
      ]),
    ]);

  const summary = onTimeAgg[0] || { total: 0, on_time: 0 };
  const total = Number(summary.total || 0);
  const onTime = Number(summary.on_time || 0);
  const onTimeRate = total > 0 ? roundTo((onTime / total) * 100, 1) : 0;

  const weekChangePct =
    completedLastWeek > 0
      ? roundTo(
          ((completedThisWeek - completedLastWeek) / completedLastWeek) * 100,
          1,
        )
      : completedThisWeek > 0
        ? 100
        : 0;

  const upcomingEnd = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
  const upcoming7d = await Task.countDocuments({
    owner_id: userId,
    is_deleted: false,
    status: { $in: ["pending", "ongoing"] },
    due_datetime: { $gte: now, $lte: upcomingEnd },
  });

  return {
    completed_this_week: completedThisWeek,
    completed_last_week: completedLastWeek,
    week_change_percent: weekChangePct,
    on_time_rate: onTimeRate,
    total_completed: total,
    streak_days: streakDays,
    upcoming_7d: upcoming7d,
  };
};

const getHeatmap = async (userId, rangeDays, timezone) => {
  const since = new Date(Date.now() - rangeDays * 24 * 60 * 60 * 1000);
  const rows = await ActivityLog.aggregate([
    {
      $match: {
        user_id: { $in: buildOwnerIdFilter(userId) },
        action_type: "task_completed",
        action_timestamp: { $gte: since },
      },
    },
    {
      $project: {
        day: {
          $ifNull: ["$scheduled_day", "$day_of_week"],
        },
        hour: {
          $ifNull: ["$scheduled_hour", "$hour_of_day"],
        },
        was_on_time: 1,
      },
    },
    {
      $match: {
        day: { $gte: 0, $lte: 6 },
        hour: { $gte: 0, $lte: 23 },
      },
    },
    {
      $group: {
        _id: { day: "$day", hour: "$hour" },
        count: { $sum: 1 },
        on_time: {
          $sum: { $cond: [{ $eq: ["$was_on_time", true] }, 1, 0] },
        },
      },
    },
    { $sort: { "_id.day": 1, "_id.hour": 1 } },
  ]);

  const cells = rows
    .map((row) => {
      const day = Number(row._id.day);
      const hour = Number(row._id.hour);
      const count = Number(row.count || 0);
      const onTime = Number(row.on_time || 0);
      return {
        day,
        day_name: DAY_LABELS[day] || String(day),
        hour,
        hour_display: HOUR_LABELS(hour),
        count,
        on_time_rate: count > 0 ? roundTo((onTime / count) * 100, 1) : 0,
        intensity: count,
      };
    })
    .filter(
      (cell) =>
        cell.hour >= HEATMAP_HOUR_START && cell.hour <= HEATMAP_HOUR_END,
    );

  return {
    range_days: rangeDays,
    timezone: normalizeTimezone(timezone),
    hour_range: {
      start: HEATMAP_HOUR_START,
      end: HEATMAP_HOUR_END,
      start_display: HOUR_LABELS(HEATMAP_HOUR_START),
      end_display: HOUR_LABELS(HEATMAP_HOUR_END),
    },
    cells,
    peak: cells.length
      ? [...cells].sort((a, b) => b.count - a.count || b.on_time_rate - a.on_time_rate)[0]
      : null,
    weakest: findWeakestHeatmapCell(cells),
  };
};

const getTasksOverview = async (userId, timezone) => {
  const now = new Date();
  const in48h = new Date(now.getTime() + 48 * 60 * 60 * 1000);
  const week = startOfLocalWeekUtc(now, timezone, 0);

  const baseMatch = {
    owner_id: userId,
    is_deleted: false,
  };

  const [pending, complete, overdue, byPriorityRows, due48h, weekTasks] =
    await Promise.all([
      Task.countDocuments({ ...baseMatch, status: { $in: ["pending", "ongoing"] } }),
      Task.countDocuments({ ...baseMatch, status: "complete" }),
      Task.countDocuments({
        ...baseMatch,
        status: { $in: ["pending", "ongoing"] },
        due_datetime: { $lt: now },
      }),
      Task.aggregate([
        {
          $match: {
            ...baseMatch,
            status: { $in: ["pending", "ongoing"] },
          },
        },
        {
          $group: {
            _id: "$priority",
            count: { $sum: 1 },
          },
        },
      ]),
      Task.find({
        ...baseMatch,
        status: { $in: ["pending", "ongoing"] },
        due_datetime: { $gte: now, $lte: in48h },
      })
        .select("title due_datetime priority status")
        .sort({ due_datetime: 1 })
        .limit(10)
        .lean(),
      Task.find({
        ...baseMatch,
        status: { $in: ["pending", "ongoing"] },
        due_datetime: { $gte: week.start, $lte: week.end },
      })
        .select("due_datetime")
        .lean(),
    ]);

  const byPriority = { high: 0, medium: 0, low: 0 };
  byPriorityRows.forEach((row) => {
    const key = String(row._id || "medium").toLowerCase();
    if (Object.prototype.hasOwnProperty.call(byPriority, key)) {
      byPriority[key] = Number(row.count || 0);
    }
  });

  const dayCounts = Array(7).fill(0);
  weekTasks.forEach((task) => {
    if (!task.due_datetime) return;
    const day = localWeekday(new Date(task.due_datetime), timezone);
    dayCounts[day] += 1;
  });
  let busiestDayNum = 0;
  let busiestCount = 0;
  dayCounts.forEach((count, dayNum) => {
    if (count > busiestCount) {
      busiestCount = count;
      busiestDayNum = dayNum;
    }
  });

  return {
    pending,
    complete,
    overdue,
    by_priority: byPriority,
    due_within_48h: due48h.map((task) => ({
      id: String(task._id),
      title: task.title,
      due_datetime: task.due_datetime,
      priority: task.priority,
      status: task.status,
    })),
    busiest_day_this_week: {
      day_num: busiestDayNum,
      day_name: DAY_LABELS[busiestDayNum],
      task_count: busiestCount,
    },
  };
};

const findWeakestHeatmapCell = (cells = []) => {
  const withData = cells.filter((cell) => cell.count > 0);
  if (!withData.length) return null;
  return [...withData].sort(
    (a, b) =>
      a.count - b.count ||
      a.on_time_rate - b.on_time_rate ||
      b.hour - a.hour,
  )[0];
};

const buildHourWindows = (hours = [], limit = 3) => {
  if (!Array.isArray(hours) || !hours.length) return [];

  const byDay = {};
  hours.forEach((row) => {
    const dayNum = Number(row.day_num ?? row.day);
    const hour = Number(row.hour);
    if (!Number.isFinite(dayNum) || !Number.isFinite(hour)) return;
    if (!byDay[dayNum]) byDay[dayNum] = [];
    byDay[dayNum].push({ hour, score: Number(row.score || 0), log_count: Number(row.log_count || 0) });
  });

  const windows = [];
  Object.entries(byDay).forEach(([dayNumRaw, slots]) => {
    const dayNum = Number(dayNumRaw);
    const sorted = [...slots].sort((a, b) => a.hour - b.hour);
    let runStart = sorted[0];
    let runEnd = sorted[0];
    let runScore = Number(sorted[0]?.score || 0);
    let runCount = Number(sorted[0]?.log_count || 0);

    const flushRun = () => {
      if (!runStart) return;
      windows.push({
        day_num: dayNum,
        day_name: DAY_LABELS[dayNum],
        start_hour: runStart.hour,
        end_hour: runEnd.hour,
        start_display: HOUR_LABELS(runStart.hour),
        end_display: HOUR_LABELS(runEnd.hour),
        label:
          runStart.hour === runEnd.hour
            ? `${DAY_LABELS[dayNum]} ${HOUR_LABELS(runStart.hour)}`
            : `${DAY_LABELS[dayNum]} ${HOUR_LABELS(runStart.hour)}–${HOUR_LABELS(runEnd.hour)}`,
        score: roundTo(runScore, 2),
        log_count: runCount,
      });
    };

    for (let i = 1; i < sorted.length; i += 1) {
      const slot = sorted[i];
      if (slot.hour === runEnd.hour + 1) {
        runEnd = slot;
        runScore += Number(slot.score || 0);
        runCount += Number(slot.log_count || 0);
      } else {
        flushRun();
        runStart = slot;
        runEnd = slot;
        runScore = Number(slot.score || 0);
        runCount = Number(slot.log_count || 0);
      }
    }
    flushRun();
  });

  return windows
    .sort((a, b) => b.score - a.score || b.log_count - a.log_count)
    .slice(0, limit);
};

const buildStrengthSummary = (topDays = [], hourWindows = []) => {
  const dayNames = topDays
    .slice(0, 2)
    .map((row) => row.day)
    .filter(Boolean);
  if (!dayNames.length) return null;

  const topWindow = hourWindows[0];
  const hours = topWindow
    ? [topWindow.start_hour, topWindow.end_hour].filter((hour) =>
        Number.isFinite(hour),
      )
    : [];
  const afternoon =
    hours.length > 0 && hours.every((hour) => hour >= 12 && hour <= 17);
  const evening =
    hours.length > 0 && hours.every((hour) => hour >= 18 && hour <= 23);

  let timePhrase = "";
  if (afternoon) timePhrase = " afternoons";
  else if (evening) timePhrase = " evenings";

  return `You're strongest ${dayNames.join(" & ")}${timePhrase}.`;
};

const getCompletionTrendWeeks = async (userId, weeks = COMPLETION_TREND_WEEKS) => {
  const trendRows = await ActivityLog.aggregate([
    {
      $match: {
        user_id: { $in: buildOwnerIdFilter(userId) },
        action_type: "task_completed",
        week_number: { $gte: 1, $lte: 53 },
      },
    },
    {
      $group: {
        _id: "$week_number",
        count: { $sum: 1 },
        on_time: {
          $sum: { $cond: [{ $eq: ["$was_on_time", true] }, 1, 0] },
        },
      },
    },
    { $sort: { _id: -1 } },
    { $limit: weeks },
    { $sort: { _id: 1 } },
  ]);

  return trendRows.map((row) => {
    const count = Number(row.count || 0);
    const onTime = Number(row.on_time || 0);
    const late = Math.max(0, count - onTime);
    return {
      week: Number(row._id),
      count,
      on_time: onTime,
      late,
      on_time_rate: count > 0 ? roundTo((onTime / count) * 100, 1) : 0,
    };
  });
};

const buildBehavioralBlock = async ({
  userId,
  timezone,
  behavioralPayload,
  hero = null,
}) => {
  const behavioralData = behavioralPayload?.data || {};
  const behavioralEnabled =
    behavioralPayload?.status !== "analytics_disabled";

  const heroSummary = hero ?? (await getHeroSummary(userId, timezone));

  const allDays = behavioralData.days || [];
  const allHours = behavioralData.hours || [];
  const topDays = allDays.slice(0, 3);
  const hourWindows = buildHourWindows(allHours, 3);

  const aiCompletionRate = behavioralData.completion_rate || {};

  return {
    enabled: behavioralEnabled,
    has_enough_data: Boolean(behavioralData.has_enough_data),
    thresholds: behavioralData.thresholds || {
      global: ANALYTICS_MIN_TASKS_THRESHOLD,
      per_day: ANALYTICS_MIN_TASKS_PER_DAY,
    },
    total_completed:
      behavioralData.total_completed ?? heroSummary.total_completed,
    top_days: topDays,
    hour_windows: hourWindows,
    strength_summary: buildStrengthSummary(topDays, hourWindows),
    unreliable_days: behavioralData.unreliable_days || [],
    completion_rate: {
      total_completed:
        aiCompletionRate.total_completed ?? heroSummary.total_completed,
      on_time: aiCompletionRate.on_time ?? 0,
      late: aiCompletionRate.late ?? 0,
      on_time_rate:
        aiCompletionRate.on_time_rate ?? heroSummary.on_time_rate,
    },
    avg_time_taken: behavioralData.avg_time_taken ?? null,
  };
};

const pickTopSlots = (hours = [], limit = 3) => {
  if (!Array.isArray(hours) || !hours.length) return [];

  return [...hours]
    .sort(
      (a, b) =>
        Number(b.score || 0) - Number(a.score || 0) ||
        Number(b.log_count || 0) - Number(a.log_count || 0),
    )
    .slice(0, limit)
    .map((slot) => ({
      day_num: slot.day_num,
      day_name: slot.day,
      hour: slot.hour,
      hour_display: slot.hour_display || HOUR_LABELS(slot.hour),
      score: slot.score,
      on_time_rate: slot.on_time_rate,
      log_count: slot.log_count,
      suggestion: `Best time to plan deep work: ${slot.day} around ${slot.hour_display || HOUR_LABELS(slot.hour)}`,
    }));
};

const buildDashboard = async ({
  userId,
  timezone,
  rangeDays = 30,
  behavioralPayload,
}) => {
  const tz = normalizeTimezone(timezone);

  const [hero, heatmap, tasks, completionTrend] = await Promise.all([
    getHeroSummary(userId, tz),
    getHeatmap(userId, rangeDays, tz),
    getTasksOverview(userId, tz),
    getCompletionTrendWeeks(userId, COMPLETION_TREND_WEEKS),
  ]);

  const behavioral = await buildBehavioralBlock({
    userId,
    timezone: tz,
    behavioralPayload,
    hero,
  });

  const bestSlots = pickTopSlots(behavioralPayload?.data?.hours || [], 3);

  return {
    generated_at: new Date().toISOString(),
    timezone: tz,
    range_days: rangeDays,
    hero,
    behavioral,
    heatmap,
    tasks,
    completion_trend: {
      weeks: COMPLETION_TREND_WEEKS,
      trend: completionTrend,
    },
    best_slots: bestSlots,
  };
};

module.exports = {
  parseRangeDays,
  buildBehavioralBlock,
  buildDashboard,
  DAY_LABELS,
  HOUR_LABELS,
  HEATMAP_HOUR_START,
  HEATMAP_HOUR_END,
};

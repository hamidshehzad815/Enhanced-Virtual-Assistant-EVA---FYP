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

const clamp01 = (value) => Math.max(0, Math.min(1, Number(value) || 0));

/** Time-of-day buckets (local hours). "night" wraps past midnight. */
const TIME_BUCKETS = [
  { key: "morning", label: "Morning", start: 5, end: 11, range_display: "5AM–12PM" },
  { key: "afternoon", label: "Afternoon", start: 12, end: 16, range_display: "12PM–5PM" },
  { key: "evening", label: "Evening", start: 17, end: 20, range_display: "5PM–9PM" },
  { key: "night", label: "Night", start: 21, end: 4, range_display: "9PM–5AM" },
];

const bucketKeyForHour = (hour) => {
  const h = Number(hour);
  if (h >= 5 && h <= 11) return "morning";
  if (h >= 12 && h <= 16) return "afternoon";
  if (h >= 17 && h <= 20) return "evening";
  return "night";
};

const PRIORITY_ORDER = ["high", "medium", "low"];
const PRIORITY_LABELS = { high: "High", medium: "Medium", low: "Low" };

const localHour = (date, timezone) => {
  const value = new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    hourCycle: "h23",
    timeZone: timezone,
  }).format(date);
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed % 24 : 0;
};

const SCORE_RATINGS = [
  { min: 85, label: "Excellent", caption: "You're operating at your best — steady and on time." },
  { min: 70, label: "Great", caption: "Strong, consistent momentum. Keep it going." },
  { min: 55, label: "Good", caption: "Solid habits forming — a little more consistency lifts this." },
  { min: 40, label: "Fair", caption: "You're building rhythm. Small daily wins add up fast." },
  { min: 0, label: "Building", caption: "Every completed task moves this number up." },
];

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

/**
 * Fetch completion logs within the range once, so several blocks
 * (daily series, time-of-day, priority) can reuse the same rows.
 */
const fetchRangeCompletionLogs = async (userId, rangeDays) => {
  const since = new Date(Date.now() - (rangeDays + 1) * 24 * 60 * 60 * 1000);
  return ActivityLog.find({
    user_id: { $in: buildOwnerIdFilter(userId) },
    action_type: "task_completed",
    action_timestamp: { $gte: since },
  })
    .select("action_timestamp was_on_time hour_of_day task_priority time_taken_minutes")
    .sort({ action_timestamp: 1 })
    .limit(2000)
    .lean();
};

/** Dense per-day completion series over the selected range (for the trend line). */
const buildDailyCompletions = (rangeLogs, rangeDays, timezone) => {
  const now = new Date();
  const order = [];
  const map = {};
  for (let i = rangeDays - 1; i >= 0; i -= 1) {
    const day = new Date(now.getTime() - i * 24 * 60 * 60 * 1000);
    const key = localDateKey(day, timezone);
    order.push(key);
    map[key] = { date: key, count: 0, on_time: 0, late: 0 };
  }

  rangeLogs.forEach((log) => {
    if (!log.action_timestamp) return;
    const key = localDateKey(new Date(log.action_timestamp), timezone);
    const bucket = map[key];
    if (!bucket) return;
    bucket.count += 1;
    if (log.was_on_time === true) bucket.on_time += 1;
    else if (log.was_on_time === false) bucket.late += 1;
  });

  const series = order.map((key) => map[key]);
  const total = series.reduce((sum, row) => sum + row.count, 0);
  const activeDays = series.filter((row) => row.count > 0).length;
  const busiest = series.reduce(
    (best, row) => (row.count > (best?.count || 0) ? row : best),
    null,
  );

  return {
    range_days: rangeDays,
    total,
    active_days: activeDays,
    avg_per_active_day: activeDays ? roundTo(total / activeDays, 1) : 0,
    busiest_date: busiest && busiest.count > 0 ? busiest : null,
    series,
  };
};

/** Distribution of completions across morning / afternoon / evening / night. */
const buildTimeOfDay = (rangeLogs, timezone) => {
  const counters = {};
  TIME_BUCKETS.forEach((bucket) => {
    counters[bucket.key] = { count: 0, on_time: 0 };
  });

  rangeLogs.forEach((log) => {
    let hour = Number(log.hour_of_day);
    if (!Number.isFinite(hour) && log.action_timestamp) {
      hour = localHour(new Date(log.action_timestamp), timezone);
    }
    if (!Number.isFinite(hour)) return;
    const key = bucketKeyForHour(hour);
    counters[key].count += 1;
    if (log.was_on_time === true) counters[key].on_time += 1;
  });

  const total = TIME_BUCKETS.reduce((sum, b) => sum + counters[b.key].count, 0);

  const buckets = TIME_BUCKETS.map((bucket) => {
    const { count, on_time: onTime } = counters[bucket.key];
    return {
      key: bucket.key,
      label: bucket.label,
      range_display: bucket.range_display,
      count,
      on_time_rate: count > 0 ? roundTo((onTime / count) * 100, 1) : 0,
      percent: total > 0 ? roundTo((count / total) * 100, 1) : 0,
    };
  });

  const dominant = total
    ? [...buckets].sort((a, b) => b.count - a.count)[0]
    : null;

  return { total, buckets, dominant };
};

/** How reliably the user finishes tasks at each priority level. */
const buildPriorityPerformance = (rangeLogs) => {
  const counters = {};
  PRIORITY_ORDER.forEach((priority) => {
    counters[priority] = { completed: 0, on_time: 0 };
  });

  rangeLogs.forEach((log) => {
    const priority = String(log.task_priority || "").toLowerCase();
    if (!counters[priority]) return;
    counters[priority].completed += 1;
    if (log.was_on_time === true) counters[priority].on_time += 1;
  });

  const totalKnown = PRIORITY_ORDER.reduce(
    (sum, priority) => sum + counters[priority].completed,
    0,
  );

  return PRIORITY_ORDER.map((priority) => {
    const { completed, on_time: onTime } = counters[priority];
    return {
      priority,
      label: PRIORITY_LABELS[priority],
      completed,
      on_time: onTime,
      on_time_rate: completed > 0 ? roundTo((onTime / completed) * 100, 1) : 0,
      percent: totalKnown > 0 ? roundTo((completed / totalKnown) * 100, 1) : 0,
    };
  });
};

/**
 * Composite 0–100 productivity score with a transparent component breakdown.
 * Weighted: on-time 35, consistency 25, volume 25, streak 15.
 */
const buildProductivityScore = ({ hero, daily, rangeDays }) => {
  const onTime = clamp01((hero.on_time_rate || 0) / 100);
  // 60% of days active earns full consistency credit (range-agnostic target).
  const activeRatio = rangeDays > 0 ? daily.active_days / rangeDays : 0;
  const consistency = clamp01(activeRatio / 0.6);
  // ~0.8 completions/day averaged over the range earns full volume credit.
  const volume = clamp01(rangeDays > 0 ? daily.total / rangeDays / 0.8 : 0);
  const streak = clamp01((hero.streak_days || 0) / 7);

  const score = Math.round(
    100 * (0.35 * onTime + 0.25 * consistency + 0.25 * volume + 0.15 * streak),
  );
  const rating = SCORE_RATINGS.find((r) => score >= r.min) || SCORE_RATINGS[SCORE_RATINGS.length - 1];

  return {
    score,
    rating: rating.label,
    caption: rating.caption,
    components: {
      on_time: Math.round(onTime * 100),
      consistency: Math.round(consistency * 100),
      volume: Math.round(volume * 100),
      streak: Math.round(streak * 100),
    },
    weights: { on_time: 35, consistency: 25, volume: 25, streak: 15 },
  };
};

/**
 * Rule-based, human-readable insight cards. Built entirely from Mongo-derived
 * data so they work even when the AI server is unavailable.
 */
const buildInsights = ({
  hero,
  heatmap,
  tasks,
  behavioral,
  timeOfDay,
  priorityPerformance,
  daily,
}) => {
  const insights = [];
  const push = (type, icon, title, message) =>
    insights.push({ id: `${insights.length + 1}`, type, icon, title, message });

  if ((hero.total_completed || 0) === 0) {
    push(
      "tip",
      "rocket_launch",
      "Let's get started",
      "Complete your first task to unlock your productivity insights.",
    );
    return insights;
  }

  if ((hero.streak_days || 0) >= 3) {
    push(
      "positive",
      "local_fire_department",
      "On a roll",
      `${hero.streak_days}-day completion streak — keep the momentum going!`,
    );
  }

  const weekChange = hero.week_change_percent || 0;
  if (weekChange >= 10) {
    push(
      "positive",
      "trending_up",
      "Up from last week",
      `You've finished ${hero.completed_this_week} tasks this week — ${Math.round(Math.abs(weekChange))}% more than last week.`,
    );
  } else if (weekChange <= -20 && (hero.completed_last_week || 0) > 0) {
    push(
      "warning",
      "trending_down",
      "Slower week",
      `Completions are down ${Math.round(Math.abs(weekChange))}% versus last week — a small push gets you back on track.`,
    );
  }

  const onTimeRate = hero.on_time_rate || 0;
  if (onTimeRate >= 85) {
    push(
      "positive",
      "verified",
      "Reliably on time",
      `You finish ${onTimeRate}% of your tasks on schedule. Excellent discipline.`,
    );
  } else if (onTimeRate > 0 && onTimeRate < 60 && (hero.total_completed || 0) >= 10) {
    push(
      "tip",
      "schedule",
      "Beat the deadline",
      `Only ${onTimeRate}% of tasks finish on time. Try scheduling them inside your peak window.`,
    );
  }

  const strength = behavioral?.strength_summary;
  const peak = heatmap?.peak;
  if (strength) {
    push("info", "bolt", "Your power hours", strength);
  } else if (peak) {
    push(
      "info",
      "bolt",
      "Your power hours",
      `You're most productive on ${peak.day_name} around ${peak.hour_display}.`,
    );
  }

  const high = (priorityPerformance || []).find((p) => p.priority === "high");
  if (high && high.completed >= 3 && high.on_time_rate < onTimeRate - 15) {
    push(
      "tip",
      "priority_high",
      "High-priority tasks slip",
      `High-priority tasks are on time only ${high.on_time_rate}% of the time — plan them earlier in the day.`,
    );
  }

  if ((tasks?.overdue || 0) > 0) {
    push(
      "warning",
      "warning_amber",
      "Overdue tasks waiting",
      `You have ${tasks.overdue} overdue task${tasks.overdue > 1 ? "s" : ""}. Clearing them lifts your score.`,
    );
  }

  const dominant = timeOfDay?.dominant;
  if (dominant && dominant.percent >= 40) {
    push(
      "info",
      "wb_sunny",
      `${dominant.label} person`,
      `${dominant.percent}% of your work happens in the ${dominant.label.toLowerCase()} (${dominant.range_display}).`,
    );
  }

  if (daily && daily.range_days > 0) {
    const activeRatio = daily.active_days / daily.range_days;
    if (activeRatio >= 0.6) {
      push(
        "positive",
        "calendar_month",
        "Consistent presence",
        `Active on ${daily.active_days} of the last ${daily.range_days} days — consistency is your superpower.`,
      );
    }
  }

  return insights.slice(0, 5);
};

const buildDashboard = async ({
  userId,
  timezone,
  rangeDays = 30,
  behavioralPayload,
}) => {
  const tz = normalizeTimezone(timezone);

  const [hero, heatmap, tasks, completionTrend, rangeLogs] = await Promise.all([
    getHeroSummary(userId, tz),
    getHeatmap(userId, rangeDays, tz),
    getTasksOverview(userId, tz),
    getCompletionTrendWeeks(userId, COMPLETION_TREND_WEEKS),
    fetchRangeCompletionLogs(userId, rangeDays),
  ]);

  const behavioral = await buildBehavioralBlock({
    userId,
    timezone: tz,
    behavioralPayload,
    hero,
  });

  const bestSlots = pickTopSlots(behavioralPayload?.data?.hours || [], 3);

  const daily = buildDailyCompletions(rangeLogs, rangeDays, tz);
  const timeOfDay = buildTimeOfDay(rangeLogs, tz);
  const priorityPerformance = buildPriorityPerformance(rangeLogs);
  const productivityScore = buildProductivityScore({ hero, daily, rangeDays });
  const insights = buildInsights({
    hero,
    heatmap,
    tasks,
    behavioral,
    timeOfDay,
    priorityPerformance,
    daily,
  });

  return {
    generated_at: new Date().toISOString(),
    timezone: tz,
    range_days: rangeDays,
    productivity_score: productivityScore,
    hero,
    insights,
    behavioral,
    daily_completions: daily,
    time_of_day: timeOfDay,
    priority_performance: priorityPerformance,
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
  buildDailyCompletions,
  buildTimeOfDay,
  buildPriorityPerformance,
  buildProductivityScore,
  buildInsights,
  buildDashboard,
  DAY_LABELS,
  HOUR_LABELS,
  HEATMAP_HOUR_START,
  HEATMAP_HOUR_END,
};

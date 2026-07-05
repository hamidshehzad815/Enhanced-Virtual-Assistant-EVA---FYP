/**
 * Analytics dashboard aggregations for the web UI.
 *
 * Produces a de-duplicated, six-section payload where every headline metric has
 * exactly ONE home:
 *   1. snapshot         — score, on-time rate, streak, completed (+Δ)
 *   2. insights         — narrative cards derived from the sections below
 *   3. activity         — daily completion series (a breakdown of the total)
 *   4. productivity_map — heatmap + AI best slots + unreliable days
 *   5. work_patterns    — time-of-day + priority breakdowns
 *   6. needs_attention  — overdue / due-soon / pending
 *
 * Everything is computed from MongoDB except `productivity_map.best_slots`,
 * which comes from the AI server's scored hours (empty when AI is unavailable).
 *
 * De-duplication rules:
 *   - The aggregate on-time rate and the canonical completed total live only in
 *     `snapshot`. Per-slice `on_time_rate` (cells/buckets/priority) is a
 *     breakdown, not a duplicate.
 *   - `activity`, `work_patterns.time_of_day`, and `work_patterns.by_priority`
 *     are breakdowns of that single total by a dimension — no `total` field.
 */

const { ActivityLog, Task } = require("../models");
const {
  ANALYTICS_MIN_TASKS_PER_DAY,
  ANALYTICS_MIN_TASKS_THRESHOLD,
} = require("../utils/analyticsConstants");
const { normalizeTimezone } = require("../utils/timezone");

const DAY_MS = 24 * 60 * 60 * 1000;
const HEATMAP_HOUR_START = 6;
const HEATMAP_HOUR_END = 23;

const DAY_LABELS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

const PRIORITY_ORDER = ["high", "medium", "low"];
const PRIORITY_LABELS = { high: "High", medium: "Medium", low: "Low" };

/** Time-of-day buckets (local hours). "night" wraps past midnight. */
const TIME_BUCKETS = [
  { key: "morning", label: "Morning", range_display: "5AM–12PM" },
  { key: "afternoon", label: "Afternoon", range_display: "12PM–5PM" },
  { key: "evening", label: "Evening", range_display: "5PM–9PM" },
  { key: "night", label: "Night", range_display: "9PM–5AM" },
];

const SCORE_RATINGS = [
  { min: 85, label: "Excellent", caption: "You're operating at your best — steady and on time." },
  { min: 70, label: "Great", caption: "Strong, consistent momentum. Keep it going." },
  { min: 55, label: "Good", caption: "Solid habits forming — a little more consistency lifts this." },
  { min: 40, label: "Fair", caption: "You're building rhythm. Small daily wins add up fast." },
  { min: 0, label: "Building", caption: "Every completed task moves this number up." },
];

// ─── small helpers ────────────────────────────────────────────────────────

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

const pct = (part, whole) => (whole > 0 ? roundTo((part / whole) * 100, 1) : 0);

const bucketKeyForHour = (hour) => {
  const h = Number(hour);
  if (h >= 5 && h <= 11) return "morning";
  if (h >= 12 && h <= 16) return "afternoon";
  if (h >= 17 && h <= 20) return "evening";
  return "night";
};

const buildOwnerIdFilter = (userId) => [...new Set([userId, String(userId)])];

const parseRangeDays = (value) => {
  if (value === undefined || value === null || value === "") return 30;
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

const localHour = (date, timezone) => {
  const value = new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    hourCycle: "h23",
    timeZone: timezone,
  }).format(date);
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed % 24 : NaN;
};

// ─── data access ──────────────────────────────────────────────────────────

/** One fetch of completion logs in the range; reused by several sections. */
const fetchRangeCompletionLogs = (userId, rangeDays) => {
  const since = new Date(Date.now() - (rangeDays + 1) * DAY_MS);
  return ActivityLog.find({
    user_id: { $in: buildOwnerIdFilter(userId) },
    action_type: "task_completed",
    action_timestamp: { $gte: since },
  })
    .select(
      "action_timestamp was_on_time hour_of_day day_of_week scheduled_hour scheduled_day task_priority",
    )
    .sort({ action_timestamp: 1 })
    .limit(3000)
    .lean();
};

const countCompletionsInRange = (userId, start, end) =>
  ActivityLog.countDocuments({
    user_id: { $in: buildOwnerIdFilter(userId) },
    action_type: "task_completed",
    action_timestamp: { $gte: start, $lte: end },
  });

const countAllTimeCompleted = (userId) =>
  ActivityLog.countDocuments({
    user_id: { $in: buildOwnerIdFilter(userId) },
    action_type: "task_completed",
  });

const computeStreakDays = async (userId, timezone) => {
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
      .map((ts) => localDateKey(new Date(ts), timezone)),
  );

  let streak = 0;
  const cursor = new Date();
  for (let i = 0; i < 366; i += 1) {
    const key = localDateKey(cursor, timezone);
    if (daySet.has(key)) {
      streak += 1;
      cursor.setUTCDate(cursor.getUTCDate() - 1);
    } else if (i === 0) {
      // Today with no completion yet doesn't break the streak.
      cursor.setUTCDate(cursor.getUTCDate() - 1);
    } else {
      break;
    }
  }
  return streak;
};

// ─── section builders ─────────────────────────────────────────────────────

/**
 * Dense per-day completion series (zero-filled) over the range. Returns the
 * public fields plus internal `_total` / `_onTime` used by snapshot + score.
 */
const buildActivity = (rangeLogs, rangeDays, timezone) => {
  const now = Date.now();
  const order = [];
  const map = {};
  for (let i = rangeDays - 1; i >= 0; i -= 1) {
    const key = localDateKey(new Date(now - i * DAY_MS), timezone);
    order.push(key);
    map[key] = { date: key, count: 0, on_time: 0, late: 0 };
  }

  rangeLogs.forEach((log) => {
    if (!log.action_timestamp) return;
    const bucket = map[localDateKey(new Date(log.action_timestamp), timezone)];
    if (!bucket) return;
    bucket.count += 1;
    if (log.was_on_time === true) bucket.on_time += 1;
    else if (log.was_on_time === false) bucket.late += 1;
  });

  const series = order.map((key) => map[key]);
  const total = series.reduce((sum, row) => sum + row.count, 0);
  const onTime = series.reduce((sum, row) => sum + row.on_time, 0);
  const activeDays = series.filter((row) => row.count > 0).length;

  return {
    series,
    active_days: activeDays,
    avg_per_active_day: activeDays ? roundTo(total / activeDays, 1) : 0,
    _total: total,
    _onTime: onTime,
  };
};

/** Day × hour completion grid (6AM–11PM) keyed on the scheduled slot. */
const buildHeatmapCells = (rangeLogs) => {
  const grid = {};
  rangeLogs.forEach((log) => {
    const day = log.scheduled_day ?? log.day_of_week;
    const hour = log.scheduled_hour ?? log.hour_of_day;
    const d = Number(day);
    const h = Number(hour);
    if (!Number.isFinite(d) || d < 0 || d > 6) return;
    if (!Number.isFinite(h) || h < HEATMAP_HOUR_START || h > HEATMAP_HOUR_END) return;
    const key = `${d}-${h}`;
    if (!grid[key]) grid[key] = { day: d, hour: h, count: 0, on_time: 0 };
    grid[key].count += 1;
    if (log.was_on_time === true) grid[key].on_time += 1;
  });

  return Object.values(grid)
    .sort((a, b) => a.day - b.day || a.hour - b.hour)
    .map((cell) => ({
      day: cell.day,
      day_name: DAY_LABELS[cell.day],
      hour: cell.hour,
      hour_display: HOUR_LABELS(cell.hour),
      count: cell.count,
      on_time_rate: pct(cell.on_time, cell.count),
    }));
};

/** Top scored hour slots from the AI server (forward-looking scheduling). */
const buildBestSlots = (behavioralPayload, limit = 3) => {
  const hours = behavioralPayload?.data?.hours || [];
  if (!Array.isArray(hours) || !hours.length) return [];
  return [...hours]
    .sort(
      (a, b) =>
        Number(b.score || 0) - Number(a.score || 0) ||
        Number(b.log_count || 0) - Number(a.log_count || 0),
    )
    .slice(0, limit)
    .map((slot) => {
      const display = slot.hour_display || HOUR_LABELS(slot.hour);
      return {
        day_name: slot.day,
        hour_display: display,
        on_time_rate: roundTo(Number(slot.on_time_rate || 0) * 100, 1),
        suggestion: `Plan deep work on ${slot.day} around ${display}`,
      };
    });
};

/** Weekdays with fewer than the per-day threshold of completions in range. */
const buildUnreliableDays = (rangeLogs) => {
  const counts = Array(7).fill(0);
  rangeLogs.forEach((log) => {
    const d = Number(log.day_of_week);
    if (Number.isFinite(d) && d >= 0 && d <= 6) counts[d] += 1;
  });
  const result = [];
  for (let d = 0; d < 7; d += 1) {
    if (counts[d] < ANALYTICS_MIN_TASKS_PER_DAY) {
      result.push({
        day: DAY_LABELS[d],
        log_count: counts[d],
        needed: ANALYTICS_MIN_TASKS_PER_DAY,
      });
    }
  }
  return result;
};

const buildProductivityMap = (rangeLogs, behavioralPayload) => ({
  hour_range: {
    start: HEATMAP_HOUR_START,
    end: HEATMAP_HOUR_END,
    start_display: HOUR_LABELS(HEATMAP_HOUR_START),
    end_display: HOUR_LABELS(HEATMAP_HOUR_END),
  },
  cells: buildHeatmapCells(rangeLogs),
  best_slots: buildBestSlots(behavioralPayload, 3),
  unreliable_days: buildUnreliableDays(rangeLogs),
});

/** Completion distribution across day-parts (breakdown of the total). */
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

  return TIME_BUCKETS.map((bucket) => {
    const { count, on_time: onTime } = counters[bucket.key];
    return {
      key: bucket.key,
      label: bucket.label,
      range_display: bucket.range_display,
      count,
      percent: pct(count, total),
      on_time_rate: pct(onTime, count),
    };
  });
};

/** On-time reliability per priority (breakdown of the total). */
const buildByPriority = (rangeLogs) => {
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
      on_time_rate: pct(onTime, completed),
      percent: pct(completed, totalKnown),
    };
  });
};

const getNeedsAttention = async (userId) => {
  const now = new Date();
  const in48h = new Date(now.getTime() + 48 * 60 * 60 * 1000);
  const in7d = new Date(now.getTime() + 7 * DAY_MS);
  const baseMatch = {
    owner_id: userId,
    is_deleted: false,
    status: { $in: ["pending", "ongoing"] },
  };

  const [overdue, dueNext7d, byPriorityRows, dueSoon] = await Promise.all([
    Task.countDocuments({ ...baseMatch, due_datetime: { $lt: now } }),
    Task.countDocuments({ ...baseMatch, due_datetime: { $gte: now, $lte: in7d } }),
    Task.aggregate([
      { $match: baseMatch },
      { $group: { _id: "$priority", count: { $sum: 1 } } },
    ]),
    Task.find({ ...baseMatch, due_datetime: { $gte: now, $lte: in48h } })
      .select("title due_datetime priority")
      .sort({ due_datetime: 1 })
      .limit(8)
      .lean(),
  ]);

  const pendingByPriority = { high: 0, medium: 0, low: 0 };
  byPriorityRows.forEach((row) => {
    const key = String(row._id || "medium").toLowerCase();
    if (Object.prototype.hasOwnProperty.call(pendingByPriority, key)) {
      pendingByPriority[key] = Number(row.count || 0);
    }
  });

  return {
    overdue,
    due_next_7d: dueNext7d,
    due_soon: dueSoon.map((task) => ({
      id: String(task._id),
      title: task.title,
      due_datetime: task.due_datetime,
      priority: task.priority,
    })),
    pending_by_priority: pendingByPriority,
  };
};

/** Composite 0–100 productivity score with a transparent component blend. */
const computeProductivityScore = ({ onTimeRate, activeDays, total, rangeDays, streakDays }) => {
  const components = {
    on_time: clamp01(onTimeRate / 100),
    consistency: clamp01(rangeDays > 0 ? activeDays / rangeDays / 0.6 : 0),
    volume: clamp01(rangeDays > 0 ? total / rangeDays / 0.8 : 0),
    streak: clamp01(streakDays / 7),
  };
  const score = Math.round(
    100 *
      (0.35 * components.on_time +
        0.25 * components.consistency +
        0.25 * components.volume +
        0.15 * components.streak),
  );
  const rating =
    SCORE_RATINGS.find((r) => score >= r.min) ||
    SCORE_RATINGS[SCORE_RATINGS.length - 1];
  return { score, rating: rating.label, caption: rating.caption };
};

/** Rule-based narrative cards. Never introduces a metric not shown elsewhere. */
const buildInsights = ({
  allTimeCompleted,
  snapshot,
  peakCell,
  byPriority,
  timeOfDay,
  overdue,
  activeDays,
  rangeDays,
}) => {
  const insights = [];
  const push = (type, icon, title, message) =>
    insights.push({ id: `${insights.length + 1}`, type, icon, title, message });

  if (allTimeCompleted === 0) {
    push(
      "tip",
      "rocket_launch",
      "Let's get started",
      "Complete your first task to unlock your productivity insights.",
    );
    return insights;
  }

  const streak = snapshot.current_streak || 0;
  if (streak >= 3) {
    push(
      "positive",
      "local_fire_department",
      "On a roll",
      `${streak}-day completion streak — keep the momentum going!`,
    );
  }

  const change = snapshot.completed.change_percent || 0;
  if (change >= 10) {
    push(
      "positive",
      "trending_up",
      "Trending up",
      `You've completed ${snapshot.completed.period} tasks — ${Math.round(Math.abs(change))}% more than the previous ${rangeDays} days.`,
    );
  } else if (change <= -20 && (snapshot.completed.previous || 0) > 0) {
    push(
      "warning",
      "trending_down",
      "Slower stretch",
      `Completions are down ${Math.round(Math.abs(change))}% versus the previous ${rangeDays} days — a small push gets you back on track.`,
    );
  }

  const onTimeRate = snapshot.on_time_rate || 0;
  if (onTimeRate >= 85) {
    push(
      "positive",
      "verified",
      "Reliably on time",
      `You finish ${onTimeRate}% of your tasks on schedule. Excellent discipline.`,
    );
  } else if (onTimeRate > 0 && onTimeRate < 60 && snapshot.completed.period >= 10) {
    push(
      "tip",
      "schedule",
      "Beat the deadline",
      `Only ${onTimeRate}% of tasks finish on time. Try scheduling them inside your peak window.`,
    );
  }

  if (peakCell) {
    push(
      "info",
      "bolt",
      "Your power hours",
      `You're most productive on ${peakCell.day_name} around ${peakCell.hour_display}.`,
    );
  }

  const high = (byPriority || []).find((p) => p.priority === "high");
  if (high && high.completed >= 3 && high.on_time_rate < onTimeRate - 15) {
    push(
      "tip",
      "priority_high",
      "High-priority tasks slip",
      `High-priority tasks are on time only ${high.on_time_rate}% of the time — plan them earlier in the day.`,
    );
  }

  if ((overdue || 0) > 0) {
    push(
      "warning",
      "warning_amber",
      "Overdue tasks waiting",
      `You have ${overdue} overdue task${overdue > 1 ? "s" : ""}. Clearing them lifts your score.`,
    );
  }

  const dominant = [...(timeOfDay || [])].sort((a, b) => b.count - a.count)[0];
  if (dominant && dominant.percent >= 40) {
    push(
      "info",
      "wb_sunny",
      `${dominant.label} person`,
      `${dominant.percent}% of your work happens in the ${dominant.label.toLowerCase()} (${dominant.range_display}).`,
    );
  }

  if (rangeDays > 0 && activeDays / rangeDays >= 0.6) {
    push(
      "positive",
      "calendar_month",
      "Consistent presence",
      `Active on ${activeDays} of the last ${rangeDays} days — consistency is your superpower.`,
    );
  }

  return insights.slice(0, 5);
};

// ─── orchestrator ─────────────────────────────────────────────────────────

const buildDashboard = async ({
  userId,
  timezone,
  rangeDays = 30,
  behavioralPayload,
}) => {
  const tz = normalizeTimezone(timezone);
  const now = Date.now();

  const [rangeLogs, streakDays, previousCount, allTimeCompleted, needsAttention] =
    await Promise.all([
      fetchRangeCompletionLogs(userId, rangeDays),
      computeStreakDays(userId, tz),
      countCompletionsInRange(
        userId,
        new Date(now - 2 * rangeDays * DAY_MS),
        new Date(now - rangeDays * DAY_MS),
      ),
      countAllTimeCompleted(userId),
      getNeedsAttention(userId),
    ]);

  const activity = buildActivity(rangeLogs, rangeDays, tz);
  const periodTotal = activity._total;
  const onTimeRate = pct(activity._onTime, periodTotal);
  const changePercent =
    previousCount > 0
      ? roundTo(((periodTotal - previousCount) / previousCount) * 100, 1)
      : periodTotal > 0
        ? 100
        : 0;

  const snapshot = {
    productivity_score: computeProductivityScore({
      onTimeRate,
      activeDays: activity.active_days,
      total: periodTotal,
      rangeDays,
      streakDays,
    }),
    on_time_rate: onTimeRate,
    current_streak: streakDays,
    completed: {
      period: periodTotal,
      previous: previousCount,
      change_percent: changePercent,
    },
  };

  const productivityMap = buildProductivityMap(rangeLogs, behavioralPayload);
  const timeOfDay = buildTimeOfDay(rangeLogs, tz);
  const byPriority = buildByPriority(rangeLogs);

  const insights = buildInsights({
    allTimeCompleted,
    snapshot,
    peakCell: [...productivityMap.cells].sort((a, b) => b.count - a.count)[0] || null,
    byPriority,
    timeOfDay,
    overdue: needsAttention.overdue,
    activeDays: activity.active_days,
    rangeDays,
  });

  return {
    generated_at: new Date().toISOString(),
    timezone: tz,
    range_days: rangeDays,
    meta: {
      has_enough_data: allTimeCompleted >= ANALYTICS_MIN_TASKS_THRESHOLD,
      min_tasks: ANALYTICS_MIN_TASKS_THRESHOLD,
      tasks_remaining: Math.max(0, ANALYTICS_MIN_TASKS_THRESHOLD - allTimeCompleted),
    },
    snapshot,
    insights,
    activity: {
      series: activity.series,
      active_days: activity.active_days,
      avg_per_active_day: activity.avg_per_active_day,
    },
    productivity_map: productivityMap,
    work_patterns: {
      time_of_day: timeOfDay,
      by_priority: byPriority,
    },
    needs_attention: needsAttention,
  };
};

module.exports = {
  parseRangeDays,
  buildDashboard,
  buildActivity,
  buildHeatmapCells,
  buildBestSlots,
  buildUnreliableDays,
  buildTimeOfDay,
  buildByPriority,
  computeProductivityScore,
  buildInsights,
  DAY_LABELS,
  HOUR_LABELS,
  HEATMAP_HOUR_START,
  HEATMAP_HOUR_END,
};

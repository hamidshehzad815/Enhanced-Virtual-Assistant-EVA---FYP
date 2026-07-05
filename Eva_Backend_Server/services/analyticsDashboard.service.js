/**
 * Analytics dashboard aggregations for the web UI.
 *
 * De-duplicated, behavior-forward payload where every headline metric has
 * exactly ONE home:
 *   1. snapshot        — score, on-time rate, streak, completed (+Δ)
 *   2. insights        — narrative cards derived from the sections below
 *   3. activity        — daily completion series (a breakdown of the total)
 *   4. behavioral      — FLAGSHIP: top-3 days (each with their best hours),
 *                        focus time, momentum, procrastination, unreliable days
 *   5. heatmap         — day × hour completion grid (6AM–11PM)
 *   6. work_patterns   — time-of-day + priority breakdowns
 *   7. needs_attention — overdue / due-soon / pending
 *
 * The behavioral day/hour ranking prefers the AI server's scored output
 * (`callAIAnalytics` → `days` / `hours`) and falls back to a Mongo count-based
 * ranking when the AI server is unavailable. Everything else is Mongo.
 *
 * De-duplication rules:
 *   - Aggregate on-time rate + the canonical completed total live only in
 *     `snapshot`. Per-slice `on_time_rate` (cells / buckets / priority / behavioral)
 *     is a breakdown, not a duplicate.
 *   - `activity`, `time_of_day`, `by_priority` are breakdowns of that one total —
 *     no `total` field. The heatmap "peak" and time-of-day "dominant" are the max
 *     entries (derive client-side) and are not sent.
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
      "action_timestamp was_on_time hour_of_day day_of_week scheduled_hour scheduled_day task_priority time_taken_minutes reschedule_count",
    )
    .sort({ action_timestamp: 1 })
    .limit(3000)
    .lean();
};

/** Completion logs in the window immediately before the range (for momentum). */
const fetchPreviousCompletionLogs = (userId, rangeDays) => {
  const now = Date.now();
  return ActivityLog.find({
    user_id: { $in: buildOwnerIdFilter(userId) },
    action_type: "task_completed",
    action_timestamp: {
      $gte: new Date(now - 2 * rangeDays * DAY_MS),
      $lte: new Date(now - rangeDays * DAY_MS),
    },
  })
    .select("action_timestamp was_on_time")
    .limit(3000)
    .lean();
};

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

const buildHeatmap = (rangeLogs) => ({
  hour_range: {
    start: HEATMAP_HOUR_START,
    end: HEATMAP_HOUR_END,
    start_display: HOUR_LABELS(HEATMAP_HOUR_START),
    end_display: HOUR_LABELS(HEATMAP_HOUR_END),
  },
  cells: buildHeatmapCells(rangeLogs),
});

/**
 * Top-N most productive weekdays, each with its own best hours. Prefers the AI
 * server's scored ranking; falls back to a Mongo count ranking when unavailable.
 * All `on_time_rate` values are normalized to a 0–100 percentage.
 */
const buildTopDays = (behavioralPayload, rangeLogs, limit = 3, hoursPerDay = 3) => {
  const aiDays = behavioralPayload?.data?.days;
  const aiHours = behavioralPayload?.data?.hours || [];

  if (Array.isArray(aiDays) && aiDays.length) {
    const days = [...aiDays]
      .sort((a, b) => Number(b.score || 0) - Number(a.score || 0))
      .slice(0, limit)
      .map((day) => ({
        day: day.day || DAY_LABELS[day.day_num],
        day_num: day.day_num,
        score: roundTo(Number(day.score || 0), 2),
        log_count: Number(day.log_count || 0),
        on_time_rate: roundTo(Number(day.on_time_rate || 0) * 100, 1),
        hours: [...aiHours]
          .filter((h) => Number(h.day_num) === Number(day.day_num))
          .sort((a, b) => Number(b.score || 0) - Number(a.score || 0))
          .slice(0, hoursPerDay)
          .map((h) => ({
            hour: h.hour,
            hour_display: h.hour_display || HOUR_LABELS(h.hour),
            score: roundTo(Number(h.score || 0), 2),
            on_time_rate: roundTo(Number(h.on_time_rate || 0) * 100, 1),
            log_count: Number(h.log_count || 0),
          })),
      }));
    return { source: "ai", days };
  }

  // Mongo fallback: rank weekdays (and their hours) by completion count.
  const agg = {};
  rangeLogs.forEach((log) => {
    const d = Number(log.day_of_week);
    if (!Number.isFinite(d) || d < 0 || d > 6) return;
    if (!agg[d]) agg[d] = { count: 0, on_time: 0, hours: {} };
    agg[d].count += 1;
    if (log.was_on_time === true) agg[d].on_time += 1;
    const h = Number(log.hour_of_day);
    if (Number.isFinite(h)) {
      if (!agg[d].hours[h]) agg[d].hours[h] = { count: 0, on_time: 0 };
      agg[d].hours[h].count += 1;
      if (log.was_on_time === true) agg[d].hours[h].on_time += 1;
    }
  });

  const entries = Object.entries(agg).map(([d, v]) => ({ day_num: Number(d), ...v }));
  const maxDay = Math.max(1, ...entries.map((e) => e.count));

  const days = entries
    .sort((a, b) => b.count - a.count)
    .slice(0, limit)
    .map((entry) => {
      const hourEntries = Object.entries(entry.hours).map(([h, v]) => ({
        hour: Number(h),
        ...v,
      }));
      const maxHour = Math.max(1, ...hourEntries.map((h) => h.count));
      return {
        day: DAY_LABELS[entry.day_num],
        day_num: entry.day_num,
        score: roundTo(entry.count / maxDay, 2),
        log_count: entry.count,
        on_time_rate: pct(entry.on_time, entry.count),
        hours: hourEntries
          .sort((a, b) => b.count - a.count)
          .slice(0, hoursPerDay)
          .map((h) => ({
            hour: h.hour,
            hour_display: HOUR_LABELS(h.hour),
            score: roundTo(h.count / maxHour, 2),
            on_time_rate: pct(h.on_time, h.count),
            log_count: h.count,
          })),
      };
    });

  return { source: "history", days };
};

/** Average minutes spent per completed task in the range. */
const buildFocus = (rangeLogs) => {
  const values = rangeLogs
    .map((log) => Number(log.time_taken_minutes))
    .filter((v) => Number.isFinite(v) && v > 0);
  const avg = values.length
    ? Math.round(values.reduce((sum, v) => sum + v, 0) / values.length)
    : 0;
  return { avg_minutes: avg, sample_size: values.length };
};

/** Late-night finishing and rescheduling — gentle "watch-out" signals. */
const buildProcrastination = (rangeLogs) => {
  const total = rangeLogs.length;
  let lateNight = 0;
  let rescheduled = 0;
  rangeLogs.forEach((log) => {
    const h = Number(log.hour_of_day);
    if (Number.isFinite(h) && (h >= 22 || h < 5)) lateNight += 1;
    if (Number(log.reschedule_count) > 0) rescheduled += 1;
  });
  return {
    late_night_rate: pct(lateNight, total),
    reschedule_rate: pct(rescheduled, total),
  };
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

/** Behaviour sub-score (on-time / consistency / volume, no streak) 0–100. */
const computeBehaviorScore = ({ onTimeRate, activeDays, total, rangeDays }) =>
  Math.round(
    100 *
      (0.4 * clamp01(onTimeRate / 100) +
        0.3 * clamp01(rangeDays > 0 ? activeDays / rangeDays / 0.6 : 0) +
        0.3 * clamp01(rangeDays > 0 ? total / rangeDays / 0.8 : 0)),
  );

const buildMomentum = (currentScore, previousScore) => {
  const delta = currentScore - previousScore;
  let direction = "steady";
  if (delta >= 3) direction = "up";
  else if (delta <= -3) direction = "down";
  const label =
    direction === "up"
      ? "Your habits are improving versus the previous period."
      : direction === "down"
        ? "Your habits dipped versus the previous period."
        : "Holding steady versus the previous period.";
  return { direction, delta, label };
};

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

/** On-time reliability + average focus time per priority. */
const buildByPriority = (rangeLogs) => {
  const counters = {};
  PRIORITY_ORDER.forEach((priority) => {
    counters[priority] = { completed: 0, on_time: 0, minutes: 0, minutesCount: 0 };
  });

  rangeLogs.forEach((log) => {
    const priority = String(log.task_priority || "").toLowerCase();
    if (!counters[priority]) return;
    counters[priority].completed += 1;
    if (log.was_on_time === true) counters[priority].on_time += 1;
    const minutes = Number(log.time_taken_minutes);
    if (Number.isFinite(minutes) && minutes > 0) {
      counters[priority].minutes += minutes;
      counters[priority].minutesCount += 1;
    }
  });

  const totalKnown = PRIORITY_ORDER.reduce(
    (sum, priority) => sum + counters[priority].completed,
    0,
  );

  return PRIORITY_ORDER.map((priority) => {
    const c = counters[priority];
    return {
      priority,
      label: PRIORITY_LABELS[priority],
      completed: c.completed,
      on_time_rate: pct(c.on_time, c.completed),
      percent: pct(c.completed, totalKnown),
      avg_minutes: c.minutesCount ? Math.round(c.minutes / c.minutesCount) : 0,
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
  behavioral,
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

  // Prefer the scored top day/hour; fall back to the busiest heatmap cell.
  const topDay = behavioral?.top_days?.[0];
  const topHour = topDay?.hours?.[0];
  if (topDay && topHour) {
    push(
      "info",
      "bolt",
      "Your power hours",
      `You're most productive on ${topDay.day} around ${topHour.hour_display}.`,
    );
  } else if (peakCell) {
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

  if (behavioral?.momentum?.direction === "up") {
    push("positive", "rocket_launch", "Gaining momentum", behavioral.momentum.label);
  } else if (behavioral?.momentum?.direction === "down") {
    push("warning", "trending_down", "Losing momentum", behavioral.momentum.label);
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

  const [rangeLogs, previousLogs, streakDays, allTimeCompleted, needsAttention] =
    await Promise.all([
      fetchRangeCompletionLogs(userId, rangeDays),
      fetchPreviousCompletionLogs(userId, rangeDays),
      computeStreakDays(userId, tz),
      countAllTimeCompleted(userId),
      getNeedsAttention(userId),
    ]);

  // Current-period aggregates
  const activity = buildActivity(rangeLogs, rangeDays, tz);
  const periodTotal = activity._total;
  const onTimeRate = pct(activity._onTime, periodTotal);

  // Previous-period aggregates (for Δ + momentum)
  const previousCount = previousLogs.length;
  const previousOnTime = previousLogs.filter((l) => l.was_on_time === true).length;
  const previousActiveDays = new Set(
    previousLogs.map((l) => localDateKey(new Date(l.action_timestamp), tz)),
  ).size;

  const changePercent =
    previousCount > 0
      ? roundTo(((periodTotal - previousCount) / previousCount) * 100, 1)
      : periodTotal > 0
        ? 100
        : 0;

  const momentum = buildMomentum(
    computeBehaviorScore({
      onTimeRate,
      activeDays: activity.active_days,
      total: periodTotal,
      rangeDays,
    }),
    computeBehaviorScore({
      onTimeRate: pct(previousOnTime, previousCount),
      activeDays: previousActiveDays,
      total: previousCount,
      rangeDays,
    }),
  );

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

  const topDays = buildTopDays(behavioralPayload, rangeLogs, 3, 3);
  const behavioral = {
    has_scores: topDays.days.length > 0,
    source: topDays.source,
    top_days: topDays.days,
    focus: buildFocus(rangeLogs),
    momentum,
    procrastination: buildProcrastination(rangeLogs),
    unreliable_days: buildUnreliableDays(rangeLogs),
  };

  const heatmap = buildHeatmap(rangeLogs);
  const timeOfDay = buildTimeOfDay(rangeLogs, tz);
  const byPriority = buildByPriority(rangeLogs);

  const insights = buildInsights({
    allTimeCompleted,
    snapshot,
    behavioral,
    peakCell: [...heatmap.cells].sort((a, b) => b.count - a.count)[0] || null,
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
    behavioral,
    heatmap,
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
  buildHeatmap,
  buildHeatmapCells,
  buildTopDays,
  buildFocus,
  buildProcrastination,
  buildUnreliableDays,
  computeBehaviorScore,
  buildMomentum,
  buildTimeOfDay,
  buildByPriority,
  computeProductivityScore,
  buildInsights,
  DAY_LABELS,
  HOUR_LABELS,
  HEATMAP_HOUR_START,
  HEATMAP_HOUR_END,
};

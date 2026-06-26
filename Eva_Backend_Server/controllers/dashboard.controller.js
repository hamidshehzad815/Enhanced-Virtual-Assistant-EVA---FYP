/**
 * Dashboard Controller
 * Aggregated dashboard data for home screen widgets.
 */

const { Task, LearningGoal, RoadmapTopic } = require("../models");
const { normalizeTimezone, toLocalDayRangeUtc } = require("../utils/timezone");
const { serializeInstantForApi, withApiTimezone } = require("../utils/apiDateTime");
const {
  isStoredComplete,
  computeTaskDisplayStatus,
  normalizeStoredStatus,
} = require("../utils/taskDisplayStatus");

const toLocalDateString = (timeZone, dateValue = new Date()) => {
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
  const parts = formatter.formatToParts(dateValue);
  const partMap = {};
  parts.forEach((part) => {
    if (part.type !== "literal") {
      partMap[part.type] = part.value;
    }
  });
  return `${partMap.year}-${partMap.month}-${partMap.day}`;
};

const formatDayTime = (dateValue, timeZone) => {
  const value = new Date(dateValue);
  if (Number.isNaN(value.getTime())) {
    return { day: null, time: null };
  }

  const day = new Intl.DateTimeFormat("en-US", {
    timeZone,
    weekday: "long",
  }).format(value);
  const time = new Intl.DateTimeFormat("en-US", {
    timeZone,
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(value);

  return { day, time };
};

const buildDashboardTask = (task, timeZone, nowUtc = new Date()) => {
  const due = task?.due_datetime ? new Date(task.due_datetime) : null;
  const formatted = due ? formatDayTime(due, timeZone) : { day: null, time: null };
  return {
    task_id: String(task._id),
    title: task.title,
    status: normalizeStoredStatus(task.status),
    display_status: computeTaskDisplayStatus(task, nowUtc),
    priority: task.priority,
    day: formatted.day,
    time: formatted.time,
    due_datetime: due ? serializeInstantForApi(due, timeZone) : null,
    is_learning_task: Boolean(task.learning_plan_id),
    learning_goal_id: task.learning_plan_id ? String(task.learning_plan_id) : null,
    learning_session_id: task.learning_topic_id ? String(task.learning_topic_id) : null,
    editable: !task.learning_plan_id,
  };
};

const buildLearningTopic = (topic, timeZone) => {
  if (!topic) {
    return null;
  }
  const due = topic?.scheduled_date ? new Date(topic.scheduled_date) : null;
  const formatted = due ? formatDayTime(due, timeZone) : { day: null, time: null };
  return {
    topic_id: String(topic._id),
    title: topic.title,
    status: topic.status,
    day: formatted.day,
    time: formatted.time,
    scheduled_datetime: due ? serializeInstantForApi(due, timeZone) : null,
  };
};

/**
 * GET /api/dashboard
 * Returns: up_next, daily_progress, learning, today_schedule.
 */
const getDashboard = async (req, res, next) => {
  try {
    const timeZone = normalizeTimezone(req.user?.timezone || "UTC");
    const todayLocal = toLocalDateString(timeZone);
    const range = toLocalDayRangeUtc(todayLocal, timeZone);

    const tasksQuery = {
      is_deleted: false,
      due_datetime: {
        $gte: range.start,
        $lte: range.end,
      },
      $or: [
        { owner_id: req.userId },
        {
          collaborators: {
            $elemMatch: {
              user_id: req.userId,
              status: "accepted",
            },
          },
        },
      ],
    };

    const [todayTasks, goals] = await Promise.all([
      Task.find(tasksQuery).sort({ due_datetime: 1, created_at: 1 }).lean(),
      LearningGoal.find({
        user_id: req.userId,
        is_deleted: false,
        status: { $in: ["active", "paused"] },
      })
        .sort({ created_at: -1 })
        .lean(),
    ]);

    const nowUtc = new Date();
    const upNextTask =
      todayTasks.find(
        (task) => computeTaskDisplayStatus(task, nowUtc) !== "complete",
      ) || null;

    const completedCount = todayTasks.filter((task) => isStoredComplete(task.status)).length;
    const totalCount = todayTasks.length;
    const completionPercentage =
      totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

    let learning = [];
    if (goals.length > 0) {
      const goalIds = goals.map((goal) => goal._id);
      const pendingTopics = await RoadmapTopic.find({
        goal_id: { $in: goalIds },
        is_deleted: false,
        status: { $in: ["pending", "ongoing"] },
      })
        .sort({ goal_id: 1, order: 1, scheduled_date: 1 })
        .lean();

      const firstTopicByGoal = new Map();
      pendingTopics.forEach((topic) => {
        const key = String(topic.goal_id);
        if (!firstTopicByGoal.has(key)) {
          firstTopicByGoal.set(key, topic);
        }
      });

      learning = goals.map((goal) => {
        const totalTopics = Number(goal.total_topics || 0);
        const doneTopics = Number(goal.completed_topics || 0);
        const progressPercent =
          totalTopics > 0 ? Math.min(100, Math.round((doneTopics / totalTopics) * 100)) : 0;

        return {
          learning_goal_id: String(goal._id),
          title: goal.title,
          roadmap_key: goal.roadmap_key || null,
          status: goal.status,
          progress_percent: progressPercent,
          next_topic: buildLearningTopic(firstTopicByGoal.get(String(goal._id)), timeZone),
        };
      });
    }

    return res.json({
      status: "success",
      data: withApiTimezone(
        {
          up_next: upNextTask ? buildDashboardTask(upNextTask, timeZone, nowUtc) : null,
          daily_progress: {
            date: todayLocal,
            timezone: timeZone,
            completed_tasks: completedCount,
            total_tasks: totalCount,
            completion_percentage: completionPercentage,
          },
          learning,
          today_schedule: todayTasks.map((task) => buildDashboardTask(task, timeZone, nowUtc)),
        },
        timeZone,
      ),
    });
  } catch (error) {
    return next(error);
  }
};

module.exports = {
  getDashboard,
};


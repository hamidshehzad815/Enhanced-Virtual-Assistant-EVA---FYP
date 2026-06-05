/**
 * Learning Auto-complete Job (Phase 6)
 * - Runs every 15 minutes
 * - Finds pending roadmap topics where:
 *     scheduled_date + estimated_duration(min) + 180min <= now
 * - Calls AI server: POST /internal/auto-complete-topic
 * - Best-effort: doesn't crash the process on partial failures
 */

const cron = require("node-cron");
const axios = require("axios");

const logger = require("../config/logger");
const { RoadmapTopic, LearningGoal } = require("../models");

const AI_SERVER_URL = process.env.AI_SERVER_URL || "http://localhost:8080";
const AI_SERVER_TIMEOUT_MS = Number(process.env.AI_SERVER_TIMEOUT_MS || 15000);

let activeJob = null;
let isRunning = false;

const minutes = (n) => Number(n) * 60 * 1000;

const computeDeadline = (topic) => {
  const scheduled = topic?.scheduled_date ? new Date(topic.scheduled_date) : null;
  if (!scheduled || Number.isNaN(scheduled.getTime())) {
    return null;
  }
  const durationMin = Math.max(1, Number(topic.estimated_duration || 90));
  return new Date(scheduled.getTime() + minutes(durationMin + 180));
};

const findDueTopics = async (now) => {
  // Narrow by base criteria in Mongo; deadline calculation uses JS for simplicity.
  const candidates = await RoadmapTopic.find({
    status: "pending",
    is_deleted: false,
    scheduled_date: { $ne: null },
  })
    .select("_id goal_id scheduled_date estimated_duration")
    .lean();

  if (!candidates.length) {
    return [];
  }

  // Filter to those past deadline and whose goal is active (best-effort)
  const due = candidates.filter((t) => {
    const deadline = computeDeadline(t);
    return deadline && deadline <= now;
  });

  if (!due.length) {
    return [];
  }

  const goalIds = [...new Set(due.map((t) => String(t.goal_id)).filter(Boolean))];
  const goals = await LearningGoal.find(
    { _id: { $in: goalIds }, status: "active", is_deleted: false },
    { _id: 1, user_id: 1 },
  ).lean();

  const goalById = new Map(goals.map((g) => [String(g._id), g]));
  return due
    .map((t) => {
      const goal = goalById.get(String(t.goal_id));
      if (!goal) {
        return null;
      }
      return { topic: t, goal };
    })
    .filter(Boolean);
};

const callAutoComplete = async ({ topicId, goalId, userId }) => {
  const response = await axios.post(
    `${AI_SERVER_URL}/internal/auto-complete-topic`,
    { topic_id: topicId, goal_id: goalId, user_id: userId },
    { timeout: AI_SERVER_TIMEOUT_MS },
  );
  return response.data;
};

const runAutoCompleteCycle = async () => {
  if (isRunning) {
    logger.warn(
      "Learning auto-complete job skipped because previous cycle is still running",
    );
    return { checked: 0, completed: 0, failed: 0 };
  }

  isRunning = true;
  try {
    const now = new Date();
    const rows = await findDueTopics(now);
    if (!rows.length) {
      return { checked: 0, completed: 0, failed: 0 };
    }

    let completed = 0;
    let failed = 0;

    for (const row of rows) {
      const topicId = String(row.topic._id);
      const goalId = String(row.goal._id);
      const userId = String(row.goal.user_id);
      try {
        await callAutoComplete({ topicId, goalId, userId });
        completed += 1;
      } catch (error) {
        failed += 1;
        logger.error("Learning auto-complete AI call failed", {
          topic_id: topicId,
          goal_id: goalId,
          user_id: userId,
          error: error?.message,
        });
      }
    }

    return { checked: rows.length, completed, failed };
  } catch (error) {
    logger.error("Learning auto-complete cycle failed", { error: error.message });
    return { checked: 0, completed: 0, failed: 1 };
  } finally {
    isRunning = false;
  }
};

const startLearningAutoCompleteJob = () => {
  if (activeJob) {
    return activeJob;
  }
  // every 15 minutes
  activeJob = cron.schedule("*/15 * * * *", runAutoCompleteCycle, {
    scheduled: true,
  });
  logger.info("Learning auto-complete job started (every 15 minutes)");
  return activeJob;
};

const stopLearningAutoCompleteJob = () => {
  if (!activeJob) {
    return;
  }
  activeJob.stop();
  activeJob = null;
  logger.info("Learning auto-complete job stopped");
};

module.exports = {
  computeDeadline,
  findDueTopics,
  runAutoCompleteCycle,
  startLearningAutoCompleteJob,
  stopLearningAutoCompleteJob,
};


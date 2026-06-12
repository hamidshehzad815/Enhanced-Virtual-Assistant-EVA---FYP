/**
 * User-created learning roadmaps (learning_goals collection).
 */

const { LearningGoal, RoadmapTopic } = require("../models");
const {
  normalizeSubjectFilter,
  subjectToDisplay,
  formatTrackLabel,
} = require("../utils/learningSubject");
const { enrichSessionsForGoal } = require("../utils/learningSessionState");
const {
  serializeInstantForApi,
  serializeDateOnlyForApi,
  withApiTimezone,
} = require("../utils/apiDateTime");

const GOAL_STATUSES = new Set(["active", "paused", "completed", "cancelled"]);

const GOAL_LIST_PROJECTION =
  "title subject roadmap_key status start_date end_date total_topics completed_topics";

const TOPIC_LIST_PROJECTION =
  "goal_id order title status scheduled_date estimated_duration completed_at updated_at resources";

const toProgressPercent = (goal) => {
  const total = Number(goal.total_topics || 0);
  const done = Number(goal.completed_topics || 0);
  if (total <= 0) {
    return 0;
  }
  return Math.min(100, Math.round((done / total) * 100));
};

const serializeSession = (topic, timezone = "UTC", meta = {}) => {
  const status = topic.status;
  const payload = {
    id: String(topic._id),
    order: Number(topic.order || 0),
    title: topic.title,
    status,
    scheduled_date: topic.scheduled_date
      ? serializeInstantForApi(topic.scheduled_date, timezone)
      : null,
    estimated_duration: Number(topic.estimated_duration || 0),
    resources: Array.isArray(topic.resources) ? topic.resources : [],
    session_state: meta.session_state,
    is_current: Boolean(meta.is_current),
    unlock_at: meta.unlock_at ?? null,
  };

  if (status === "completed" || status === "skipped") {
    payload.completed_at = topic.completed_at
      ? serializeInstantForApi(topic.completed_at, timezone)
      : null;
  }

  return payload;
};

const buildSessionsSummary = (sessionList) => ({
  completed: sessionList.filter((s) => s.status === "completed").length,
  skipped: sessionList.filter((s) => s.status === "skipped").length,
  pending: sessionList.filter((s) => s.status === "pending").length,
  ongoing: sessionList.filter((s) => s.status === "ongoing").length,
});

const serializeRoadmap = (goal, sessions = [], timezone = "UTC") => {
  const subject = String(goal.subject || "").trim().toLowerCase();
  const sessionList = Array.isArray(sessions) ? sessions : [];

  return {
    id: String(goal._id),
    title: goal.title,
    language: subjectToDisplay(subject),
    track_label: formatTrackLabel(goal.roadmap_key),
    status: goal.status,
    start_date: goal.start_date
      ? serializeDateOnlyForApi(goal.start_date, timezone)
      : null,
    end_date: goal.end_date
      ? serializeDateOnlyForApi(goal.end_date, timezone)
      : null,
    completed_topics: Number(goal.completed_topics || 0),
    total_topics: Number(goal.total_topics || 0),
    progress_percent: toProgressPercent(goal),
    session_count: sessionList.length,
    sessions_summary: buildSessionsSummary(sessionList),
    sessions: sessionList,
  };
};

const loadSessionsByGoalId = async (goalIds, timezone = "UTC") => {
  if (!goalIds.length) {
    return new Map();
  }

  const topics = await RoadmapTopic.find({
    goal_id: { $in: goalIds },
    is_deleted: false,
  })
    .select(TOPIC_LIST_PROJECTION)
    .sort({ goal_id: 1, order: 1 })
    .lean();

  const grouped = new Map();
  goalIds.forEach((id) => grouped.set(String(id), []));

  topics.forEach((topic) => {
    const key = String(topic.goal_id);
    if (!grouped.has(key)) {
      grouped.set(key, []);
    }
    grouped.get(key).push(topic);
  });

  grouped.forEach((goalTopics, key) => {
    const now = new Date();
    const enrichedMeta = enrichSessionsForGoal(goalTopics, now);
    grouped.set(
      key,
      goalTopics.map((topic, index) => {
        const meta = enrichedMeta[index] || {};
        return serializeSession(topic, timezone, {
          session_state: meta.session_state,
          is_current: meta.is_current,
          unlock_at: meta.unlock_at
            ? serializeInstantForApi(meta.unlock_at, timezone)
            : null,
        });
      }),
    );
  });

  return grouped;
};

const parseStatusFilter = (raw) => {
  if (!raw) {
    return null;
  }
  const values = String(raw)
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter((s) => GOAL_STATUSES.has(s));

  return values.length ? values : null;
};

const buildGoalsQuery = (userId, filters = {}) => {
  const query = {
    user_id: userId,
    is_deleted: false,
  };

  if (filters.subject) {
    query.subject = filters.subject;
  }

  if (filters.statuses?.length) {
    query.status = { $in: filters.statuses };
  }

  if (filters.roadmap_key) {
    query.roadmap_key = filters.roadmap_key;
  }

  return query;
};

/**
 * Distinct languages (subjects) the user has at least one non-deleted roadmap for.
 */
const listUserLanguages = async (userId) => {
  const subjects = await LearningGoal.distinct("subject", {
    user_id: userId,
    is_deleted: false,
    subject: { $nin: [null, ""] },
  });

  return subjects
    .map((subject) => {
      const key = String(subject).trim().toLowerCase();
      return {
        key,
        label: subjectToDisplay(key),
      };
    })
    .sort((a, b) => a.label.localeCompare(b.label));
};

/**
 * List user's roadmaps with optional filters.
 */
const listUserRoadmaps = async (userId, filters = {}, timezone = "UTC") => {
  const subject = filters.languageInput
    ? normalizeSubjectFilter(filters.languageInput)
    : null;

  const statuses = parseStatusFilter(filters.statusInput);
  const roadmapKey = String(filters.roadmapKeyInput || "").trim().toLowerCase() || null;
  const includeSessions = filters.includeSessions !== false;

  const query = buildGoalsQuery(userId, {
    subject,
    statuses,
    roadmap_key: roadmapKey,
  });

  const goals = await LearningGoal.find(query)
    .select(GOAL_LIST_PROJECTION)
    .sort({ created_at: -1 })
    .lean();

  let sessionsByGoal = new Map();
  if (includeSessions && goals.length > 0) {
    sessionsByGoal = await loadSessionsByGoalId(
      goals.map((g) => g._id),
      timezone,
    );
  }

  return withApiTimezone(
    {
    filters: {
      language: subject ? subjectToDisplay(subject) : null,
      subject,
      status: statuses,
      roadmap_key: roadmapKey,
      include_sessions: includeSessions,
    },
    roadmaps: goals.map((goal) =>
      serializeRoadmap(
        goal,
        includeSessions ? sessionsByGoal.get(String(goal._id)) || [] : [],
        timezone,
      ),
    ),
    count: goals.length,
  },
    timezone,
  );
};

module.exports = {
  GOAL_STATUSES,
  listUserLanguages,
  listUserRoadmaps,
  serializeRoadmap,
  serializeSession,
  buildGoalsQuery,
  enrichSessionsForGoal,
};

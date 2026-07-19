/**
 * User-created learning roadmaps (learning_goals collection).
 */

const mongoose = require("mongoose");
const { LearningGoal, RoadmapTopic, UserSetting } = require("../models");
const { BadRequestError, NotFoundError } = require("../middleware/errorHandler");
const {
  subjectToDisplay,
  formatTrackLabel,
} = require("../utils/learningSubject");
const { enrichSessionsForGoal } = require("../utils/learningSessionState");
const {
  serializeInstantForApi,
  serializeDateOnlyForApi,
  withApiTimezone,
} = require("../utils/apiDateTime");
const { buildPlanScheduleDates, MAX_HORIZON_WEEKS } = require("../utils/planScheduleDates");
const {
  buildCollaboratorProgressForGoals,
} = require("./collaboratorProgress.service");

const GOAL_STATUSES = new Set(["active", "paused", "completed", "cancelled"]);

const GOAL_LIST_PROJECTION =
  "user_id title subject roadmap_key status start_date end_date total_topics completed_topics created_at updated_at learning_schedule_id collaborators source_goal_id";

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
    // Which collaborators have reached / finished this session (by order).
    // Populated by the roadmap-detail path; empty for solo plans.
    collaborator_progress: Array.isArray(meta.collaborator_progress)
      ? meta.collaborator_progress
      : [],
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

const serializeRoadmap = (goal, sessions = [], timezone = "UTC", collaborators = []) => {
  const subject = String(goal.subject || "").trim().toLowerCase();
  const sessionList = Array.isArray(sessions) ? sessions : [];

  return {
    id: String(goal._id),
    title: goal.title,
    language: subjectToDisplay(subject),
    language_key: subject,
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
    collaborators: Array.isArray(collaborators) ? collaborators : [],
    sessions: sessionList,
  };
};

/** Roadmap header for session detail — no sessions[] list */
const serializeRoadmapSummary = (goal, sessions = [], timezone = "UTC", collaborators = []) => {
  const full = serializeRoadmap(goal, sessions, timezone, collaborators);
  const { sessions: _sessions, ...summary } = full;
  return summary;
};

/** Plan card / list item — roadmap metadata only (no sessions[]). */
const serializeRoadmapPlan = (goal, sessionsSummary = null, timezone = "UTC", collaborators = []) => {
  const subject = String(goal.subject || "").trim().toLowerCase();
  const total = Number(goal.total_topics || 0);
  const completed = Number(goal.completed_topics || 0);
  const summary = sessionsSummary || {
    completed,
    skipped: 0,
    pending: Math.max(0, total - completed),
    ongoing: 0,
  };

  return {
    id: String(goal._id),
    title: goal.title,
    language: subjectToDisplay(subject),
    language_key: subject,
    track_label: formatTrackLabel(goal.roadmap_key),
    status: goal.status,
    start_date: goal.start_date
      ? serializeDateOnlyForApi(goal.start_date, timezone)
      : null,
    end_date: goal.end_date
      ? serializeDateOnlyForApi(goal.end_date, timezone)
      : null,
    completed_topics: completed,
    total_topics: total,
    progress_percent: toProgressPercent(goal),
    session_count: total,
    sessions_summary: summary,
    collaborators: Array.isArray(collaborators) ? collaborators : [],
  };
};

const loadSessionsSummaryByGoalId = async (goalIds) => {
  const map = new Map();
  goalIds.forEach((id) => {
    map.set(String(id), {
      completed: 0,
      skipped: 0,
      pending: 0,
      ongoing: 0,
    });
  });

  if (!goalIds.length) {
    return map;
  }

  const rows = await RoadmapTopic.aggregate([
    {
      $match: {
        goal_id: { $in: goalIds },
        is_deleted: false,
      },
    },
    {
      $group: {
        _id: { goal_id: "$goal_id", status: "$status" },
        count: { $sum: 1 },
      },
    },
  ]);

  rows.forEach((row) => {
    const goalId = String(row._id.goal_id);
    const status = String(row._id.status || "").toLowerCase();
    const bucket = map.get(goalId);
    if (!bucket) {
      return;
    }
    if (status === "completed") {
      bucket.completed = row.count;
    } else if (status === "skipped") {
      bucket.skipped = row.count;
    } else if (status === "ongoing") {
      bucket.ongoing = row.count;
    } else if (status === "pending") {
      bucket.pending = row.count;
    }
  });

  return map;
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
 * Single roadmap with sessions for one learning goal (by goal id).
 */
const getUserRoadmapForGoalId = async (userId, goalIdInput, timezone = "UTC") => {
  const goalId = String(goalIdInput || "").trim();
  if (!mongoose.Types.ObjectId.isValid(goalId)) {
    throw new BadRequestError("Invalid goal id");
  }

  const goal = await LearningGoal.findOne({
    _id: goalId,
    user_id: userId,
    is_deleted: false,
  })
    .select(GOAL_LIST_PROJECTION)
    .lean();

  if (!goal) {
    throw new NotFoundError("Learning goal not found");
  }

  const subject = String(goal.subject || "").trim().toLowerCase();
  const sessionsByGoal = await loadSessionsByGoalId([goal._id], timezone);
  const sessions = sessionsByGoal.get(String(goal._id)) || [];

  // Collaborator profiles + per-session progress on the shared roadmap.
  const progressByGoal = await buildCollaboratorProgressForGoals([goal]);
  const { collaborators, perSession } =
    progressByGoal.get(String(goal._id)) || { collaborators: [], perSession: new Map() };

  const sessionsWithCollaborators = sessions.map((session) => ({
    ...session,
    collaborator_progress: perSession.get(Number(session.order)) || [],
  }));

  return withApiTimezone(
    {
      language: {
        key: subject,
        label: subjectToDisplay(subject),
      },
      roadmap: serializeRoadmap(goal, sessionsWithCollaborators, timezone, collaborators),
    },
    timezone,
  );
};

/**
 * All learning plans for the user (no sessions[] — use GET /api/roadmaps/:goalId for sessions).
 */
const listUserRoadmapPlans = async (userId, timezone = "UTC", filters = {}) => {
  const statuses = parseStatusFilter(filters.statusInput);

  const query = buildGoalsQuery(userId, { statuses });

  const goals = await LearningGoal.find(query)
    .select(GOAL_LIST_PROJECTION)
    .sort({ updated_at: -1, created_at: -1 })
    .lean();

  const goalIds = goals.map((goal) => goal._id);
  const summariesByGoal = await loadSessionsSummaryByGoalId(goalIds);
  const progressByGoal = await buildCollaboratorProgressForGoals(goals);

  const roadmaps = goals.map((goal) =>
    serializeRoadmapPlan(
      goal,
      summariesByGoal.get(String(goal._id)),
      timezone,
      (progressByGoal.get(String(goal._id)) || {}).collaborators || [],
    ),
  );

  return withApiTimezone({ roadmaps }, timezone);
};

/**
 * Reschedule-eligible calendar dates for a plan (learning-schedule weekdays only).
 */
const getPlanScheduleDatesForGoal = async (
  userId,
  goalIdInput,
  timezone = "UTC",
  options = {},
) => {
  const goalId = String(goalIdInput || "").trim();
  if (!mongoose.Types.ObjectId.isValid(goalId)) {
    throw new BadRequestError("Invalid goal id");
  }

  const goal = await LearningGoal.findOne({
    _id: goalId,
    user_id: userId,
    is_deleted: false,
  })
    .select(`${GOAL_LIST_PROJECTION} duration_days`)
    .lean();

  if (!goal) {
    throw new NotFoundError("Learning goal not found");
  }

  if (String(goal.status || "").toLowerCase() !== "active") {
    throw new BadRequestError(
      "Schedule dates are only available for active learning plans.",
    );
  }

  const settings = await UserSetting.findOne({ user_id: userId }).lean();
  if (!settings) {
    throw new NotFoundError("User settings not found");
  }

  let horizonWeeks = Number(options.horizonWeeks);
  if (options.horizonWeeks !== undefined && options.horizonWeeks !== null) {
    if (!Number.isFinite(horizonWeeks) || horizonWeeks < 1) {
      throw new BadRequestError("horizon_weeks must be a positive integer");
    }
    if (horizonWeeks > MAX_HORIZON_WEEKS) {
      throw new BadRequestError(
        `horizon_weeks cannot exceed ${MAX_HORIZON_WEEKS}`,
      );
    }
  } else {
    horizonWeeks = undefined;
  }

  const payload = buildPlanScheduleDates(goal, settings, timezone, {
    horizonWeeks,
  });

  return withApiTimezone(payload, timezone);
};

/**
 * Refresh payload after session/plan mutations (roadmap + optional session slice).
 */
const buildRoadmapMutationPayload = async (
  userId,
  goalDoc,
  timezone = "UTC",
  { sessionId = null } = {},
) => {
  if (!goalDoc) {
    return { language: null, roadmap: null, session: null };
  }

  const subject = String(goalDoc.subject || "").trim().toLowerCase();
  const sessionsByGoal = await loadSessionsByGoalId([goalDoc._id], timezone);
  const sessions = sessionsByGoal.get(String(goalDoc._id)) || [];
  const roadmap = serializeRoadmap(goalDoc, sessions, timezone);

  let session = null;
  if (sessionId) {
    session = sessions.find((row) => row.id === String(sessionId)) || null;
  }

  return withApiTimezone(
    {
      language: subject
        ? { key: subject, label: subjectToDisplay(subject) }
        : null,
      roadmap,
      session,
      sessions,
    },
    timezone,
  );
};

/**
 * Single session detail for GET popup — session + slim roadmap (no sessions[]).
 */
const buildSessionDetailPayload = async (
  goalDoc,
  sessionId,
  timezone = "UTC",
) => {
  if (!goalDoc) {
    return { language: null, roadmap: null, session: null };
  }

  const subject = String(goalDoc.subject || "").trim().toLowerCase();
  const sessionsByGoal = await loadSessionsByGoalId([goalDoc._id], timezone);
  const sessions = sessionsByGoal.get(String(goalDoc._id)) || [];
  const session = sessions.find((row) => row.id === String(sessionId)) || null;

  return withApiTimezone(
    {
      language: subject
        ? { key: subject, label: subjectToDisplay(subject) }
        : null,
      roadmap: serializeRoadmapSummary(goalDoc, sessions, timezone),
      session,
    },
    timezone,
  );
};

/**
 * Overdue current sessions across all the user's active learning goals.
 * At most one overdue session per goal — only the lowest-order pending
 * topic is ever "current", so this never needs to surface more than one
 * per goal.
 */
const listOverdueSessionsForUser = async (userId, timezone = "UTC") => {
  const goals = await LearningGoal.find({
    user_id: userId,
    status: "active",
    is_deleted: false,
  })
    .select(GOAL_LIST_PROJECTION)
    .lean();

  if (!goals.length) {
    return withApiTimezone({ overdue_sessions: [] }, timezone);
  }

  const goalIds = goals.map((goal) => goal._id);
  const sessionsByGoal = await loadSessionsByGoalId(goalIds, timezone);

  const overdueSessions = [];
  goals.forEach((goal) => {
    const sessions = sessionsByGoal.get(String(goal._id)) || [];
    const current = sessions.find((session) => session.is_current);
    if (current && current.session_state === "overdue") {
      const subject = String(goal.subject || "").trim().toLowerCase();
      overdueSessions.push({
        goal_id: String(goal._id),
        goal_title: goal.title,
        language: subjectToDisplay(subject),
        track_label: formatTrackLabel(goal.roadmap_key),
        session: current,
      });
    }
  });

  return withApiTimezone({ overdue_sessions: overdueSessions }, timezone);
};

module.exports = {
  GOAL_STATUSES,
  listUserRoadmapPlans,
  getUserRoadmapForGoalId,
  getPlanScheduleDatesForGoal,
  buildRoadmapMutationPayload,
  buildSessionDetailPayload,
  listOverdueSessionsForUser,
  serializeRoadmap,
  serializeRoadmapSummary,
  serializeRoadmapPlan,
  serializeSession,
  buildGoalsQuery,
  loadSessionsByGoalId,
};

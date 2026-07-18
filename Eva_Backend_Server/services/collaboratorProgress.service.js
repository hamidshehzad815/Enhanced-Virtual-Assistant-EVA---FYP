/**
 * Collaborator progress on shared learning roadmaps.
 *
 * When a collaborator accepts a learning-plan invite, the plan is *cloned* into
 * their own account (own LearningGoal + RoadmapTopics + Tasks). The clone keeps
 * a `source_goal_id` pointing back to the owner's goal. These helpers use that
 * link (with a best-effort fallback for older clones created before the link
 * existed) to answer, from the owner's side:
 *
 *   - Where has each collaborator reached?  (current session / percent)
 *   - Have they finished a given session?    (per-session status)
 *
 * Output per owner goal:
 *   {
 *     collaborators: [
 *       { user, status, progress: {
 *           completed_topics, total_topics, progress_percent,
 *           current_order, plan_status
 *         } | null }
 *     ],
 *     perSession: Map<order:number, Array<{ user_id, status }>>
 *   }
 */

const { LearningGoal, RoadmapTopic } = require("../models");
const {
  loadCollaboratorProfiles,
  serializeCollaborators,
} = require("../utils/collaboratorDetails");

const sameId = (a, b) => String(a) === String(b);

const isAccepted = (status) =>
  String(status || "").trim().toLowerCase() === "accepted";

const cloneMatchesGoal = (clone, goal) => {
  if (clone.source_goal_id && sameId(clone.source_goal_id, goal._id)) {
    return true;
  }
  // Fallback for clones created before source_goal_id existed: a collaborator
  // is very unlikely to hold two plans with the same track + title.
  return (
    !clone.source_goal_id
    && String(clone.roadmap_key || "") === String(goal.roadmap_key || "")
    && String(clone.title || "") === String(goal.title || "")
  );
};

/** completed / total / percent / where-they-reached, from a clone's topics. */
const summarizeTopics = (topics) => {
  const list = Array.isArray(topics) ? topics : [];
  const total = list.length;
  let completed = 0;
  let currentOrder = null;

  const ordered = [...list].sort(
    (a, b) => Number(a.order || 0) - Number(b.order || 0),
  );
  for (const topic of ordered) {
    const status = String(topic.status || "pending").toLowerCase();
    if (status === "completed") {
      completed += 1;
    }
    // First not-yet-finished session is where the collaborator currently is.
    if (currentOrder === null && status !== "completed" && status !== "skipped") {
      currentOrder = Number(topic.order || 0);
    }
  }

  const progressPercent = total > 0
    ? Math.min(100, Math.round((completed / total) * 100))
    : 0;

  return { total, completed, currentOrder, progressPercent };
};

/**
 * Compute collaborator details + progress for one or more owner goals.
 * @param {Array<{_id, roadmap_key, title, collaborators}>} goals
 * @returns {Promise<Map<string, {collaborators: Array, perSession: Map}>>}
 */
const buildCollaboratorProgressForGoals = async (goals) => {
  const result = new Map();
  const goalList = (Array.isArray(goals) ? goals : []).filter(
    (g) => Array.isArray(g?.collaborators) && g.collaborators.length > 0,
  );

  // Seed every requested goal (even collaborator-less ones) with an empty shape
  // so callers get a stable structure.
  for (const goal of Array.isArray(goals) ? goals : []) {
    result.set(String(goal._id), { collaborators: [], perSession: new Map() });
  }

  if (!goalList.length) {
    return result;
  }

  // 1. Batch-load collaborator public profiles once.
  const allCollaboratorIds = [];
  for (const goal of goalList) {
    for (const row of goal.collaborators) {
      if (row?.user_id) {
        allCollaboratorIds.push(String(row.user_id));
      }
    }
  }
  const profileMap = await loadCollaboratorProfiles(allCollaboratorIds);

  // 2. Find the mirrored (clone) plans for accepted collaborators.
  const acceptedCollaboratorIds = [
    ...new Set(
      goalList.flatMap((goal) =>
        goal.collaborators
          .filter((row) => isAccepted(row.status) && row.user_id)
          .map((row) => String(row.user_id)),
      ),
    ),
  ];

  const goalIds = goalList.map((goal) => goal._id);

  const cloneGoals = acceptedCollaboratorIds.length
    ? await LearningGoal.find({
        is_deleted: false,
        $or: [
          { source_goal_id: { $in: goalIds } },
          { user_id: { $in: acceptedCollaboratorIds } },
        ],
      })
        .select("user_id roadmap_key title status source_goal_id")
        .lean()
    : [];

  // 3. Load the clones' topics in one query, grouped by clone goal id.
  const cloneIds = cloneGoals.map((g) => g._id);
  const topicsByClone = new Map();
  if (cloneIds.length) {
    const topics = await RoadmapTopic.find({
      goal_id: { $in: cloneIds },
      is_deleted: false,
    })
      .select("goal_id order status")
      .lean();
    for (const topic of topics) {
      const key = String(topic.goal_id);
      if (!topicsByClone.has(key)) {
        topicsByClone.set(key, []);
      }
      topicsByClone.get(key).push(topic);
    }
  }

  // 4. Assemble per owner goal.
  for (const goal of goalList) {
    const perSession = new Map();

    const collaborators = serializeCollaborators(
      goal.collaborators,
      profileMap,
      (row) => {
        if (!isAccepted(row.status)) {
          return { progress: null };
        }

        const clone = cloneGoals.find(
          (c) => sameId(c.user_id, row.user_id) && cloneMatchesGoal(c, goal),
        );
        if (!clone) {
          return { progress: null };
        }

        const topics = topicsByClone.get(String(clone._id)) || [];
        const summary = summarizeTopics(topics);

        // Record this collaborator's status on each session (by order) so the
        // roadmap can show who has finished which session.
        for (const topic of topics) {
          const order = Number(topic.order || 0);
          if (!perSession.has(order)) {
            perSession.set(order, []);
          }
          perSession.get(order).push({
            user_id: String(row.user_id),
            status: String(topic.status || "pending").toLowerCase(),
          });
        }

        return {
          progress: {
            completed_topics: summary.completed,
            total_topics: summary.total,
            progress_percent: summary.progressPercent,
            current_order: summary.currentOrder,
            plan_status: String(clone.status || "active"),
          },
        };
      },
    );

    result.set(String(goal._id), { collaborators, perSession });
  }

  return result;
};

module.exports = {
  buildCollaboratorProgressForGoals,
  summarizeTopics,
};

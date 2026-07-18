/**
 * Collaborator progress on shared learning roadmaps.
 *
 * A shared plan lives as several independent documents: the owner's original
 * LearningGoal (whose `collaborators[]` holds the invitees) plus one *clone*
 * per accepted collaborator (their own goal + topics + tasks, linked back with
 * `source_goal_id`). "Group membership" is only recorded on the owner's doc.
 *
 * To give *every* member the same view — owner sees collaborators, and each
 * collaborator sees the owner + siblings — we resolve the **root** goal for the
 * goal being viewed, expand the whole participant group from it, and drop the
 * viewer themselves.
 *
 * Output per viewed goal:
 *   {
 *     collaborators: [
 *       { user, status, is_owner, progress: {
 *           completed_topics, total_topics, progress_percent,
 *           current_order, plan_status
 *         } | null }
 *     ],
 *     perSession: Map<order:number, Array<{ user_id, status }>>
 *   }
 */

const { LearningGoal, RoadmapTopic } = require("../models");
const { loadCollaboratorProfiles } = require("../utils/collaboratorDetails");

/** completed / total / percent / where-they-reached, from a goal's topics. */
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
 * Compute the participant group (excluding the viewer) + progress for one or
 * more goals the viewer owns (each may be an original plan or an accepted
 * clone).
 * @param {Array<{_id, user_id, source_goal_id, roadmap_key, title, status, collaborators}>} goals
 * @returns {Promise<Map<string, {collaborators: Array, perSession: Map}>>}
 */
const buildCollaboratorProgressForGoals = async (goals) => {
  const result = new Map();
  const goalList = Array.isArray(goals) ? goals : [];

  // Seed a stable empty shape for every requested goal.
  for (const goal of goalList) {
    result.set(String(goal._id), { collaborators: [], perSession: new Map() });
  }
  if (!goalList.length) {
    return result;
  }

  // 1. Resolve the root (owner's) goal for each viewed goal.
  //    Originals are their own root; clones point back via source_goal_id.
  const rootIdsToFetch = new Set();
  for (const goal of goalList) {
    if (goal.source_goal_id) {
      rootIdsToFetch.add(String(goal.source_goal_id));
    }
  }
  const fetchedRoots = rootIdsToFetch.size
    ? await LearningGoal.find({ _id: { $in: [...rootIdsToFetch] } })
        .select("user_id roadmap_key title status collaborators")
        .lean()
    : [];
  const rootById = new Map(fetchedRoots.map((r) => [String(r._id), r]));
  for (const goal of goalList) {
    if (!goal.source_goal_id) {
      rootById.set(String(goal._id), goal);
    }
  }

  const rootForViewedGoal = new Map();
  for (const goal of goalList) {
    const root = rootById.get(String(goal.source_goal_id || goal._id));
    if (root) {
      rootForViewedGoal.set(String(goal._id), root);
    }
  }

  // Only goals whose group actually has collaborators matter.
  const activeGoals = goalList.filter((goal) => {
    const root = rootForViewedGoal.get(String(goal._id));
    return root
      && Array.isArray(root.collaborators)
      && root.collaborators.length > 0;
  });
  if (!activeGoals.length) {
    return result;
  }

  // 2. Load public profiles for every participant (owner + collaborators).
  const participantIds = new Set();
  for (const goal of activeGoals) {
    const root = rootForViewedGoal.get(String(goal._id));
    participantIds.add(String(root.user_id));
    for (const row of root.collaborators) {
      if (row.user_id) {
        participantIds.add(String(row.user_id));
      }
    }
  }
  const profileMap = await loadCollaboratorProfiles([...participantIds]);

  // 3. Find every accepted collaborator's clone of the involved roots.
  const rootIds = [
    ...new Set(
      activeGoals.map((goal) =>
        String(rootForViewedGoal.get(String(goal._id))._id),
      ),
    ),
  ];
  const cloneGoals = await LearningGoal.find({
    is_deleted: false,
    source_goal_id: { $in: rootIds },
  })
    .select("user_id status source_goal_id")
    .lean();
  const cloneByRootAndUser = new Map();
  for (const clone of cloneGoals) {
    cloneByRootAndUser.set(
      `${String(clone.source_goal_id)}|${String(clone.user_id)}`,
      clone,
    );
  }

  // 4. Load topics for every "progress goal" (root goals + clones).
  const progressGoalIds = new Set(rootIds);
  for (const clone of cloneGoals) {
    progressGoalIds.add(String(clone._id));
  }
  const topicsByGoal = new Map();
  const topics = await RoadmapTopic.find({
    goal_id: { $in: [...progressGoalIds] },
    is_deleted: false,
  })
    .select("goal_id order status")
    .lean();
  for (const topic of topics) {
    const key = String(topic.goal_id);
    if (!topicsByGoal.has(key)) {
      topicsByGoal.set(key, []);
    }
    topicsByGoal.get(key).push(topic);
  }

  // 5. Assemble the group (minus the viewer) for each viewed goal.
  for (const goal of activeGoals) {
    const root = rootForViewedGoal.get(String(goal._id));
    const rootId = String(root._id);
    const viewerUserId = String(goal.user_id);
    const perSession = new Map();

    const participants = [
      { user_id: String(root.user_id), is_owner: true, status: "accepted" },
      ...root.collaborators.map((row) => ({
        user_id: String(row.user_id),
        is_owner: false,
        status: String(row.status || "pending").toLowerCase(),
      })),
    ];

    const collaborators = [];
    for (const participant of participants) {
      if (participant.user_id === viewerUserId) {
        continue; // never show the viewer to themselves
      }
      if (participant.status === "rejected") {
        continue;
      }
      const user = profileMap.get(participant.user_id);
      if (!user) {
        continue;
      }

      // Which goal reflects this participant's progress?
      let progressGoal = null;
      if (participant.is_owner) {
        progressGoal = root;
      } else if (participant.status === "accepted") {
        progressGoal = cloneByRootAndUser.get(`${rootId}|${participant.user_id}`) || null;
      }

      let progress = null;
      if (progressGoal) {
        const goalTopics = topicsByGoal.get(String(progressGoal._id)) || [];
        const summary = summarizeTopics(goalTopics);
        progress = {
          completed_topics: summary.completed,
          total_topics: summary.total,
          progress_percent: summary.progressPercent,
          current_order: summary.currentOrder,
          plan_status: String(progressGoal.status || "active"),
        };
        for (const topic of goalTopics) {
          const order = Number(topic.order || 0);
          if (!perSession.has(order)) {
            perSession.set(order, []);
          }
          perSession.get(order).push({
            user_id: participant.user_id,
            status: String(topic.status || "pending").toLowerCase(),
          });
        }
      }

      collaborators.push({
        user,
        status: participant.status,
        is_owner: participant.is_owner,
        progress,
      });
    }

    result.set(String(goal._id), { collaborators, perSession });
  }

  return result;
};

module.exports = {
  buildCollaboratorProgressForGoals,
  summarizeTopics,
};

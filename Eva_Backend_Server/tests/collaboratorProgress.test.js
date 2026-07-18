jest.mock("../models", () => ({
  User: { find: jest.fn() },
  LearningGoal: { find: jest.fn() },
  RoadmapTopic: { find: jest.fn() },
}));

const mongoose = require("mongoose");
const { User, LearningGoal, RoadmapTopic } = require("../models");
const {
  summarizeTopics,
  buildCollaboratorProgressForGoals,
} = require("../services/collaboratorProgress.service");

const selectLean = (data) => ({
  select: jest.fn().mockReturnValue({ lean: jest.fn().mockResolvedValue(data) }),
});

describe("summarizeTopics", () => {
  test("computes completed/total/percent and where the collaborator reached", () => {
    const summary = summarizeTopics([
      { order: 1, status: "completed" },
      { order: 2, status: "ongoing" },
      { order: 3, status: "pending" },
    ]);
    expect(summary).toEqual({
      total: 3,
      completed: 1,
      currentOrder: 2,
      progressPercent: 33,
    });
  });

  test("finished plan has no current order and 100 percent", () => {
    const summary = summarizeTopics([
      { order: 1, status: "completed" },
      { order: 2, status: "completed" },
    ]);
    expect(summary.currentOrder).toBeNull();
    expect(summary.progressPercent).toBe(100);
  });

  test("skipped sessions count toward reached but not completed", () => {
    const summary = summarizeTopics([
      { order: 1, status: "skipped" },
      { order: 2, status: "pending" },
    ]);
    expect(summary.completed).toBe(0);
    expect(summary.currentOrder).toBe(2);
  });
});

describe("buildCollaboratorProgressForGoals", () => {
  beforeEach(() => jest.clearAllMocks());

  test("returns empty shape for goals without collaborators (no DB calls)", async () => {
    const goalId = new mongoose.Types.ObjectId();
    const map = await buildCollaboratorProgressForGoals([
      { _id: goalId, roadmap_key: "python:basics", title: "Python", collaborators: [] },
    ]);
    expect(map.get(String(goalId))).toEqual({ collaborators: [], perSession: expect.any(Map) });
    expect(User.find).not.toHaveBeenCalled();
    expect(LearningGoal.find).not.toHaveBeenCalled();
  });

  test("populates accepted collaborator progress + per-session status", async () => {
    const goalId = new mongoose.Types.ObjectId();
    const collabId = new mongoose.Types.ObjectId();
    const cloneId = new mongoose.Types.ObjectId();

    const goal = {
      _id: goalId,
      roadmap_key: "python:basics",
      title: "Python",
      collaborators: [{ user_id: collabId, status: "accepted" }],
    };

    User.find.mockReturnValue(
      selectLean([
        { _id: collabId, name: "Bilal", username: "bilal", profile_picture: null },
      ]),
    );
    LearningGoal.find.mockReturnValue(
      selectLean([
        {
          _id: cloneId,
          user_id: collabId,
          roadmap_key: "python:basics",
          title: "Python",
          status: "active",
          source_goal_id: goalId,
        },
      ]),
    );
    RoadmapTopic.find.mockReturnValue(
      selectLean([
        { goal_id: cloneId, order: 1, status: "completed" },
        { goal_id: cloneId, order: 2, status: "pending" },
      ]),
    );

    const map = await buildCollaboratorProgressForGoals([goal]);
    const entry = map.get(String(goalId));

    expect(entry.collaborators).toHaveLength(1);
    expect(entry.collaborators[0].user.username).toBe("bilal");
    expect(entry.collaborators[0].status).toBe("accepted");
    expect(entry.collaborators[0].progress).toEqual({
      completed_topics: 1,
      total_topics: 2,
      progress_percent: 50,
      current_order: 2,
      plan_status: "active",
    });

    expect(entry.perSession.get(1)).toEqual([
      { user_id: String(collabId), status: "completed" },
    ]);
    expect(entry.perSession.get(2)).toEqual([
      { user_id: String(collabId), status: "pending" },
    ]);
  });

  test("collaborator viewing their clone sees the owner + progress", async () => {
    const ownerId = new mongoose.Types.ObjectId();
    const collabId = new mongoose.Types.ObjectId();
    const rootGoalId = new mongoose.Types.ObjectId();
    const cloneGoalId = new mongoose.Types.ObjectId();

    // The viewer is the collaborator, looking at their cloned plan.
    const cloneGoal = {
      _id: cloneGoalId,
      user_id: collabId,
      source_goal_id: rootGoalId,
      roadmap_key: "python:basics",
      title: "Python",
      collaborators: [],
    };

    // Root fetch, then clone fetch (two LearningGoal.find calls).
    LearningGoal.find
      .mockReturnValueOnce(
        selectLean([
          {
            _id: rootGoalId,
            user_id: ownerId,
            roadmap_key: "python:basics",
            title: "Python",
            status: "active",
            collaborators: [{ user_id: collabId, status: "accepted" }],
          },
        ]),
      )
      .mockReturnValueOnce(
        selectLean([
          { _id: cloneGoalId, user_id: collabId, status: "active", source_goal_id: rootGoalId },
        ]),
      );

    User.find.mockReturnValue(
      selectLean([
        { _id: ownerId, name: "Hamid", username: "hamid", profile_picture: null },
        { _id: collabId, name: "Bilal", username: "bilal", profile_picture: null },
      ]),
    );

    // Owner (root goal) topics — owner is ahead.
    RoadmapTopic.find.mockReturnValue(
      selectLean([
        { goal_id: rootGoalId, order: 1, status: "completed" },
        { goal_id: rootGoalId, order: 2, status: "completed" },
      ]),
    );

    const map = await buildCollaboratorProgressForGoals([cloneGoal]);
    const entry = map.get(String(cloneGoalId));

    expect(entry.collaborators).toHaveLength(1);
    const owner = entry.collaborators[0];
    expect(owner.is_owner).toBe(true);
    expect(owner.user.username).toBe("hamid");
    expect(owner.progress.progress_percent).toBe(100);
    expect(owner.progress.current_order).toBeNull();
    expect(entry.perSession.get(1)).toEqual([
      { user_id: String(ownerId), status: "completed" },
    ]);
  });

  test("reports a deleted collaborator plan as plan_status 'deleted'", async () => {
    const goalId = new mongoose.Types.ObjectId();
    const collabId = new mongoose.Types.ObjectId();
    const cloneId = new mongoose.Types.ObjectId();

    const goal = {
      _id: goalId,
      roadmap_key: "python:basics",
      title: "Python",
      collaborators: [{ user_id: collabId, status: "accepted" }],
    };

    User.find.mockReturnValue(
      selectLean([
        { _id: collabId, name: "Bilal", username: "bilal", profile_picture: null },
      ]),
    );
    // The collaborator deleted their copy: is_deleted true, topics gone.
    LearningGoal.find.mockReturnValue(
      selectLean([
        {
          _id: cloneId,
          user_id: collabId,
          source_goal_id: goalId,
          status: "cancelled",
          is_deleted: true,
          total_topics: 8,
          completed_topics: 3,
        },
      ]),
    );
    RoadmapTopic.find.mockReturnValue(selectLean([]));

    const map = await buildCollaboratorProgressForGoals([goal]);
    const entry = map.get(String(goalId));

    expect(entry.collaborators[0].status).toBe("accepted");
    expect(entry.collaborators[0].progress.plan_status).toBe("deleted");
    // Falls back to the goal's stored counts when topics are gone.
    expect(entry.collaborators[0].progress.completed_topics).toBe(3);
    expect(entry.collaborators[0].progress.total_topics).toBe(8);
  });

  test("reports a paused collaborator plan as plan_status 'paused'", async () => {
    const goalId = new mongoose.Types.ObjectId();
    const collabId = new mongoose.Types.ObjectId();
    const cloneId = new mongoose.Types.ObjectId();

    const goal = {
      _id: goalId,
      roadmap_key: "python:basics",
      title: "Python",
      collaborators: [{ user_id: collabId, status: "accepted" }],
    };

    User.find.mockReturnValue(
      selectLean([
        { _id: collabId, name: "Bilal", username: "bilal", profile_picture: null },
      ]),
    );
    LearningGoal.find.mockReturnValue(
      selectLean([
        {
          _id: cloneId,
          user_id: collabId,
          source_goal_id: goalId,
          status: "paused",
          is_deleted: false,
        },
      ]),
    );
    RoadmapTopic.find.mockReturnValue(
      selectLean([{ goal_id: cloneId, order: 1, status: "completed" }]),
    );

    const map = await buildCollaboratorProgressForGoals([goal]);
    const entry = map.get(String(goalId));

    expect(entry.collaborators[0].progress.plan_status).toBe("paused");
  });

  test("pending collaborator is shown with null progress", async () => {
    const goalId = new mongoose.Types.ObjectId();
    const collabId = new mongoose.Types.ObjectId();

    User.find.mockReturnValue(
      selectLean([
        { _id: collabId, name: "Sara", username: "sara", profile_picture: null },
      ]),
    );
    // No accepted collaborators -> no clone lookup results.
    LearningGoal.find.mockReturnValue(selectLean([]));
    RoadmapTopic.find.mockReturnValue(selectLean([]));

    const map = await buildCollaboratorProgressForGoals([
      {
        _id: goalId,
        roadmap_key: "python:basics",
        title: "Python",
        collaborators: [{ user_id: collabId, status: "pending" }],
      },
    ]);

    const entry = map.get(String(goalId));
    expect(entry.collaborators[0].status).toBe("pending");
    expect(entry.collaborators[0].progress).toBeNull();
  });
});

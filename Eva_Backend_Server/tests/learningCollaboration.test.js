jest.mock("../services/collaborationNotifications", () => ({
  notifyOwnerOfCollaborationResponse: jest.fn().mockResolvedValue({ dispatched: true }),
}));

jest.mock("../utils/userCalendarConflicts", () => ({
  findUserCalendarConflicts: jest.fn(),
  formatCollaboratorConflictMessage: jest.fn(),
  resolveUserTimezone: jest.fn().mockResolvedValue("UTC"),
}));

jest.mock("../models", () => ({
  LearningGoal: {
    findOne: jest.fn(),
    findOneAndUpdate: jest.fn(),
    create: jest.fn(),
    updateOne: jest.fn().mockResolvedValue({}),
  },
  RoadmapTopic: {
    find: jest.fn(),
    create: jest.fn(),
    updateOne: jest.fn(),
  },
  Task: {
    findOne: jest.fn(),
    create: jest.fn(),
  },
  User: {
    findById: jest.fn(),
  },
  Notification: {
    findOneAndUpdate: jest.fn().mockResolvedValue({}),
  },
}));

const mongoose = require("mongoose");
const { LearningGoal, RoadmapTopic, Notification, Task, User } = require("../models");
const { notifyOwnerOfCollaborationResponse } = require("../services/collaborationNotifications");
const { findUserCalendarConflicts } = require("../utils/userCalendarConflicts");
const { applyLearningCollaborationAction } = require("../services/learningCollaboration.service");

const sortLean = (value) => ({
  sort: jest.fn().mockReturnValue({ lean: jest.fn().mockResolvedValue(value) }),
});
const selLean = (value) => ({
  select: jest.fn().mockReturnValue({ lean: jest.fn().mockResolvedValue(value) }),
});
const justLean = (value) => ({ lean: jest.fn().mockResolvedValue(value) });

const OWNER_ID = new mongoose.Types.ObjectId();
const COLLAB_ID = new mongoose.Types.ObjectId();
const GOAL_ID = new mongoose.Types.ObjectId();

describe("learningCollaboration service", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    findUserCalendarConflicts.mockResolvedValue(null);
  });

  test("notifies owner when collaborator accepts invite", async () => {
    const pendingGoal = {
      _id: GOAL_ID,
      user_id: OWNER_ID,
      title: "Python roadmap",
      collaborators: [{ user_id: COLLAB_ID, status: "pending" }],
    };

    LearningGoal.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue(pendingGoal),
    });
    LearningGoal.findOneAndUpdate.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        ...pendingGoal,
        collaborators: [{ user_id: COLLAB_ID, status: "accepted" }],
      }),
    });

    const { RoadmapTopic } = require("../models");
    RoadmapTopic.find.mockReturnValue({
      sort: jest.fn().mockReturnValue({
        lean: jest.fn().mockResolvedValue([]),
      }),
    });
    LearningGoal.create.mockResolvedValue({ _id: new mongoose.Types.ObjectId() });
    User.findById.mockReturnValue({
      select: jest.fn().mockReturnValue({
        lean: jest.fn().mockResolvedValue({ name: "Collaborator" }),
      }),
    });

    const result = await applyLearningCollaborationAction({
      goalId: String(GOAL_ID),
      collaboratorUserId: String(COLLAB_ID),
      action: "accept",
    });

    expect(result.already_responded).toBe(false);
    expect(Notification.findOneAndUpdate).toHaveBeenCalled();
    expect(notifyOwnerOfCollaborationResponse).toHaveBeenCalledWith(
      expect.objectContaining({
        ownerId: OWNER_ID,
        collaboratorUserId: String(COLLAB_ID),
        action: "accept",
        referenceType: "learning_goal",
        itemTitle: "Python roadmap",
      }),
    );
  });

  test("reverts status to pending when cloning fails on accept", async () => {
    const pendingGoal = {
      _id: GOAL_ID,
      user_id: OWNER_ID,
      title: "Python roadmap",
      collaborators: [{ user_id: COLLAB_ID, status: "pending" }],
    };

    LearningGoal.findOne.mockReturnValue(justLean(pendingGoal));
    LearningGoal.findOneAndUpdate.mockReturnValue(
      justLean({
        ...pendingGoal,
        collaborators: [{ user_id: COLLAB_ID, status: "accepted" }],
      }),
    );

    // validateCollaboratorCanAcceptPlan finds a conflicting session.
    RoadmapTopic.find.mockReturnValue(sortLean([{ task_id: new mongoose.Types.ObjectId() }]));
    User.findById.mockReturnValue(selLean({ name: "Collaborator" }));
    Task.findOne.mockReturnValue(justLean({ due_datetime: new Date(), duration: 60 }));
    findUserCalendarConflicts.mockResolvedValue({ conflict: true });

    await expect(
      applyLearningCollaborationAction({
        goalId: String(GOAL_ID),
        collaboratorUserId: String(COLLAB_ID),
        action: "accept",
      }),
    ).rejects.toBeDefined();

    // Rolled back to pending so the invite stays actionable.
    expect(LearningGoal.updateOne).toHaveBeenCalledWith(
      expect.objectContaining({ _id: GOAL_ID }),
      expect.objectContaining({
        $set: expect.objectContaining({ "collaborators.$.status": "pending" }),
      }),
    );
    expect(notifyOwnerOfCollaborationResponse).not.toHaveBeenCalled();
  });

  test("self-heals a stuck 'accepted' collaborator that has no clone", async () => {
    const acceptedGoal = {
      _id: GOAL_ID,
      user_id: OWNER_ID,
      title: "Python roadmap",
      collaborators: [{ user_id: COLLAB_ID, status: "accepted" }],
    };

    // 1st findOne: load the goal. 2nd findOne: look for an existing clone (none).
    LearningGoal.findOne
      .mockReturnValueOnce(justLean(acceptedGoal))
      .mockReturnValueOnce(justLean(null));
    RoadmapTopic.find.mockReturnValue(sortLean([]));
    User.findById.mockReturnValue(selLean({ name: "Collaborator" }));
    LearningGoal.create.mockResolvedValue({ _id: new mongoose.Types.ObjectId() });

    const result = await applyLearningCollaborationAction({
      goalId: String(GOAL_ID),
      collaboratorUserId: String(COLLAB_ID),
      action: "accept",
    });

    expect(result.already_responded).toBe(false);
    expect(result.collaborator_goal_id).toBeDefined();
    expect(LearningGoal.create).toHaveBeenCalled(); // clone rebuilt
    expect(LearningGoal.findOneAndUpdate).not.toHaveBeenCalled(); // status stays accepted
  });

  test("does not notify owner when invite was already handled", async () => {
    LearningGoal.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: GOAL_ID,
        user_id: OWNER_ID,
        title: "Python roadmap",
        collaborators: [{ user_id: COLLAB_ID, status: "accepted" }],
      }),
    });

    const result = await applyLearningCollaborationAction({
      goalId: String(GOAL_ID),
      collaboratorUserId: String(COLLAB_ID),
      action: "reject",
    });

    expect(result.already_responded).toBe(true);
    expect(notifyOwnerOfCollaborationResponse).not.toHaveBeenCalled();
    expect(LearningGoal.findOneAndUpdate).not.toHaveBeenCalled();
  });
});

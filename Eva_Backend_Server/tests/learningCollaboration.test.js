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
const { LearningGoal, Notification, User } = require("../models");
const { notifyOwnerOfCollaborationResponse } = require("../services/collaborationNotifications");
const { findUserCalendarConflicts } = require("../utils/userCalendarConflicts");
const { applyLearningCollaborationAction } = require("../services/learningCollaboration.service");

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

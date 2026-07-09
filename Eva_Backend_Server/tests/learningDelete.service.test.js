process.env.NODE_ENV = "test";

const mongoose = require("mongoose");

jest.mock("../models", () => ({
  LearningGoal: {
    findOne: jest.fn(),
    updateOne: jest.fn(),
  },
  RoadmapTopic: {
    updateMany: jest.fn(),
  },
  Task: {
    updateMany: jest.fn(),
  },
  User: {
    findById: jest.fn(),
  },
  ActivityLog: {
    create: jest.fn(),
  },
  UserSetting: {
    findOne: jest.fn(),
  },
}));

const {
  LearningGoal,
  RoadmapTopic,
  Task,
  User,
  ActivityLog,
  UserSetting,
} = require("../models");
const {
  softDeleteLearningGoalById,
  buildCollaboratorNotifications,
} = require("../services/learningDelete.service");

const OWNER_ID = "507f1f77bcf86cd799439011";
const GOAL_ID = "507f1f77bcf86cd799439099";
const COLLAB_ID = "507f1f77bcf86cd799439088";

describe("learningDelete.service", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("buildCollaboratorNotifications for accepted collaborators only", () => {
    const payloads = buildCollaboratorNotifications(
      {
        _id: GOAL_ID,
        subject: "python",
        roadmap_key: "basics",
        collaborators: [
          { user_id: COLLAB_ID, status: "accepted" },
          { user_id: OWNER_ID, status: "accepted" },
          { user_id: new mongoose.Types.ObjectId(), status: "pending" },
        ],
      },
      OWNER_ID,
      "Ali",
    );

    expect(payloads).toHaveLength(1);
    expect(payloads[0].type).toBe("learning_goal_deleted");
    expect(payloads[0].user_id).toBe(COLLAB_ID);
    expect(payloads[0].message).toContain("Ali");
    expect(payloads[0].message).toContain("unaffected");
  });

  test("softDeleteLearningGoalById soft-deletes goal topics and pending tasks", async () => {
    LearningGoal.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: GOAL_ID,
        user_id: OWNER_ID,
        subject: "python",
        roadmap_key: "basics",
        title: "Python basics",
        collaborators: [],
        is_deleted: false,
      }),
    });
    LearningGoal.updateOne.mockResolvedValue({ modifiedCount: 1 });
    RoadmapTopic.updateMany.mockResolvedValue({ modifiedCount: 2 });
    Task.updateMany.mockResolvedValue({ modifiedCount: 3 });
    ActivityLog.create.mockResolvedValue({ _id: new mongoose.Types.ObjectId() });
    UserSetting.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({ behavioral_analytics_enabled: true }),
    });
    User.findById.mockReturnValue({
      select: jest.fn().mockReturnValue({
        lean: jest.fn().mockResolvedValue({ name: "Ali" }),
      }),
    });

    const result = await softDeleteLearningGoalById(GOAL_ID, OWNER_ID);

    expect(LearningGoal.updateOne).toHaveBeenCalledWith(
      expect.objectContaining({ _id: expect.any(mongoose.Types.ObjectId) }),
      expect.objectContaining({
        $set: expect.objectContaining({
          is_deleted: true,
          status: "cancelled",
        }),
      }),
    );
    expect(RoadmapTopic.updateMany).toHaveBeenCalledWith(
      expect.objectContaining({
        status: { $in: ["pending", "ongoing"] },
      }),
      expect.any(Object),
    );
    expect(Task.updateMany).toHaveBeenCalledWith(
      expect.objectContaining({
        status: { $in: ["pending", "ongoing"] },
      }),
      expect.any(Object),
    );
    expect(ActivityLog.create).toHaveBeenCalledWith(
      expect.objectContaining({ action_type: "goal_deleted" }),
    );
    expect(result.goal.is_deleted).toBe(true);
    expect(result.goal.status).toBe("cancelled");
    expect(result.notifications).toEqual([]);
  });
});

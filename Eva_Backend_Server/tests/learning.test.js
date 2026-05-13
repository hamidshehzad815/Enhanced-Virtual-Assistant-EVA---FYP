process.env.NODE_ENV = "test";
process.env.JWT_ACCESS_SECRET = process.env.JWT_ACCESS_SECRET || "test-access-secret";

const jwt = require("jsonwebtoken");
const request = require("supertest");

jest.mock("../config/db", () => ({
  connectDB: jest.fn().mockResolvedValue(true),
}));

jest.mock("../jobs/reminder.job", () => ({
  startReminderJob: jest.fn(),
  stopReminderJob: jest.fn(),
}));

jest.mock("../config/logger", () => ({
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
  debug: jest.fn(),
  http: jest.fn(),
  add: jest.fn(),
  stream: { write: jest.fn() },
}));

jest.mock("../models", () => ({
  User: { findById: jest.fn() },
  LearningGoal: {
    find: jest.fn(),
    findOne: jest.fn(),
    findOneAndUpdate: jest.fn(),
    updateOne: jest.fn(),
  },
  RoadmapTopic: {
    find: jest.fn(),
    findOne: jest.fn(),
    findOneAndUpdate: jest.fn(),
  },
  Task: {
    updateMany: jest.fn(),
    updateOne: jest.fn(),
  },
  UserSetting: {},
  ChatSession: {},
  ConversationHistory: {},
  Notification: {},
  ActivityLog: {},
  Integration: {},
  Friend: {},
}));

const app = require("../app");
const { User, LearningGoal, RoadmapTopic, Task } = require("../models");

const USER_ID = "507f1f77bcf86cd799439011";
const GOAL_ID = "507f1f77bcf86cd799439099";
const TOPIC_ID = "507f1f77bcf86cd799439088";
const TASK_ID = "507f1f77bcf86cd799439077";

const makeToken = () =>
  jwt.sign({ userId: USER_ID }, process.env.JWT_ACCESS_SECRET, {
    expiresIn: "15m",
  });

describe("Learning API", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    LearningGoal.findOne.mockReset();
    LearningGoal.find.mockReset();
    LearningGoal.findOneAndUpdate.mockReset();
    RoadmapTopic.find.mockReset();
    RoadmapTopic.findOne.mockReset();
    RoadmapTopic.findOneAndUpdate.mockReset();
    LearningGoal.updateOne.mockReset();
    Task.updateMany.mockReset();
    Task.updateOne.mockReset();
    User.findById.mockResolvedValue({
      _id: USER_ID,
      is_active: true,
    });
  });

  test("GET /api/learning without token → 401", async () => {
    const res = await request(app).get("/api/learning");
    expect(res.status).toBe(401);
  });

  test("GET /api/learning → active and paused goals", async () => {
    const sort = jest.fn().mockReturnValue({ lean: jest.fn().mockResolvedValue([]) });
    LearningGoal.find.mockReturnValue({ sort });

    const res = await request(app)
      .get("/api/learning")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(res.status).toBe(200);
    expect(res.body.status).toBe("success");
    expect(Array.isArray(res.body.data.goals)).toBe(true);
    expect(LearningGoal.find).toHaveBeenCalledWith({
      user_id: USER_ID,
      is_deleted: false,
      status: { $in: ["active", "paused"] },
    });
  });

  test("GET /api/learning/:id → goal with progress", async () => {
    LearningGoal.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: GOAL_ID,
        user_id: USER_ID,
        title: "Learn Python",
        total_topics: 8,
        completed_topics: 2,
        status: "active",
        is_deleted: false,
      }),
    });

    const res = await request(app)
      .get(`/api/learning/${GOAL_ID}`)
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(res.status).toBe(200);
    expect(res.body.data.goal.progress_percent).toBe(25);
  });

  test("GET /api/learning/:id/topics → ordered topics", async () => {
    LearningGoal.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: GOAL_ID,
        user_id: USER_ID,
        is_deleted: false,
      }),
    });

    const topics = [
      { order: 1, title: "A", resources: [] },
      { order: 2, title: "B", resources: [{ title: "v", url: "https://youtu.be/x" }] },
    ];
    RoadmapTopic.find.mockReturnValue({
      sort: jest.fn().mockReturnValue({ lean: jest.fn().mockResolvedValue(topics) }),
    });

    const res = await request(app)
      .get(`/api/learning/${GOAL_ID}/topics`)
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(res.status).toBe(200);
    expect(res.body.data.topics).toHaveLength(2);
    expect(RoadmapTopic.find).toHaveBeenCalled();
  });

  test("PATCH /api/learning/:id/status pause → paused", async () => {
    LearningGoal.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: GOAL_ID,
        user_id: USER_ID,
        status: "active",
        is_deleted: false,
      }),
    });

    LearningGoal.findOneAndUpdate.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: GOAL_ID,
        status: "paused",
        paused_at: new Date(),
      }),
    });

    const res = await request(app)
      .patch(`/api/learning/${GOAL_ID}/status`)
      .set("Authorization", `Bearer ${makeToken()}`)
      .send({ status: "paused" });

    expect(res.status).toBe(200);
    expect(res.body.data.goal.status).toBe("paused");
  });

  test("PATCH /api/learning/:id/status resume → active", async () => {
    LearningGoal.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: GOAL_ID,
        user_id: USER_ID,
        status: "paused",
        is_deleted: false,
      }),
    });

    LearningGoal.findOneAndUpdate.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: GOAL_ID,
        status: "active",
        paused_at: null,
      }),
    });

    const res = await request(app)
      .patch(`/api/learning/${GOAL_ID}/status`)
      .set("Authorization", `Bearer ${makeToken()}`)
      .send({ status: "active" });

    expect(res.status).toBe(200);
    expect(res.body.data.goal.status).toBe("active");
  });

  test("PATCH /api/learning/:id/status cancel → soft-deletes tasks", async () => {
    LearningGoal.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: GOAL_ID,
        user_id: USER_ID,
        status: "active",
        is_deleted: false,
      }),
    });

    LearningGoal.findOneAndUpdate.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: GOAL_ID,
        status: "cancelled",
      }),
    });

    Task.updateMany.mockResolvedValue({ modifiedCount: 3 });

    const res = await request(app)
      .patch(`/api/learning/${GOAL_ID}/status`)
      .set("Authorization", `Bearer ${makeToken()}`)
      .send({ status: "cancelled" });

    expect(res.status).toBe(200);
    expect(Task.updateMany).toHaveBeenCalled();
  });

  test("POST /api/learning/:id/topics/:topicId/complete → marks topic and increments goal", async () => {
    LearningGoal.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: GOAL_ID,
        user_id: USER_ID,
        status: "active",
        is_deleted: false,
        started_at: new Date("2026-01-01T10:00:00Z"),
        total_topics: 8,
        completed_topics: 2,
      }),
    });

    RoadmapTopic.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: TOPIC_ID,
        goal_id: GOAL_ID,
        status: "pending",
        task_id: TASK_ID,
        title: "Loops",
      }),
    });

    RoadmapTopic.findOneAndUpdate.mockResolvedValue({});
    LearningGoal.updateOne.mockResolvedValue({});
    LearningGoal.findOneAndUpdate.mockReturnValueOnce({
      lean: jest.fn().mockResolvedValue({
        _id: GOAL_ID,
        user_id: USER_ID,
        total_topics: 8,
        completed_topics: 3,
        status: "active",
        started_at: new Date("2026-01-01T10:00:00Z"),
      }),
    });
    Task.updateOne.mockResolvedValue({ modifiedCount: 1 });

    const res = await request(app)
      .post(`/api/learning/${GOAL_ID}/topics/${TOPIC_ID}/complete`)
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(res.status).toBe(200);
    expect(res.body.data.topic.status).toBe("completed");
    expect(res.body.data.goal.completed_topics).toBe(3);
    expect(Task.updateOne).toHaveBeenCalled();
  });

  test("PATCH status completed → 400", async () => {
    LearningGoal.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: GOAL_ID,
        user_id: USER_ID,
        status: "active",
        is_deleted: false,
      }),
    });

    const res = await request(app)
      .patch(`/api/learning/${GOAL_ID}/status`)
      .set("Authorization", `Bearer ${makeToken()}`)
      .send({ status: "completed" });

    expect(res.status).toBe(400);
  });
});

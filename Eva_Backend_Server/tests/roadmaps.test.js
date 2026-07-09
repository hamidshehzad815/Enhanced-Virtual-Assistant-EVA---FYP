process.env.NODE_ENV = "test";
process.env.JWT_ACCESS_SECRET = process.env.JWT_ACCESS_SECRET || "test-access-secret";

const jwt = require("jsonwebtoken");
const request = require("supertest");
const mongoose = require("mongoose");

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
  User: {
    findById: jest.fn(),
  },
  LearningGoal: {
    distinct: jest.fn(),
    find: jest.fn(),
    findOne: jest.fn(),
  },
  RoadmapTopic: {
    find: jest.fn(),
    aggregate: jest.fn(),
  },
  UserSetting: {
    findOne: jest.fn(),
  },
}));

const app = require("../app");
const { User, LearningGoal, RoadmapTopic, UserSetting } = require("../models");

const USER_ID = "507f1f77bcf86cd799439011";

const makeToken = () =>
  jwt.sign({ userId: USER_ID }, process.env.JWT_ACCESS_SECRET, {
    expiresIn: "15m",
  });

const pythonGoal = {
  _id: new mongoose.Types.ObjectId(),
  user_id: USER_ID,
  title: "Python basics",
  subject: "python",
  roadmap_key: "basics",
  status: "active",
  learning_schedule_id: "sched-evening",
  start_date: new Date("2026-06-01"),
  end_date: new Date("2026-07-01"),
  duration_days: 30,
  total_topics: 8,
  completed_topics: 2,
  is_deleted: false,
  created_at: new Date(),
  updated_at: new Date(),
};

const completedPythonGoal = {
  ...pythonGoal,
  _id: new mongoose.Types.ObjectId(),
  status: "completed",
  title: "Python basics (done)",
  updated_at: new Date("2026-01-01"),
};

describe("User roadmaps API", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    User.findById.mockResolvedValue({
      _id: USER_ID,
      is_active: true,
      timezone: "UTC",
      toPublicProfile: jest.fn(),
    });
  });

  test("GET /api/roadmaps/plans returns all plans without sessions", async () => {
    const goalChain = {
      select: jest.fn().mockReturnThis(),
      sort: jest.fn().mockReturnThis(),
      lean: jest.fn().mockResolvedValue([pythonGoal, completedPythonGoal]),
    };
    LearningGoal.find.mockReturnValue(goalChain);
    RoadmapTopic.aggregate.mockResolvedValue([
      {
        _id: { goal_id: pythonGoal._id, status: "completed" },
        count: 2,
      },
      {
        _id: { goal_id: pythonGoal._id, status: "pending" },
        count: 6,
      },
    ]);

    const response = await request(app)
      .get("/api/roadmaps/plans")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.data.roadmaps).toHaveLength(2);
    expect(response.body.data.roadmaps[0]).toEqual(
      expect.objectContaining({
        title: "Python basics",
        language_key: "python",
        status: "active",
        session_count: 8,
      }),
    );
    expect(response.body.data.roadmaps[0].sessions).toBeUndefined();
    expect(response.body.data.roadmaps[0].sessions_summary).toEqual(
      expect.objectContaining({
        completed: 2,
        pending: 6,
      }),
    );
    expect(RoadmapTopic.find).not.toHaveBeenCalled();
  });

  test("GET /api/roadmaps/plans?status=active filters plans", async () => {
    const goalChain = {
      select: jest.fn().mockReturnThis(),
      sort: jest.fn().mockReturnThis(),
      lean: jest.fn().mockResolvedValue([pythonGoal]),
    };
    LearningGoal.find.mockReturnValue(goalChain);
    RoadmapTopic.aggregate.mockResolvedValue([]);

    const response = await request(app)
      .get("/api/roadmaps/plans?status=active")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(LearningGoal.find).toHaveBeenCalledWith(
      expect.objectContaining({
        user_id: USER_ID,
        is_deleted: false,
        status: { $in: ["active"] },
      }),
    );
  });

  test("GET /api/roadmaps/:goalId invalid id -> 400", async () => {
    const response = await request(app)
      .get("/api/roadmaps/not-a-valid-id")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(400);
    expect(response.body.message).toMatch(/invalid goal id/i);
    expect(LearningGoal.findOne).not.toHaveBeenCalled();
  });

  test("GET /api/roadmaps/:goalId returns roadmap with sessions", async () => {
    const goalId = String(pythonGoal._id);

    LearningGoal.findOne.mockReturnValue({
      select: jest.fn().mockReturnThis(),
      lean: jest.fn().mockResolvedValue(pythonGoal),
    });

    const topicChain = {
      select: jest.fn().mockReturnThis(),
      sort: jest.fn().mockReturnThis(),
      lean: jest.fn().mockResolvedValue([
        {
          _id: new mongoose.Types.ObjectId(),
          goal_id: pythonGoal._id,
          order: 1,
          title: "Session 1",
          status: "completed",
          scheduled_date: new Date("2026-06-02T18:00:00Z"),
          estimated_duration: 90,
          completed_at: new Date("2026-06-03T18:00:00Z"),
          resources: [{ title: "Intro", url: "https://youtu.be/x" }],
        },
        {
          _id: new mongoose.Types.ObjectId(),
          goal_id: pythonGoal._id,
          order: 2,
          title: "Session 2",
          status: "pending",
          scheduled_date: new Date("2026-06-05T18:00:00Z"),
          estimated_duration: 90,
        },
      ]),
    };
    RoadmapTopic.find.mockReturnValue(topicChain);

    const response = await request(app)
      .get(`/api/roadmaps/${goalId}`)
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(LearningGoal.findOne).toHaveBeenCalledWith(
      expect.objectContaining({
        _id: goalId,
        user_id: USER_ID,
        is_deleted: false,
      }),
    );
    expect(response.body.data.language).toEqual({ key: "python", label: "Python" });
    const roadmap = response.body.data.roadmap;
    expect(roadmap).toEqual(
      expect.objectContaining({
        id: goalId,
        title: "Python basics",
        language: "Python",
        language_key: "python",
        track_label: "Basics",
        status: "active",
        session_count: 2,
      }),
    );
    expect(roadmap.sessions).toHaveLength(2);
    expect(roadmap.sessions[1].is_current).toBe(true);
  });

  test("GET /api/roadmaps/:goalId/schedule-dates returns learning weekdays only", async () => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date("2026-06-27T10:00:00.000Z"));

    const goalId = String(pythonGoal._id);

    LearningGoal.findOne.mockReturnValue({
      select: jest.fn().mockReturnThis(),
      lean: jest.fn().mockResolvedValue(pythonGoal),
    });

    UserSetting.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        preferred_learning_schedules: [
          {
            id: "sched-evening",
            label: "Evening",
            slots: [
              { day: 0, time: "18:00", duration_minutes: 90 },
              { day: 4, time: "18:00", duration_minutes: 90 },
            ],
          },
        ],
      }),
    });

    const response = await request(app)
      .get(`/api/roadmaps/${goalId}/schedule-dates`)
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.data.weekdays).toHaveLength(2);
    expect(response.body.data.dates.length).toBeGreaterThan(0);
    response.body.data.dates.forEach((row) => {
      expect([0, 4]).toContain(row.day);
    });

    jest.useRealTimers();
  });

  test("GET /api/roadmaps/:goalId/schedule-dates rejects paused plan", async () => {
    const goalId = String(pythonGoal._id);
    const pausedGoal = { ...pythonGoal, status: "paused" };

    LearningGoal.findOne.mockReturnValue({
      select: jest.fn().mockReturnThis(),
      lean: jest.fn().mockResolvedValue(pausedGoal),
    });

    const response = await request(app)
      .get(`/api/roadmaps/${goalId}/schedule-dates`)
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(400);
    expect(response.body.message).toMatch(/active learning plans/i);
  });

  test("GET /api/roadmaps/:goalId not found -> 404", async () => {
    const goalId = String(pythonGoal._id);

    LearningGoal.findOne.mockReturnValue({
      select: jest.fn().mockReturnThis(),
      lean: jest.fn().mockResolvedValue(null),
    });

    const response = await request(app)
      .get(`/api/roadmaps/${goalId}`)
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(404);
    expect(response.body.message).toMatch(/learning goal not found/i);
  });

  test("roadmaps routes require auth -> 401", async () => {
    const goalId = String(pythonGoal._id);
    const [plans, roadmap] = await Promise.all([
      request(app).get("/api/roadmaps/plans"),
      request(app).get(`/api/roadmaps/${goalId}`),
    ]);

    expect(plans.status).toBe(401);
    expect(roadmap.status).toBe(401);
  });
});

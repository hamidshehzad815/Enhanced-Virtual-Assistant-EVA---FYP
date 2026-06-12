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
  },
  RoadmapTopic: {
    find: jest.fn(),
  },
}));

const app = require("../app");
const { User, LearningGoal, RoadmapTopic } = require("../models");

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

  test("GET /api/roadmaps/languages returns only user's languages", async () => {
    LearningGoal.distinct.mockResolvedValue(["python", "javascript"]);

    const response = await request(app)
      .get("/api/roadmaps/languages")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.data.languages).toEqual([
      { key: "javascript", label: "JavaScript" },
      { key: "python", label: "Python" },
    ]);
  });

  test("GET /api/roadmaps without language -> 400", async () => {
    const response = await request(app)
      .get("/api/roadmaps")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(400);
    expect(response.body.message).toMatch(/language query parameter is required/i);
    expect(LearningGoal.find).not.toHaveBeenCalled();
  });

  test("GET /api/roadmaps?language=python returns single roadmap with sessions", async () => {
    const goalChain = {
      select: jest.fn().mockReturnThis(),
      sort: jest.fn().mockReturnThis(),
      lean: jest.fn().mockResolvedValue([pythonGoal]),
    };
    LearningGoal.find.mockReturnValue(goalChain);

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
      .get("/api/roadmaps?language=python")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.data.language).toEqual({ key: "python", label: "Python" });
    const roadmap = response.body.data.roadmap;
    expect(roadmap).toEqual(
      expect.objectContaining({
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

  test("prefers active roadmap over completed for same language", async () => {
    const activeGoal = { ...pythonGoal, updated_at: new Date("2026-02-01") };
    const goalChain = {
      select: jest.fn().mockReturnThis(),
      sort: jest.fn().mockReturnThis(),
      lean: jest.fn().mockResolvedValue([completedPythonGoal, activeGoal]),
    };
    LearningGoal.find.mockReturnValue(goalChain);
    RoadmapTopic.find.mockReturnValue({
      select: jest.fn().mockReturnThis(),
      sort: jest.fn().mockReturnThis(),
      lean: jest.fn().mockResolvedValue([]),
    });

    const response = await request(app)
      .get("/api/roadmaps?language=python")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.data.roadmap.title).toBe("Python basics");
    expect(response.body.data.roadmap.status).toBe("active");
  });

  test("returns completed roadmap when only completed exists", async () => {
    const goalChain = {
      select: jest.fn().mockReturnThis(),
      sort: jest.fn().mockReturnThis(),
      lean: jest.fn().mockResolvedValue([completedPythonGoal]),
    };
    LearningGoal.find.mockReturnValue(goalChain);
    RoadmapTopic.find.mockReturnValue({
      select: jest.fn().mockReturnThis(),
      sort: jest.fn().mockReturnThis(),
      lean: jest.fn().mockResolvedValue([]),
    });

    const response = await request(app)
      .get("/api/roadmaps?language=python")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.data.roadmap.status).toBe("completed");
  });

  test("GET /api/roadmaps?status=invalid -> 400", async () => {
    const response = await request(app)
      .get("/api/roadmaps?language=python&status=running")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(400);
    expect(LearningGoal.find).not.toHaveBeenCalled();
  });

  test("roadmaps routes require auth -> 401", async () => {
    const [languages, list] = await Promise.all([
      request(app).get("/api/roadmaps/languages"),
      request(app).get("/api/roadmaps?language=python"),
    ]);

    expect(languages.status).toBe(401);
    expect(list.status).toBe(401);
  });
});

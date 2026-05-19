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
  User: {
    findById: jest.fn(),
  },
  UserSetting: {
    findOne: jest.fn(),
    createDefaultSettings: jest.fn(),
  },
  ChatSession: {},
  ConversationHistory: {},
  Notification: {},
  Task: {
    find: jest.fn(),
  },
  ActivityLog: {},
  Integration: {},
  Friend: {},
  LearningGoal: {
    find: jest.fn(),
  },
  RoadmapTopic: {
    find: jest.fn(),
  },
}));

const app = require("../app");
const { User, Task, LearningGoal, RoadmapTopic } = require("../models");

const USER_ID = "507f1f77bcf86cd799439011";

const makeToken = () =>
  jwt.sign({ userId: USER_ID }, process.env.JWT_ACCESS_SECRET, {
    expiresIn: "15m",
  });

const mockFindResult = (rows) => ({
  sort: jest.fn().mockReturnValue({
    lean: jest.fn().mockResolvedValue(rows),
  }),
});

describe("Dashboard API", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    User.findById.mockResolvedValue({
      _id: USER_ID,
      is_active: true,
      timezone: "Asia/Karachi",
    });
  });

  test("GET /api/dashboard returns all 4 dashboard sections", async () => {
    const now = new Date();
    const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
    const oneHourAhead = new Date(now.getTime() + 60 * 60 * 1000);
    const twoHoursAhead = new Date(now.getTime() + 2 * 60 * 60 * 1000);

    Task.find.mockReturnValue(
      mockFindResult([
        {
          _id: "t1",
          title: "Completed task",
          status: "complete",
          priority: "medium",
          due_datetime: oneHourAgo,
          learning_plan_id: null,
        },
        {
          _id: "t2",
          title: "Upcoming task",
          status: "pending",
          priority: "high",
          due_datetime: oneHourAhead,
          learning_plan_id: null,
        },
      ]),
    );

    LearningGoal.find.mockReturnValue(
      mockFindResult([
        {
          _id: "g1",
          title: "Python roadmap",
          roadmap_key: "functions",
          status: "active",
          total_topics: 10,
          completed_topics: 3,
        },
      ]),
    );

    RoadmapTopic.find.mockReturnValue(
      mockFindResult([
        {
          _id: "rt1",
          goal_id: "g1",
          title: "Functions intro",
          status: "pending",
          scheduled_date: twoHoursAhead,
        },
      ]),
    );

    const response = await request(app)
      .get("/api/dashboard")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");

    const data = response.body.data;
    expect(data).toBeTruthy();
    expect(data.up_next).toBeTruthy();
    expect(data.up_next.title).toBe("Upcoming task");

    expect(data.daily_progress.total_tasks).toBe(2);
    expect(data.daily_progress.completed_tasks).toBe(1);
    expect(data.daily_progress.completion_percentage).toBe(50);

    expect(Array.isArray(data.learning)).toBe(true);
    expect(data.learning).toHaveLength(1);
    expect(data.learning[0].title).toBe("Python roadmap");
    expect(data.learning[0].next_topic.title).toBe("Functions intro");

    expect(Array.isArray(data.today_schedule)).toBe(true);
    expect(data.today_schedule).toHaveLength(2);
  });

  test("GET /api/dashboard handles empty state", async () => {
    Task.find.mockReturnValue(mockFindResult([]));
    LearningGoal.find.mockReturnValue(mockFindResult([]));
    RoadmapTopic.find.mockReturnValue(mockFindResult([]));

    const response = await request(app)
      .get("/api/dashboard")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");
    expect(response.body.data.up_next).toBeNull();
    expect(response.body.data.daily_progress.total_tasks).toBe(0);
    expect(response.body.data.daily_progress.completed_tasks).toBe(0);
    expect(response.body.data.daily_progress.completion_percentage).toBe(0);
    expect(response.body.data.learning).toEqual([]);
    expect(response.body.data.today_schedule).toEqual([]);
  });
});


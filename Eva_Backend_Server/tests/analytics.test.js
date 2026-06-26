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
  stream: {
    write: jest.fn(),
  },
}));

jest.mock("../services/ai.service", () => ({
  callAIServer: jest.fn(),
  callAIAnalytics: jest.fn(),
}));

jest.mock("../models", () => ({
  User: {
    findById: jest.fn(),
  },
  UserSetting: {
    findOne: jest.fn(),
    createDefaultSettings: jest.fn(),
  },
  ChatSession: {
    create: jest.fn(),
    findOne: jest.fn(),
  },
  ConversationHistory: {},
  Notification: {
    create: jest.fn(),
  },
  Task: {
    find: jest.fn(),
    countDocuments: jest.fn(),
    aggregate: jest.fn(),
    findOne: jest.fn(),
    findOneAndUpdate: jest.fn(),
  },
  LearningGoal: {
    find: jest.fn(),
  },
  RoadmapTopic: {
    find: jest.fn(),
  },
  ActivityLog: {
    aggregate: jest.fn(),
    countDocuments: jest.fn(),
    find: jest.fn(),
  },
  Integration: {},
}));

const app = require("../app");
const { callAIAnalytics } = require("../services/ai.service");
const { ActivityLog, Task } = require("../models");

const USER_ID = "507f1f77bcf86cd799439011";

const makeQueryChain = (result = []) => {
  const chain = {
    select: jest.fn(),
    sort: jest.fn(),
    limit: jest.fn(),
    lean: jest.fn().mockResolvedValue(result),
  };
  chain.select.mockReturnValue(chain);
  chain.sort.mockReturnValue(chain);
  chain.limit.mockReturnValue(chain);
  return chain;
};

const makeToken = () =>
  jwt.sign({ userId: USER_ID }, process.env.JWT_ACCESS_SECRET, {
    expiresIn: "15m",
  });

describe("Analytics API", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    require("../models").User.findById.mockResolvedValue({
      _id: USER_ID,
      is_active: true,
      timezone: "Asia/Karachi",
      toPublicProfile: jest.fn(),
    });
    require("../models").UserSetting.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({ behavioral_analytics_enabled: true }),
    });
    ActivityLog.countDocuments.mockResolvedValue(0);
    ActivityLog.aggregate.mockResolvedValue([]);
    ActivityLog.find.mockReturnValue(makeQueryChain());
    Task.countDocuments.mockResolvedValue(0);
    Task.aggregate.mockResolvedValue([]);
    Task.find.mockReturnValue(makeQueryChain());
  });

  test("GET /api/analytics/dashboard -> unified payload", async () => {
    callAIAnalytics.mockResolvedValueOnce({
      status: "success",
      data: {
        type: "full",
        has_enough_data: true,
        total_completed: 25,
        thresholds: { global: 20, per_day: 5 },
        days: [{ day: "Tuesday", day_num: 1, score: 0.9, log_count: 10, on_time_rate: 0.88 }],
        hours: [
          { day: "Thursday", day_num: 3, hour: 13, hour_display: "1PM", score: 0.88, on_time_rate: 1, log_count: 5 },
          { day: "Thursday", day_num: 3, hour: 17, hour_display: "5PM", score: 0.71, on_time_rate: 1, log_count: 3 },
          { day: "Tuesday", day_num: 1, hour: 14, hour_display: "2PM", score: 0.7, on_time_rate: 1, log_count: 3 },
        ],
        unreliable_days: [],
        completion_rate: { total_completed: 25, on_time: 20, late: 5, on_time_rate: 80 },
        avg_time_taken: 55,
      },
    });

    const response = await request(app)
      .get("/api/analytics/dashboard?days=30")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");
    expect(response.body.data.hero).toBeDefined();
    expect(response.body.data.behavioral).toBeDefined();
    expect(response.body.data.heatmap).toBeDefined();
    expect(response.body.data.tasks).toBeDefined();
    expect(response.body.data.completion_trend.weeks).toBe(3);
    expect(Array.isArray(response.body.data.best_slots)).toBe(true);
    expect(response.body.data.best_slots).toHaveLength(3);
    expect(response.body.data.insights).toBeUndefined();
    expect(response.body.data.empty_state).toBeUndefined();
    expect(callAIAnalytics).toHaveBeenCalledWith({
      userId: USER_ID,
      type: "full",
    });
  });

  test("GET /api/analytics/dashboard with invalid days -> 400", async () => {
    const response = await request(app)
      .get("/api/analytics/dashboard?days=14")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(400);
    expect(response.body.message).toBe("days must be 7, 30, or 90");
  });

  test("GET /api/analytics/dashboard -> 401 without token", async () => {
    const response = await request(app).get("/api/analytics/dashboard");
    expect(response.status).toBe(401);
  });
});

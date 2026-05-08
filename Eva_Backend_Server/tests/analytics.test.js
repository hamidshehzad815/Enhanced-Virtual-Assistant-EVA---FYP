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
    findOne: jest.fn(),
    findOneAndUpdate: jest.fn(),
  },
  ActivityLog: {
    aggregate: jest.fn(),
  },
  Integration: {},
}));

const app = require("../app");
const { User, ActivityLog } = require("../models");
const { callAIAnalytics } = require("../services/ai.service");

const USER_ID = "507f1f77bcf86cd799439011";

const makeToken = () =>
  jwt.sign({ userId: USER_ID }, process.env.JWT_ACCESS_SECRET, {
    expiresIn: "15m",
  });

describe("Analytics API", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    User.findById.mockResolvedValue({
      _id: USER_ID,
      is_active: true,
      timezone: "Asia/Karachi",
      toPublicProfile: jest.fn(),
    });
  });

  test("GET /api/analytics/productivity -> 200 + scored shape", async () => {
    callAIAnalytics.mockResolvedValueOnce({
      status: "success",
      data: {
        type: "full",
        has_enough_data: true,
        total_completed: 25,
        thresholds: { global: 20, per_day: 5 },
        days: [{ day: "Monday", day_num: 0, score: 0.82, log_count: 8, on_time_rate: 0.88 }],
        unreliable_days: [{ day: "Wednesday", day_num: 2, log_count: 2, needed: 5 }],
        hours: [{ day: "Monday", day_num: 0, hour: 18, hour_display: "6PM", score: 0.83, on_time_rate: 0.9, log_count: 6 }],
        completion_rate: { total_completed: 25, on_time: 21, late: 4, on_time_rate: 84, weekly_trend: [] },
        avg_time_taken: 64.2,
      },
    });

    const response = await request(app)
      .get("/api/analytics/productivity")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");
    expect(response.body.data.type).toBe("full");
    expect(response.body.data.total_completed).toBe(25);
    expect(Array.isArray(response.body.data.days)).toBe(true);
    expect(Array.isArray(response.body.data.unreliable_days)).toBe(true);
    expect(callAIAnalytics).toHaveBeenCalledWith({
      userId: USER_ID,
      type: "full",
    });
  });

  test("GET /api/analytics/hours?day=monday -> filtered scored data", async () => {
    callAIAnalytics.mockResolvedValueOnce({
      status: "success",
      data: {
        type: "hours",
        day_filter: 0,
        has_enough_data: true,
        hours: [
          { day: "Monday", day_num: 0, hour: 18, hour_display: "6PM", score: 0.88, on_time_rate: 0.9, log_count: 7 },
          { day: "Monday", day_num: 0, hour: 20, hour_display: "8PM", score: 0.81, on_time_rate: 0.86, log_count: 6 },
        ],
      },
    });

    const response = await request(app)
      .get("/api/analytics/hours?day=monday")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");
    expect(response.body.data.type).toBe("hours");
    expect(response.body.data.day_filter).toBe(0);
    expect(response.body.data.hours[0].day_num).toBe(0);
    expect(callAIAnalytics).toHaveBeenCalledWith({
      userId: USER_ID,
      type: "hours",
      day: "monday",
    });
  });

  test("GET /api/analytics/hours with invalid day -> 400", async () => {
    const response = await request(app)
      .get("/api/analytics/hours?day=invalid-day")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(400);
    expect(response.body.status).toBe("fail");
    expect(response.body.message).toBe("Invalid day query value");
    expect(callAIAnalytics).not.toHaveBeenCalled();
  });

  test("GET /api/analytics/days -> reliable/unreliable split", async () => {
    callAIAnalytics.mockResolvedValueOnce({
      status: "success",
      data: {
        type: "days",
        has_enough_data: true,
        days: [
          { day: "Tuesday", day_num: 1, score: 0.85, log_count: 9, on_time_rate: 0.89 },
          { day: "Monday", day_num: 0, score: 0.81, log_count: 8, on_time_rate: 0.88 },
        ],
        unreliable_days: [
          { day: "Friday", day_num: 4, log_count: 2, needed: 5 },
        ],
      },
    });

    const response = await request(app)
      .get("/api/analytics/days")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");
    expect(response.body.data.type).toBe("days");
    expect(response.body.data.days[0].day).toBe("Tuesday");
    expect(response.body.data.unreliable_days[0].day).toBe("Friday");
    expect(callAIAnalytics).toHaveBeenCalledWith({
      userId: USER_ID,
      type: "days",
    });
  });

  test("GET /api/analytics/completion-trend?weeks=2 -> returns weekly completion trend", async () => {
    ActivityLog.aggregate.mockResolvedValueOnce([
      { week: 14, count: 4, on_time: 3 },
      { week: 15, count: 6, on_time: 5 },
    ]);

    const response = await request(app)
      .get("/api/analytics/completion-trend?weeks=2")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");
    expect(response.body.data.weeks).toBe(2);
    expect(response.body.data.trend).toEqual([
      { week: 14, count: 4, on_time: 3 },
      { week: 15, count: 6, on_time: 5 },
    ]);
  });

  test("GET /api/analytics/completion-trend with invalid weeks -> 400", async () => {
    const response = await request(app)
      .get("/api/analytics/completion-trend?weeks=0")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(400);
    expect(response.body.status).toBe("fail");
    expect(response.body.message).toBe("weeks must be an integer between 1 and 52");
    expect(ActivityLog.aggregate).not.toHaveBeenCalled();
  });

  test("analytics routes are protected -> 401 without token", async () => {
    const [productivity, hours, days, trend] = await Promise.all([
      request(app).get("/api/analytics/productivity"),
      request(app).get("/api/analytics/hours"),
      request(app).get("/api/analytics/days"),
      request(app).get("/api/analytics/completion-trend"),
    ]);

    expect(productivity.status).toBe(401);
    expect(hours.status).toBe(401);
    expect(days.status).toBe(401);
    expect(trend.status).toBe(401);
  });

  test("analytics empty-data responses return success and zero/empty payloads", async () => {
    callAIAnalytics
      .mockResolvedValueOnce({
        status: "success",
        data: {
          type: "full",
          total_completed: 0,
          has_enough_data: false,
          thresholds: { global: 20, per_day: 5 },
          days: [],
          unreliable_days: [],
          hours: [],
          completion_rate: { total_completed: 0, on_time: 0, late: 0, on_time_rate: 0, weekly_trend: [] },
          avg_time_taken: null,
        },
      })
      .mockResolvedValueOnce({
        status: "success",
        data: {
          type: "hours",
          has_enough_data: false,
          hours: [],
        },
      })
      .mockResolvedValueOnce({
        status: "success",
        data: {
          type: "days",
          has_enough_data: false,
          days: [],
          unreliable_days: [],
        },
      });

    ActivityLog.aggregate.mockResolvedValueOnce([]);

    const [productivity, hours, days, trend] = await Promise.all([
      request(app)
        .get("/api/analytics/productivity")
        .set("Authorization", `Bearer ${makeToken()}`),
      request(app)
        .get("/api/analytics/hours")
        .set("Authorization", `Bearer ${makeToken()}`),
      request(app)
        .get("/api/analytics/days")
        .set("Authorization", `Bearer ${makeToken()}`),
      request(app)
        .get("/api/analytics/completion-trend")
        .set("Authorization", `Bearer ${makeToken()}`),
    ]);

    expect(productivity.status).toBe(200);
    expect(productivity.body.data.total_completed).toBe(0);
    expect(productivity.body.data.days).toEqual([]);

    expect(hours.status).toBe(200);
    expect(hours.body.data.hours).toEqual([]);

    expect(days.status).toBe(200);
    expect(days.body.data.days).toEqual([]);

    expect(trend.status).toBe(200);
    expect(trend.body.data.weeks).toBe(4);
    expect(trend.body.data.trend).toEqual([]);
  });
});


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

  test("GET /api/analytics/productivity -> returns completion metrics + days", async () => {
    ActivityLog.aggregate
      .mockResolvedValueOnce([{ total_completed: 5, on_time: 3 }])
      .mockResolvedValueOnce([{ week: 12, count: 2 }, { week: 13, count: 3 }])
      .mockResolvedValueOnce([
        { _id: 1, count: 3, on_time_count: 2 },
        { _id: 0, count: 2, on_time_count: 1 },
      ]);

    const response = await request(app)
      .get("/api/analytics/productivity")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");
    expect(response.body.data.total_completed).toBe(5);
    expect(response.body.data.on_time).toBe(3);
    expect(response.body.data.late).toBe(2);
    expect(response.body.data.on_time_rate).toBe(60);
    expect(response.body.data.weekly_trend).toEqual([
      { week: 12, count: 2 },
      { week: 13, count: 3 },
    ]);
    expect(response.body.data.days).toHaveLength(7);
    expect(response.body.data.days[0]).toMatchObject({
      day_name: "Tuesday",
      day_num: 1,
      count: 3,
      on_time_rate: 0.67,
    });
  });

  test("GET /api/analytics/productivity with date range applies user timezone boundaries", async () => {
    ActivityLog.aggregate
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([]);

    const response = await request(app)
      .get("/api/analytics/productivity?start_date=2026-03-30&end_date=2026-03-31")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(ActivityLog.aggregate).toHaveBeenCalled();

    const summaryPipeline = ActivityLog.aggregate.mock.calls[0][0];
    const match = summaryPipeline[0].$match;
    expect(match.action_timestamp.$gte.toISOString()).toBe("2026-03-29T19:00:00.000Z");
    expect(match.action_timestamp.$lte.toISOString()).toBe("2026-03-31T18:59:59.999Z");
  });

  test("GET /api/analytics/hours?day=monday -> returns filtered hours", async () => {
    ActivityLog.aggregate.mockResolvedValueOnce([
      { _id: 18, count: 3, on_time_count: 2 },
      { _id: 10, count: 1, on_time_count: 1 },
    ]);

    const response = await request(app)
      .get("/api/analytics/hours?day=monday")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");
    expect(response.body.data.filter).toEqual({
      day: 0,
      day_name: "Monday",
    });
    expect(response.body.data.hours).toEqual([
      { hour: 18, count: 3, on_time_rate: 0.67 },
      { hour: 10, count: 1, on_time_rate: 1 },
    ]);

    const pipeline = ActivityLog.aggregate.mock.calls[0][0];
    expect(pipeline[0].$match.day_of_week).toBe(0);
  });

  test("GET /api/analytics/hours with invalid day -> 400", async () => {
    const response = await request(app)
      .get("/api/analytics/hours?day=invalid-day")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(400);
    expect(response.body.status).toBe("fail");
    expect(response.body.message).toBe("Invalid day query value");
    expect(ActivityLog.aggregate).not.toHaveBeenCalled();
  });

  test("GET /api/analytics/days -> returns ranked day distribution", async () => {
    ActivityLog.aggregate.mockResolvedValueOnce([
      { _id: 4, count: 5, on_time_count: 4 },
      { _id: 1, count: 7, on_time_count: 5 },
    ]);

    const response = await request(app)
      .get("/api/analytics/days")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");
    expect(response.body.data.days).toHaveLength(7);
    expect(response.body.data.days[0]).toMatchObject({
      day_name: "Tuesday",
      day_num: 1,
      count: 7,
      on_time_rate: 0.71,
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
    ActivityLog.aggregate
      .mockResolvedValueOnce([]) // productivity summary
      .mockResolvedValueOnce([]) // productivity trend
      .mockResolvedValueOnce([]) // productivity days
      .mockResolvedValueOnce([]) // hours
      .mockResolvedValueOnce([]) // days
      .mockResolvedValueOnce([]); // completion trend

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
    expect(productivity.body.data.on_time_rate).toBe(0);
    expect(productivity.body.data.days).toHaveLength(7);

    expect(hours.status).toBe(200);
    expect(hours.body.data.hours).toEqual([]);

    expect(days.status).toBe(200);
    expect(days.body.data.days).toHaveLength(7);
    expect(days.body.data.days.every((item) => item.count === 0)).toBe(true);

    expect(trend.status).toBe(200);
    expect(trend.body.data.weeks).toBe(4);
    expect(trend.body.data.trend).toEqual([]);
  });
});

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

  test("GET /api/analytics/dashboard -> de-duplicated behavioral payload", async () => {
    callAIAnalytics.mockResolvedValueOnce({
      status: "success",
      data: {
        type: "full",
        has_enough_data: true,
        total_completed: 25,
        days: [
          { day: "Thursday", day_num: 3, score: 0.9, log_count: 8, on_time_rate: 0.9 },
          { day: "Tuesday", day_num: 1, score: 0.8, log_count: 7, on_time_rate: 0.88 },
        ],
        hours: [
          { day: "Thursday", day_num: 3, hour: 13, hour_display: "1PM", score: 0.88, on_time_rate: 0.92, log_count: 5 },
          { day: "Thursday", day_num: 3, hour: 17, hour_display: "5PM", score: 0.71, on_time_rate: 0.9, log_count: 3 },
          { day: "Tuesday", day_num: 1, hour: 14, hour_display: "2PM", score: 0.7, on_time_rate: 1, log_count: 3 },
        ],
      },
    });

    const response = await request(app)
      .get("/api/analytics/dashboard?days=30")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");
    const { data } = response.body;

    // Metadata
    expect(data.range_days).toBe(30);
    expect(typeof data.meta.has_enough_data).toBe("boolean");

    // 1) snapshot — single home for headline numbers
    expect(typeof data.snapshot.productivity_score.score).toBe("number");
    expect(data.snapshot.productivity_score.rating).toBeDefined();
    expect(typeof data.snapshot.on_time_rate).toBe("number");
    expect(typeof data.snapshot.current_streak).toBe("number");
    expect(data.snapshot.completed).toHaveProperty("period");
    expect(data.snapshot.completed).toHaveProperty("previous");
    expect(data.snapshot.completed).toHaveProperty("change_percent");

    // 2) insights
    expect(Array.isArray(data.insights)).toBe(true);

    // 3) activity — daily series, no total field
    expect(Array.isArray(data.activity.series)).toBe(true);
    expect(data.activity.series).toHaveLength(30);
    expect(data.activity.total).toBeUndefined();

    // 4) behavioral — flagship: top-3 days each with their best hours
    expect(data.behavioral.source).toBe("ai");
    expect(data.behavioral.has_scores).toBe(true);
    expect(data.behavioral.top_days).toHaveLength(2);
    expect(data.behavioral.top_days[0].day).toBe("Thursday");
    expect(data.behavioral.top_days[0].on_time_rate).toBe(90); // 0.9 -> percentage
    expect(data.behavioral.top_days[0].hours).toHaveLength(2); // both Thursday hours
    expect(data.behavioral.top_days[0].hours[0].hour_display).toBe("1PM");
    expect(data.behavioral.focus).toHaveProperty("avg_minutes");
    expect(data.behavioral.momentum).toHaveProperty("direction");
    expect(data.behavioral.procrastination).toHaveProperty("late_night_rate");
    expect(data.behavioral.procrastination).toHaveProperty("reschedule_rate");
    expect(Array.isArray(data.behavioral.unreliable_days)).toBe(true);

    // 5) heatmap — grid only (peak derived client-side)
    expect(Array.isArray(data.heatmap.cells)).toBe(true);
    expect(data.heatmap.hour_range.start).toBe(6);
    expect(data.heatmap.peak).toBeUndefined();

    // 6) work_patterns — two breakdowns; priority rows now carry avg_minutes
    expect(data.work_patterns.time_of_day).toHaveLength(4);
    expect(data.work_patterns.by_priority).toHaveLength(3);
    expect(data.work_patterns.by_priority[0]).toHaveProperty("avg_minutes");

    // 7) needs_attention
    expect(data.needs_attention).toHaveProperty("overdue");
    expect(data.needs_attention).toHaveProperty("due_next_7d");
    expect(Array.isArray(data.needs_attention.due_soon)).toBe(true);

    // Old / removed keys must be gone
    expect(data.hero).toBeUndefined();
    expect(data.productivity_map).toBeUndefined();
    expect(data.best_slots).toBeUndefined();
    expect(data.completion_trend).toBeUndefined();
    expect(data.tasks).toBeUndefined();

    expect(callAIAnalytics).toHaveBeenCalledWith({
      userId: USER_ID,
      type: "full",
    });
  });

  test("GET /api/analytics/dashboard?days=7 -> range + Mongo behavioral fallback", async () => {
    callAIAnalytics.mockResolvedValueOnce({
      status: "success",
      data: { has_enough_data: false, total_completed: 0, hours: [], days: [] },
    });

    const response = await request(app)
      .get("/api/analytics/dashboard?days=7")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.data.activity.series).toHaveLength(7);
    expect(response.body.data.range_days).toBe(7);
    // No AI days -> falls back to Mongo ranking (empty logs -> empty list)
    expect(response.body.data.behavioral.source).toBe("history");
    expect(response.body.data.behavioral.top_days).toEqual([]);
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

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
  Task: {
    find: jest.fn(),
  },
  ChatSession: {},
  ConversationHistory: {},
  Notification: {},
  ActivityLog: {},
  Integration: {},
}));

const app = require("../app");
const { User, UserSetting, Task } = require("../models");

const USER_ID = "507f1f77bcf86cd799439011";

const makeToken = () =>
  jwt.sign({ userId: USER_ID }, process.env.JWT_ACCESS_SECRET, {
    expiresIn: "15m",
  });

const authHeaders = () => ({
  Authorization: `Bearer ${makeToken()}`,
});

describe("PATCH /api/settings/learning-schedule", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    User.findById.mockResolvedValue({
      _id: USER_ID,
      is_active: true,
      timezone: "UTC",
    });
  });

  function mockOpenTasks(tasks) {
    Task.find.mockReturnValue({
      select: jest.fn().mockReturnValue({
        lean: jest.fn().mockResolvedValue(tasks),
      }),
    });
  }

  test("valid schedule → 200 and saved", async () => {
    mockOpenTasks([]);
    const mockSettings = {
      user_id: USER_ID,
      preferred_learning_schedule: [],
      save: jest.fn().mockResolvedValue(),
    };
    UserSetting.findOne.mockResolvedValue(mockSettings);

    const response = await request(app)
      .patch("/api/settings/learning-schedule")
      .set(authHeaders())
      .send({
        preferred_learning_schedule: [{ day: 0, time: "09:00" }],
      });

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");
    expect(mockSettings.preferred_learning_schedule).toEqual([
      { day: 0, time: "09:00" },
    ]);
    expect(mockSettings.save).toHaveBeenCalled();
  });

  test("invalid day → 400", async () => {
    mockOpenTasks([]);
    UserSetting.findOne.mockResolvedValue({
      user_id: USER_ID,
      preferred_learning_schedule: [],
      save: jest.fn().mockResolvedValue(),
    });

    const response = await request(app)
      .patch("/api/settings/learning-schedule")
      .set(authHeaders())
      .send({
        preferred_learning_schedule: [{ day: 8, time: "09:00" }],
      });

    expect(response.status).toBe(400);
    expect(response.body.status).toBe("fail");
  });

  test("invalid time format → 400", async () => {
    mockOpenTasks([]);
    UserSetting.findOne.mockResolvedValue({
      user_id: USER_ID,
      preferred_learning_schedule: [],
      save: jest.fn().mockResolvedValue(),
    });

    const response = await request(app)
      .patch("/api/settings/learning-schedule")
      .set(authHeaders())
      .send({
        preferred_learning_schedule: [{ day: 0, time: "25:99" }],
      });

    expect(response.status).toBe(400);
  });

  test("empty schedule → 400", async () => {
    mockOpenTasks([]);
    UserSetting.findOne.mockResolvedValue({
      user_id: USER_ID,
      preferred_learning_schedule: [],
      save: jest.fn().mockResolvedValue(),
    });

    const response = await request(app)
      .patch("/api/settings/learning-schedule")
      .set(authHeaders())
      .send({
        preferred_learning_schedule: [],
      });

    expect(response.status).toBe(400);
    expect(response.body.message).toMatch(/at least one day/i);
  });

  test("conflict with existing task → 409 with details", async () => {
    mockOpenTasks([
      {
        _id: "507f1f77bcf86cd799439099",
        title: "Overlap",
        due_datetime: new Date(Date.UTC(2026, 0, 5, 10, 30, 0)),
        status: "pending",
      },
    ]);
    UserSetting.findOne.mockResolvedValue({
      user_id: USER_ID,
      preferred_learning_schedule: [],
      save: jest.fn().mockResolvedValue(),
    });

    const response = await request(app)
      .patch("/api/settings/learning-schedule")
      .set(authHeaders())
      .send({
        preferred_learning_schedule: [{ day: 0, time: "10:30" }],
      });

    expect(response.status).toBe(409);
    expect(response.body.message).toMatch(/conflicts/i);
    expect(response.body.data.conflicts).toHaveLength(1);
    expect(response.body.data.conflicts[0].task.title).toBe("Overlap");
  });

  test("pending task on another weekday same clock → no conflict", async () => {
    mockOpenTasks([
      {
        _id: "507f1f77bcf86cd799439099",
        title: "Tuesday slot",
        due_datetime: new Date(Date.UTC(2026, 0, 6, 10, 30, 0)),
        status: "pending",
      },
    ]);
    const mockSettings = {
      user_id: USER_ID,
      preferred_learning_schedule: [],
      save: jest.fn().mockResolvedValue(),
    };
    UserSetting.findOne.mockResolvedValue(mockSettings);

    const response = await request(app)
      .patch("/api/settings/learning-schedule")
      .set(authHeaders())
      .send({
        preferred_learning_schedule: [{ day: 0, time: "10:30" }],
      });

    expect(response.status).toBe(200);
    expect(mockSettings.save).toHaveBeenCalled();
  });
});

describe("GET /api/settings includes preferred_learning_schedule", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    User.findById.mockResolvedValue({
      _id: USER_ID,
      is_active: true,
      timezone: "UTC",
    });
  });

  test("returns schedule on settings document", async () => {
    UserSetting.findOne.mockResolvedValue({
      user_id: USER_ID,
      theme: "dark",
      preferred_learning_schedule: [{ day: 2, time: "14:00" }],
      save: jest.fn().mockResolvedValue(),
    });

    const response = await request(app)
      .get("/api/settings")
      .set({
        Authorization: `Bearer ${makeToken()}`,
      });

    expect(response.status).toBe(200);
    expect(response.body.data.settings.preferred_learning_schedule).toEqual([
      { day: 2, time: "14:00" },
    ]);
  });
});

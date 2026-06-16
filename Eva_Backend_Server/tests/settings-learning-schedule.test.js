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

jest.mock("../services/ai.service", () => ({
  callAIServer: jest.fn(),
  callAIAnalytics: jest.fn(),
  callAIInternal: jest.fn(),
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
  LearningGoal: {
    exists: jest.fn(),
  },
  ChatSession: {},
  ConversationHistory: {},
  Notification: {},
  ActivityLog: {},
  Integration: {},
}));

const app = require("../app");
const { User, UserSetting, Task, LearningGoal } = require("../models");

const USER_ID = "507f1f77bcf86cd799439011";

const makeToken = () =>
  jwt.sign({ userId: USER_ID }, process.env.JWT_ACCESS_SECRET, {
    expiresIn: "15m",
  });

const authHeaders = () => ({
  Authorization: `Bearer ${makeToken()}`,
});

function mockOpenTasks(tasks) {
  Task.find.mockReturnValue({
    select: jest.fn().mockReturnValue({
      lean: jest.fn().mockResolvedValue(tasks),
    }),
  });
}

describe("learning schedule routes (no bulk PATCH)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    User.findById.mockResolvedValue({
      _id: USER_ID,
      is_active: true,
      timezone: "UTC",
    });
    UserSetting.findOne.mockResolvedValue({
      user_id: USER_ID,
      save: jest.fn().mockResolvedValue(),
    });
  });

  test("PATCH /api/settings/learning-schedule route removed → 404", async () => {
    const response = await request(app)
      .patch("/api/settings/learning-schedule")
      .set(authHeaders())
      .send({ preferred_learning_schedules: [] });

    expect(response.status).toBe(404);
  });

  test("PATCH /api/settings rejects preferred_learning_schedules", async () => {
    const response = await request(app)
      .patch("/api/settings")
      .set(authHeaders())
      .send({
        preferred_learning_schedules: [
          {
            label: "Morning",
            slots: [{ day: 0, time: "09:00", duration_minutes: 45 }],
          },
        ],
      });

    expect(response.status).toBe(400);
    expect(response.body.message).toMatch(/learning-schedules instead/i);
  });
});

describe("learning-schedules CRUD", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    LearningGoal.exists.mockResolvedValue(null);
    User.findById.mockResolvedValue({
      _id: USER_ID,
      is_active: true,
      timezone: "UTC",
    });
    mockOpenTasks([]);
  });

  test("POST create → 201", async () => {
    const mockSettings = {
      user_id: USER_ID,
      preferred_learning_schedules: [],
      save: jest.fn().mockResolvedValue(),
    };
    UserSetting.findOne.mockResolvedValue(mockSettings);

    const response = await request(app)
      .post("/api/settings/learning-schedules")
      .set(authHeaders())
      .send({
        label: "Morning",
        slots: [{ day: 0, time: "09:00", duration_minutes: 60 }],
      });

    expect(response.status).toBe(201);
    expect(mockSettings.preferred_learning_schedules).toHaveLength(1);
    expect(mockSettings.preferred_learning_schedules[0].label).toBe("Morning");
  });

  test("POST second schedule → 201", async () => {
    const mockSettings = {
      user_id: USER_ID,
      preferred_learning_schedules: [
        {
          id: "s1",
          label: "Morning",
          slots: [{ day: 0, time: "09:00", duration_minutes: 60 }],
        },
      ],
      save: jest.fn().mockResolvedValue(),
    };
    UserSetting.findOne.mockResolvedValue(mockSettings);

    const response = await request(app)
      .post("/api/settings/learning-schedules")
      .set(authHeaders())
      .send({
        label: "Evening",
        slots: [{ day: 2, time: "18:00", duration_minutes: 45 }],
      });

    expect(response.status).toBe(201);
    expect(mockSettings.preferred_learning_schedules).toHaveLength(2);
  });

  test("POST schedule with duplicate label → 400", async () => {
    UserSetting.findOne.mockResolvedValue({
      user_id: USER_ID,
      preferred_learning_schedules: [
        {
          id: "s1",
          label: "Python learning",
          slots: [{ day: 0, time: "18:00", duration_minutes: 60 }],
        },
      ],
      save: jest.fn().mockResolvedValue(),
    });

    const response = await request(app)
      .post("/api/settings/learning-schedules")
      .set(authHeaders())
      .send({
        label: "Python learning",
        slots: [{ day: 1, time: "10:00", duration_minutes: 60 }],
      });

    expect(response.status).toBe(400);
  });

  test("POST schedule with same day+time as existing → 409", async () => {
    UserSetting.findOne.mockResolvedValue({
      user_id: USER_ID,
      preferred_learning_schedules: [
        {
          id: "s1",
          label: "Python learning",
          slots: [
            { day: 0, time: "18:00", duration_minutes: 60 },
            { day: 2, time: "19:00", duration_minutes: 90 },
          ],
        },
      ],
      save: jest.fn().mockResolvedValue(),
    });

    const response = await request(app)
      .post("/api/settings/learning-schedules")
      .set(authHeaders())
      .send({
        label: "Python learning 2",
        slots: [
          { day: 0, time: "18:00", duration_minutes: 60 },
          { day: 2, time: "19:00", duration_minutes: 75 },
        ],
      });

    expect(response.status).toBe(409);
    expect(response.body.message).toMatch(/18:00|Monday/i);
  });

  test("POST schedule same day different time → 201", async () => {
    const mockSettings = {
      user_id: USER_ID,
      preferred_learning_schedules: [
        {
          id: "s1",
          label: "Python learning",
          slots: [{ day: 0, time: "18:00", duration_minutes: 60 }],
        },
      ],
      save: jest.fn().mockResolvedValue(),
    };
    UserSetting.findOne.mockResolvedValue(mockSettings);

    const response = await request(app)
      .post("/api/settings/learning-schedules")
      .set(authHeaders())
      .send({
        label: "Python learning 2",
        slots: [{ day: 0, time: "20:00", duration_minutes: 75 }],
      });

    expect(response.status).toBe(201);
    expect(mockSettings.preferred_learning_schedules).toHaveLength(2);
  });

  test("PATCH update by id → 200", async () => {
    const mockSettings = {
      user_id: USER_ID,
      preferred_learning_schedules: [
        {
          id: "s1",
          label: "Morning",
          slots: [{ day: 0, time: "09:00", duration_minutes: 60 }],
        },
      ],
      save: jest.fn().mockResolvedValue(),
    };
    UserSetting.findOne.mockResolvedValue(mockSettings);

    const response = await request(app)
      .patch("/api/settings/learning-schedules/s1")
      .set(authHeaders())
      .send({
        label: "Early morning",
        slots: [{ day: 0, time: "07:30", duration_minutes: 90 }],
      });

    expect(response.status).toBe(200);
    expect(mockSettings.preferred_learning_schedules[0].label).toBe("Early morning");
  });

  test("DELETE by id → 200", async () => {
    const mockSettings = {
      user_id: USER_ID,
      preferred_learning_schedules: [
        {
          id: "s1",
          label: "Morning",
          slots: [{ day: 0, time: "09:00", duration_minutes: 60 }],
        },
        {
          id: "s2",
          label: "Evening",
          slots: [{ day: 2, time: "18:00", duration_minutes: 45 }],
        },
      ],
      save: jest.fn().mockResolvedValue(),
    };
    UserSetting.findOne.mockResolvedValue(mockSettings);

    const response = await request(app)
      .delete("/api/settings/learning-schedules/s2")
      .set(authHeaders());

    expect(response.status).toBe(200);
    expect(mockSettings.preferred_learning_schedules).toHaveLength(1);
  });

  test("PATCH slots when active goal uses schedule → 409", async () => {
    LearningGoal.exists.mockResolvedValue({ _id: "goal1" });
    UserSetting.findOne.mockResolvedValue({
      user_id: USER_ID,
      preferred_learning_schedules: [
        {
          id: "s1",
          label: "Morning",
          slots: [{ day: 0, time: "09:00", duration_minutes: 60 }],
        },
      ],
      save: jest.fn().mockResolvedValue(),
    });

    const response = await request(app)
      .patch("/api/settings/learning-schedules/s1")
      .set(authHeaders())
      .send({
        slots: [{ day: 0, time: "10:00", duration_minutes: 60 }],
      });

    expect(response.status).toBe(409);
  });

  test("DELETE when active goal uses schedule → 409", async () => {
    LearningGoal.exists.mockResolvedValue({ _id: "goal1" });
    UserSetting.findOne.mockResolvedValue({
      user_id: USER_ID,
      preferred_learning_schedules: [
        {
          id: "s1",
          label: "Morning",
          slots: [{ day: 0, time: "09:00", duration_minutes: 60 }],
        },
      ],
      save: jest.fn().mockResolvedValue(),
    });

    const response = await request(app)
      .delete("/api/settings/learning-schedules/s1")
      .set(authHeaders());

    expect(response.status).toBe(409);
    expect(response.body.message).toMatch(/active or paused/i);
    expect(LearningGoal.exists).toHaveBeenCalledWith(
      expect.objectContaining({
        learning_schedule_id: "s1",
        status: { $in: ["active", "paused"] },
        is_deleted: false,
      }),
    );
  });

  test("DELETE when paused goal uses schedule → 409", async () => {
    LearningGoal.exists.mockResolvedValue({ _id: "goal1" });
    UserSetting.findOne.mockResolvedValue({
      user_id: USER_ID,
      preferred_learning_schedules: [
        {
          id: "s1",
          label: "Morning",
          slots: [{ day: 0, time: "09:00", duration_minutes: 60 }],
        },
      ],
      save: jest.fn().mockResolvedValue(),
    });

    const response = await request(app)
      .delete("/api/settings/learning-schedules/s1")
      .set(authHeaders());

    expect(response.status).toBe(409);
    expect(response.body.message).toMatch(/active or paused/i);
  });

  test("DELETE succeeds when only soft-deleted goals used schedule", async () => {
    LearningGoal.exists.mockResolvedValue(null);
    const mockSettings = {
      user_id: USER_ID,
      preferred_learning_schedules: [
        {
          id: "s1",
          label: "Morning",
          slots: [{ day: 0, time: "09:00", duration_minutes: 60 }],
        },
      ],
      save: jest.fn().mockResolvedValue(),
    };
    UserSetting.findOne.mockResolvedValue(mockSettings);

    const response = await request(app)
      .delete("/api/settings/learning-schedules/s1")
      .set(authHeaders());

    expect(response.status).toBe(200);
    expect(LearningGoal.exists).toHaveBeenCalledWith(
      expect.objectContaining({
        status: { $in: ["active", "paused"] },
        is_deleted: false,
      }),
    );
  });

  test("GET list → 200", async () => {
    UserSetting.findOne.mockResolvedValue({
      user_id: USER_ID,
      preferred_learning_schedules: [
        {
          id: "a",
          label: "A",
          slots: [{ day: 1, time: "10:00", duration_minutes: 30 }],
        },
        {
          id: "b",
          label: "B",
          slots: [{ day: 3, time: "20:00", duration_minutes: 60 }],
        },
      ],
    });

    const response = await request(app)
      .get("/api/settings/learning-schedules")
      .set(authHeaders());

    expect(response.status).toBe(200);
    expect(response.body.data.preferred_learning_schedules).toHaveLength(2);
  });
});

describe("GET /api/settings", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    User.findById.mockResolvedValue({
      _id: USER_ID,
      is_active: true,
      timezone: "UTC",
    });
  });

  test("returns preferred_learning_schedules", async () => {
    UserSetting.findOne.mockResolvedValue({
      user_id: USER_ID,
      theme: "dark",
      preferred_learning_schedules: [
        {
          id: "s1",
          label: "Study",
          slots: [{ day: 2, time: "14:00", duration_minutes: 60 }],
        },
      ],
    });

    const response = await request(app).get("/api/settings").set(authHeaders());

    expect(response.status).toBe(200);
    expect(response.body.data.settings.preferred_learning_schedules).toHaveLength(1);
    expect(response.body.data.settings.preferred_learning_schedules[0].label).toBe(
      "Study",
    );
    expect(response.body.data.preferred_learning_schedules).toBeUndefined();
  });

  test("migrates orphan flat slots from old Mongo docs on read", async () => {
    UserSetting.findOne.mockResolvedValue({
      user_id: USER_ID,
      preferred_learning_schedules: [],
      preferred_learning_schedule: [{ day: 2, time: "14:00" }],
    });

    const response = await request(app).get("/api/settings").set(authHeaders());

    expect(response.status).toBe(200);
    expect(response.body.data.settings.preferred_learning_schedules).toHaveLength(1);
    expect(response.body.data.settings.preferred_learning_schedules[0].label).toBe(
      "Default",
    );
    expect(response.body.data.preferred_learning_schedules).toBeUndefined();
  });

  test("returns allow_friend_requests true when missing on stored doc", async () => {
    UserSetting.findOne.mockResolvedValue({
      user_id: USER_ID,
      theme: "light",
    });

    const response = await request(app).get("/api/settings").set(authHeaders());

    expect(response.status).toBe(200);
    expect(response.body.data.settings.allow_friend_requests).toBe(true);
  });

  test("returns allow_friend_requests false when stored as false", async () => {
    UserSetting.findOne.mockResolvedValue({
      user_id: USER_ID,
      allow_friend_requests: false,
    });

    const response = await request(app).get("/api/settings").set(authHeaders());

    expect(response.status).toBe(200);
    expect(response.body.data.settings.allow_friend_requests).toBe(false);
  });

  test("does not expose internal default_task_priority", async () => {
    UserSetting.findOne.mockResolvedValue({
      user_id: USER_ID,
      default_task_priority: "high",
      default_task_duration: 120,
    });

    const response = await request(app).get("/api/settings").set(authHeaders());

    expect(response.status).toBe(200);
    expect(response.body.data.settings.default_task_priority).toBeUndefined();
    expect(response.body.data.settings.default_task_duration).toBe(120);
  });
});

describe("PATCH /api/settings internal fields", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    User.findById.mockResolvedValue({
      _id: USER_ID,
      is_active: true,
      timezone: "UTC",
    });
    UserSetting.findOne.mockResolvedValue({
      user_id: USER_ID,
      save: jest.fn().mockResolvedValue(),
    });
  });

  test("rejects analytics_min_tasks_threshold", async () => {
    const response = await request(app)
      .patch("/api/settings")
      .set(authHeaders())
      .send({ analytics_min_tasks_threshold: 10 });

    expect(response.status).toBe(400);
    expect(response.body.message).toMatch(/system setting/i);
  });

  test("rejects preferred_learning_duration", async () => {
    const response = await request(app)
      .patch("/api/settings")
      .set(authHeaders())
      .send({ preferred_learning_duration: 60 });

    expect(response.status).toBe(400);
    expect(response.body.message).toMatch(/system setting/i);
  });

  test("rejects removed language setting", async () => {
    const response = await request(app)
      .patch("/api/settings")
      .set(authHeaders())
      .send({ language: "en" });

    expect(response.status).toBe(400);
    expect(response.body.message).toMatch(/language is no longer supported/i);
  });

  test("rejects removed show_last_active setting", async () => {
    const response = await request(app)
      .patch("/api/settings")
      .set(authHeaders())
      .send({ show_last_active: false });

    expect(response.status).toBe(400);
    expect(response.body.message).toMatch(/show_last_active is no longer supported/i);
  });

  test("rejects default_task_priority", async () => {
    const response = await request(app)
      .patch("/api/settings")
      .set(authHeaders())
      .send({ default_task_priority: "high" });

    expect(response.status).toBe(400);
    expect(response.body.message).toMatch(/system setting/i);
  });

  test("rejects removed default_topic_reminder_minutes setting", async () => {
    const response = await request(app)
      .patch("/api/settings")
      .set(authHeaders())
      .send({ default_topic_reminder_minutes: 20 });

    expect(response.status).toBe(400);
    expect(response.body.message).toMatch(
      /default_topic_reminder_minutes is no longer supported/i,
    );
  });

  test("rejects invalid allow_friend_requests", async () => {
    const response = await request(app)
      .patch("/api/settings")
      .set(authHeaders())
      .send({ allow_friend_requests: "friends_only" });

    expect(response.status).toBe(400);
    expect(response.body.message).toMatch(/allow_friend_requests must be boolean/i);
  });

  test("accepts allow_friend_requests false", async () => {
    const mockSettings = {
      user_id: USER_ID,
      save: jest.fn().mockResolvedValue(),
    };
    UserSetting.findOne.mockResolvedValue(mockSettings);

    const response = await request(app)
      .patch("/api/settings")
      .set(authHeaders())
      .send({ allow_friend_requests: false });

    expect(response.status).toBe(200);
    expect(mockSettings.allow_friend_requests).toBe(false);
    expect(mockSettings.save).toHaveBeenCalled();
  });

  test("accepts theme system", async () => {
    const mockSettings = {
      user_id: USER_ID,
      save: jest.fn().mockResolvedValue(),
    };
    UserSetting.findOne.mockResolvedValue(mockSettings);

    const response = await request(app)
      .patch("/api/settings")
      .set(authHeaders())
      .send({ theme: "system" });

    expect(response.status).toBe(200);
    expect(mockSettings.theme).toBe("system");
    expect(mockSettings.save).toHaveBeenCalled();
  });

  test("rejects invalid theme", async () => {
    const response = await request(app)
      .patch("/api/settings")
      .set(authHeaders())
      .send({ theme: "midnight" });

    expect(response.status).toBe(400);
    expect(response.body.message).toMatch(/theme must be one of/i);
  });
});

describe("learning schedule slot validation", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    LearningGoal.exists.mockResolvedValue(null);
    User.findById.mockResolvedValue({
      _id: USER_ID,
      is_active: true,
      timezone: "UTC",
    });
    mockOpenTasks([]);
  });

  test("POST schedule without duration_minutes → 400", async () => {
    UserSetting.findOne.mockResolvedValue({
      user_id: USER_ID,
      preferred_learning_schedules: [],
      save: jest.fn().mockResolvedValue(),
    });

    const response = await request(app)
      .post("/api/settings/learning-schedules")
      .set(authHeaders())
      .send({
        label: "Morning",
        slots: [{ day: 0, time: "09:00" }],
      });

    expect(response.status).toBe(400);
    expect(response.body.message).toMatch(/duration_minutes is required/i);
  });
});

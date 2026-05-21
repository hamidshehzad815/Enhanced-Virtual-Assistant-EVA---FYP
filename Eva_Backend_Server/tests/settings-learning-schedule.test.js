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

describe("PATCH /api/settings/learning-schedule", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    LearningGoal.exists.mockResolvedValue(null);
    User.findById.mockResolvedValue({
      _id: USER_ID,
      is_active: true,
      timezone: "UTC",
    });
  });

  test("labeled schedules bulk replace → 200", async () => {
    mockOpenTasks([]);
    const mockSettings = {
      user_id: USER_ID,
      preferred_learning_duration: 90,
      preferred_learning_schedules: [],
      save: jest.fn().mockResolvedValue(),
    };
    UserSetting.findOne.mockResolvedValue(mockSettings);

    const response = await request(app)
      .patch("/api/settings/learning-schedule")
      .set(authHeaders())
      .send({
        preferred_learning_schedules: [
          {
            label: "Morning",
            slots: [{ day: 0, time: "09:00", duration_minutes: 45 }],
          },
        ],
      });

    expect(response.status).toBe(200);
    expect(mockSettings.preferred_learning_schedules).toHaveLength(1);
    expect(mockSettings.preferred_learning_schedules[0].label).toBe("Morning");
    expect(mockSettings.preferred_learning_schedules[0].slots[0].duration_minutes).toBe(
      45,
    );
    expect(mockSettings.save).toHaveBeenCalled();
  });

  test("missing preferred_learning_schedules → 400", async () => {
    mockOpenTasks([]);
    UserSetting.findOne.mockResolvedValue({
      user_id: USER_ID,
      preferred_learning_schedules: [],
      save: jest.fn().mockResolvedValue(),
    });

    const response = await request(app)
      .patch("/api/settings/learning-schedule")
      .set(authHeaders())
      .send({});

    expect(response.status).toBe(400);
  });

  test("invalid day → 400", async () => {
    mockOpenTasks([]);
    UserSetting.findOne.mockResolvedValue({
      user_id: USER_ID,
      preferred_learning_schedules: [],
      save: jest.fn().mockResolvedValue(),
    });

    const response = await request(app)
      .patch("/api/settings/learning-schedule")
      .set(authHeaders())
      .send({
        preferred_learning_schedules: [
          {
            label: "Bad",
            slots: [{ day: 8, time: "09:00" }],
          },
        ],
      });

    expect(response.status).toBe(400);
  });

  test("conflict with existing task → 409", async () => {
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
      preferred_learning_schedules: [],
      save: jest.fn().mockResolvedValue(),
    });

    const response = await request(app)
      .patch("/api/settings/learning-schedule")
      .set(authHeaders())
      .send({
        preferred_learning_schedules: [
          {
            label: "Morning",
            slots: [{ day: 0, time: "10:30" }],
          },
        ],
      });

    expect(response.status).toBe(409);
    expect(response.body.data.conflicts[0].task.title).toBe("Overlap");
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
      preferred_learning_duration: 90,
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
      preferred_learning_duration: 90,
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
      preferred_learning_duration: 90,
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
  });

  test("GET list → 200", async () => {
    UserSetting.findOne.mockResolvedValue({
      user_id: USER_ID,
      preferred_learning_duration: 90,
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
      preferred_learning_duration: 90,
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
    expect(response.body.data.preferred_learning_schedules).toHaveLength(1);
    expect(response.body.data.preferred_learning_schedules[0].label).toBe("Study");
  });

  test("migrates orphan flat slots from old Mongo docs on read", async () => {
    UserSetting.findOne.mockResolvedValue({
      user_id: USER_ID,
      preferred_learning_duration: 90,
      preferred_learning_schedules: [],
      preferred_learning_schedule: [{ day: 2, time: "14:00" }],
    });

    const response = await request(app).get("/api/settings").set(authHeaders());

    expect(response.status).toBe(200);
    expect(response.body.data.preferred_learning_schedules).toHaveLength(1);
    expect(response.body.data.preferred_learning_schedules[0].label).toBe("Default");
  });
});

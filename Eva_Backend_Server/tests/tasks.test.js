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
  ActivityLog: {
    create: jest.fn(),
  },
  UserSetting: {
    findOne: jest.fn(),
  },
  Task: {
    find: jest.fn(),
    countDocuments: jest.fn(),
    findOne: jest.fn(),
    findOneAndUpdate: jest.fn(),
  },
  Integration: {},
}));

const app = require("../app");
const { User, Task, ActivityLog, UserSetting } = require("../models");

const USER_ID = "507f1f77bcf86cd799439011";
const TASK_ID = "507f1f77bcf86cd799439012";

const makeToken = () =>
  jwt.sign({ userId: USER_ID }, process.env.JWT_ACCESS_SECRET, {
    expiresIn: "15m",
  });

describe("Tasks API", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    User.findById.mockResolvedValue({
      _id: USER_ID,
      is_active: true,
      toPublicProfile: jest.fn(),
    });
  });

  test("GET /api/tasks -> returns upcoming task list", async () => {
    const tasks = [
      {
        _id: TASK_ID,
        title: "Physics quiz",
        status: "pending",
        priority: "medium",
      },
    ];

    const findChain = {
      sort: jest.fn().mockReturnThis(),
      skip: jest.fn().mockReturnThis(),
      limit: jest.fn().mockReturnThis(),
      lean: jest.fn().mockResolvedValue(tasks),
    };

    Task.find.mockReturnValue(findChain);
    Task.countDocuments.mockResolvedValue(tasks.length);

    const response = await request(app)
      .get("/api/tasks")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");
    expect(response.body.data.tasks).toEqual(
      tasks.map((task) => ({ ...task, display_status: "pending" })),
    );
    expect(response.body.data.pagination.total).toBe(1);
    expect(Task.find).toHaveBeenCalledTimes(1);
    const query = Task.find.mock.calls[0][0];
    expect(query.owner_id).toBe(USER_ID);
    expect(query.is_deleted).toBe(false);
    expect(query.due_datetime).toBeDefined();
    expect(query.due_datetime.$gte).toBeInstanceOf(Date);
    expect(query.due_datetime.$lte).toBeUndefined();
  });

  test("GET /api/tasks?priority=high -> returns high priority upcoming tasks only", async () => {
    const tasks = [];
    const findChain = {
      sort: jest.fn().mockReturnThis(),
      skip: jest.fn().mockReturnThis(),
      limit: jest.fn().mockReturnThis(),
      lean: jest.fn().mockResolvedValue(tasks),
    };

    Task.find.mockReturnValue(findChain);
    Task.countDocuments.mockResolvedValue(0);

    const response = await request(app)
      .get("/api/tasks?priority=high")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(Task.find).toHaveBeenCalledTimes(1);
    const query = Task.find.mock.calls[0][0];
    expect(query.priority).toBe("high");
    expect(query.due_datetime).toBeDefined();
    expect(query.due_datetime.$gte).toBeInstanceOf(Date);
    expect(query.due_datetime.$lte).toBeUndefined();
  });

  test("GET /api/tasks?status=pending -> returns pending upcoming tasks only", async () => {
    const tasks = [];
    const findChain = {
      sort: jest.fn().mockReturnThis(),
      skip: jest.fn().mockReturnThis(),
      limit: jest.fn().mockReturnThis(),
      lean: jest.fn().mockResolvedValue(tasks),
    };

    Task.find.mockReturnValue(findChain);
    Task.countDocuments.mockResolvedValue(0);

    const response = await request(app)
      .get("/api/tasks?status=pending")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(Task.find).toHaveBeenCalledTimes(1);
    const query = Task.find.mock.calls[0][0];
    expect(query.status).toEqual({ $in: ["pending", "ongoing"] });
    expect(query.due_datetime).toBeDefined();
    expect(query.due_datetime.$gte).toBeInstanceOf(Date);
    expect(query.due_datetime.$lte).toBeUndefined();
  });

  test("GET /api/tasks excludes soft-deleted tasks from query", async () => {
    const tasks = [
      {
        _id: TASK_ID,
        title: "Physics quiz",
        status: "pending",
        priority: "medium",
        is_deleted: false,
      },
    ];

    const findChain = {
      sort: jest.fn().mockReturnThis(),
      skip: jest.fn().mockReturnThis(),
      limit: jest.fn().mockReturnThis(),
      lean: jest.fn().mockResolvedValue(tasks),
    };

    Task.find.mockReturnValue(findChain);
    Task.countDocuments.mockResolvedValue(tasks.length);

    const response = await request(app)
      .get("/api/tasks")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");
    expect(response.body.data.tasks).toEqual(
      tasks.map((task) => ({ ...task, display_status: "pending" })),
    );
    expect(Task.find).toHaveBeenCalledTimes(1);
    expect(Task.find).toHaveBeenCalledWith(
      expect.objectContaining({
        owner_id: USER_ID,
        is_deleted: false,
      }),
    );
  });

  test("GET /api/tasks?date uses user timezone day boundaries", async () => {
    User.findById.mockResolvedValue({
      _id: USER_ID,
      is_active: true,
      timezone: "Asia/Karachi",
      toPublicProfile: jest.fn(),
    });

    const tasks = [];
    const findChain = {
      sort: jest.fn().mockReturnThis(),
      skip: jest.fn().mockReturnThis(),
      limit: jest.fn().mockReturnThis(),
      lean: jest.fn().mockResolvedValue(tasks),
    };

    Task.find.mockReturnValue(findChain);
    Task.countDocuments.mockResolvedValue(0);

    const response = await request(app)
      .get("/api/tasks?date=2026-03-30")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(Task.find).toHaveBeenCalledTimes(1);

    const query = Task.find.mock.calls[0][0];
    expect(query.due_datetime.$gte.toISOString()).toBe("2026-03-29T19:00:00.000Z");
    expect(query.due_datetime.$lte.toISOString()).toBe("2026-03-30T18:59:59.999Z");
  });

  test("GET /api/tasks/:id -> returns single task", async () => {
    const task = {
      _id: TASK_ID,
      title: "Physics quiz",
      status: "pending",
    };

    Task.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue(task),
    });

    const response = await request(app)
      .get(`/api/tasks/${TASK_ID}`)
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");
    expect(response.body.data.task._id).toBe(TASK_ID);
  });

  test("PATCH /api/tasks/:id/status -> status updated", async () => {
    const existingTask = {
      _id: TASK_ID,
      title: "Physics quiz",
      status: "pending",
      priority: "medium",
      owner_id: USER_ID,
      created_at: new Date("2026-03-01T10:00:00.000Z"),
      due_datetime: new Date("2026-03-02T10:00:00.000Z"),
    };
    const updatedTask = {
      _id: TASK_ID,
      title: "Physics quiz",
      status: "complete",
      priority: "medium",
      owner_id: USER_ID,
      created_at: new Date("2026-03-01T10:00:00.000Z"),
      due_datetime: new Date("2026-03-02T10:00:00.000Z"),
      completed_at: new Date("2026-03-02T09:00:00.000Z"),
    };

    Task.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue(existingTask),
    });
    Task.findOneAndUpdate.mockReturnValue({
      lean: jest.fn().mockResolvedValue(updatedTask),
    });
    ActivityLog.create.mockResolvedValue({
      _id: "507f1f77bcf86cd799439099",
    });
    UserSetting.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({ behavioral_analytics_enabled: true }),
    });

    const response = await request(app)
      .patch(`/api/tasks/${TASK_ID}/status`)
      .set("Authorization", `Bearer ${makeToken()}`)
      .send({ status: "complete" });

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");
    expect(response.body.message).toBe("Task status updated");
    expect(response.body.data.task.status).toBe("complete");
    expect(ActivityLog.create).toHaveBeenCalledTimes(1);
    expect(ActivityLog.create.mock.calls[0][0]).toEqual(
      expect.objectContaining({
        user_id: USER_ID,
        task_id: TASK_ID,
        action_type: "task_completed",
      }),
    );
  });

  test("DELETE /api/tasks/:id -> soft deleted", async () => {
    Task.findOneAndUpdate.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: TASK_ID,
      }),
    });

    const response = await request(app)
      .delete(`/api/tasks/${TASK_ID}`)
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");
    expect(response.body.message).toBe("Task deleted");
    expect(response.body.data).toEqual({
      task_id: TASK_ID,
      is_deleted: true,
    });
  });
});

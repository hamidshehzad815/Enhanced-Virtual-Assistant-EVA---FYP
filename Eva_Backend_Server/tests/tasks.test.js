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
  Integration: {},
}));

const app = require("../app");
const { User, Task } = require("../models");

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

  test("GET /api/tasks -> returns task list", async () => {
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
    expect(response.body.data.tasks).toEqual(tasks);
    expect(response.body.data.pagination.total).toBe(1);
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
    const updatedTask = {
      _id: TASK_ID,
      title: "Physics quiz",
      status: "complete",
    };

    Task.findOneAndUpdate.mockReturnValue({
      lean: jest.fn().mockResolvedValue(updatedTask),
    });

    const response = await request(app)
      .patch(`/api/tasks/${TASK_ID}/status`)
      .set("Authorization", `Bearer ${makeToken()}`)
      .send({ status: "complete" });

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");
    expect(response.body.message).toBe("Task status updated");
    expect(response.body.data.task.status).toBe("complete");
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

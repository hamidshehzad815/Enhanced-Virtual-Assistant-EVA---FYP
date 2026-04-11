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
}));

jest.mock("../services/notification.service", () => ({
  insert_and_dispatch: jest.fn(),
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
const { User, ChatSession } = require("../models");
const { callAIServer } = require("../services/ai.service");
const { insert_and_dispatch } = require("../services/notification.service");

const USER_ID = "507f1f77bcf86cd799439011";
const SESSION_ID = "507f1f77bcf86cd799439013";

const makeToken = () =>
  jwt.sign({ userId: USER_ID }, process.env.JWT_ACCESS_SECRET, {
    expiresIn: "15m",
  });

describe("Chat API", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    User.findById.mockResolvedValue({
      _id: USER_ID,
      is_active: true,
      toPublicProfile: jest.fn(),
    });
  });

  test("POST /api/chat/session -> session created", async () => {
    ChatSession.create.mockResolvedValue({
      _id: SESSION_ID,
      user_id: USER_ID,
      title: "New chat",
    });

    const response = await request(app)
      .post("/api/chat/session")
      .set("Authorization", `Bearer ${makeToken()}`)
      .send({ title: "New chat" });

    expect(response.status).toBe(201);
    expect(response.body.status).toBe("success");
    expect(response.body.data.session_id).toBe(SESSION_ID);
  });

  test("POST /api/chat/process with valid message -> response_text returned", async () => {
    ChatSession.findOne.mockResolvedValue({
      _id: SESSION_ID,
      user_id: USER_ID,
      is_deleted: false,
    });

    callAIServer.mockResolvedValue({
      status: "ok",
      response_text: "Task added successfully.",
      handler_status: "success",
      route: {
        intent: "scheduling_add",
      },
      notifications: [],
    });

    insert_and_dispatch.mockResolvedValue({
      requested: 0,
      inserted: 0,
      dispatched_push: 0,
      dispatched_email: 0,
      failed: 0,
      results: [],
    });

    const response = await request(app)
      .post("/api/chat/process")
      .set("Authorization", `Bearer ${makeToken()}`)
      .send({
        message: "add physics quiz tomorrow 5pm",
        session_id: SESSION_ID,
        input_type: "text",
      });

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");
    expect(response.body.response_text).toBeTruthy();
    expect(response.body.response_text.length).toBeGreaterThan(0);
    expect(response.body.intent).toBe("scheduling_add");
  });

  test("POST /api/chat/process handles scheduling_update via same chat route", async () => {
    ChatSession.findOne.mockResolvedValue({
      _id: SESSION_ID,
      user_id: USER_ID,
      is_deleted: false,
    });

    callAIServer.mockResolvedValue({
      status: "ok",
      response_text: "Please confirm the update.",
      handler_status: "pending",
      route: {
        intent: "scheduling_update",
      },
      // Explicitly no notifications from AI side.
    });

    insert_and_dispatch.mockResolvedValue({
      requested: 0,
      inserted: 0,
      dispatched_push: 0,
      dispatched_email: 0,
      failed: 0,
      results: [],
    });

    const response = await request(app)
      .post("/api/chat/process")
      .set("Authorization", `Bearer ${makeToken()}`)
      .send({
        message: "change physics exam priority to high",
        session_id: SESSION_ID,
        input_type: "text",
      });

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");
    expect(response.body.intent).toBe("scheduling_update");
    expect(insert_and_dispatch).toHaveBeenCalledWith([]);
  });
});

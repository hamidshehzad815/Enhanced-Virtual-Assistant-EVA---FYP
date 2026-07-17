process.env.NODE_ENV = "test";
process.env.JWT_ACCESS_SECRET = process.env.JWT_ACCESS_SECRET || "test-access-secret";

const jwt = require("jsonwebtoken");
const mongoose = require("mongoose");
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
    find: jest.fn(),
    findOne: jest.fn(),
    findByIdAndUpdate: jest.fn(),
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

jest.mock("../services/chat.service", () => {
  const actual = jest.requireActual("../services/chat.service");
  return {
    ...actual,
    fetchSessionMessages: jest.fn(),
    saveConversationTurn: jest.fn().mockResolvedValue(undefined),
    softDeleteSession: jest.fn().mockResolvedValue(undefined),
  };
});

const app = require("../app");
const { User, ChatSession } = require("../models");
const chatService = require("../services/chat.service");
const { callAIServer } = require("../services/ai.service");
const { insert_and_dispatch } = require("../services/notification.service");

const USER_ID = "507f1f77bcf86cd799439011";
const SESSION_ID = "507f1f77bcf86cd799439013";

const makeToken = () =>
  jwt.sign({ userId: USER_ID }, process.env.JWT_ACCESS_SECRET, {
    expiresIn: "15m",
  });

const mockSessionDoc = (overrides = {}) => ({
  _id: SESSION_ID,
  user_id: USER_ID,
  title: "New chat",
  is_deleted: false,
  toObject() {
    return { ...this };
  },
  ...overrides,
});

describe("Chat API", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    User.findById.mockResolvedValue({
      _id: USER_ID,
      is_active: true,
      timezone: "UTC",
      toPublicProfile: jest.fn(),
    });
    insert_and_dispatch.mockResolvedValue({
      requested: 0,
      inserted: 0,
      dispatched_push: 0,
      dispatched_email: 0,
      failed: 0,
      results: [],
    });
    ChatSession.findByIdAndUpdate.mockResolvedValue({});
  });

  test("GET /api/chat/sessions -> only sessions with messages", async () => {
    ChatSession.find.mockReturnValue({
      sort: jest.fn().mockReturnValue({
        limit: jest.fn().mockReturnValue({
          lean: jest.fn().mockResolvedValue([
            {
              _id: SESSION_ID,
              title: "Physics quiz",
              last_message_preview: "Task added successfully.",
              last_message_at: new Date("2026-07-10T10:00:00.000Z"),
              created_at: new Date("2026-07-10T09:00:00.000Z"),
              updated_at: new Date("2026-07-10T10:00:00.000Z"),
            },
          ]),
        }),
      }),
    });

    const response = await request(app)
      .get("/api/chat/sessions")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.data.sessions).toHaveLength(1);
    expect(response.body.data.sessions[0].id).toBe(SESSION_ID);
    expect(ChatSession.find).toHaveBeenCalledWith({
      user_id: USER_ID,
      is_deleted: false,
      last_message_at: { $ne: null },
    });
  });

  test("GET /api/chat/sessions/:sessionId/messages -> history returned in user-then-eva order", async () => {
    ChatSession.findOne.mockResolvedValue(mockSessionDoc({ title: "Physics quiz" }));
    chatService.fetchSessionMessages.mockResolvedValue([
      {
        _id: "507f1f77bcf86cd799439015",
        role: "user",
        content: "add physics quiz tomorrow 5pm",
        input_type: "text",
        intent: "scheduling_add",
        status: "processed",
        created_at: new Date("2026-07-10T10:00:00.000Z"),
      },
      {
        _id: "507f1f77bcf86cd799439014",
        role: "eva",
        content: "Task added successfully.",
        input_type: "text",
        intent: "scheduling_add",
        status: "processed",
        created_at: new Date("2026-07-10T10:00:00.000Z"),
      },
    ]);

    const response = await request(app)
      .get(`/api/chat/sessions/${SESSION_ID}/messages`)
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.data.session_id).toBe(SESSION_ID);
    expect(response.body.data.messages).toHaveLength(2);
    expect(response.body.data.messages[0].role).toBe("user");
    expect(response.body.data.messages[1].role).toBe("eva");
    expect(chatService.fetchSessionMessages).toHaveBeenCalledWith(
      SESSION_ID,
      100,
    );
  });

  test("sortConversationMessages keeps user before eva when timestamps match", () => {
    const { sortConversationMessages } = jest.requireActual("../services/chat.service");
    const sameTime = new Date("2026-07-11T09:48:45.000Z");

    const sorted = sortConversationMessages([
      {
        _id: "b",
        role: "eva",
        content: "reply",
        created_at: sameTime,
      },
      {
        _id: "a",
        role: "user",
        content: "hello",
        created_at: sameTime,
      },
    ]);

    expect(sorted[0].role).toBe("user");
    expect(sorted[1].role).toBe("eva");
  });

  test("DELETE /api/chat/sessions/:sessionId -> soft deletes session", async () => {
    ChatSession.findOne.mockResolvedValue(mockSessionDoc({ title: "Physics quiz" }));

    const response = await request(app)
      .delete(`/api/chat/sessions/${SESSION_ID}`)
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");
    expect(response.body.data.session_id).toBe(SESSION_ID);
    expect(chatService.softDeleteSession).toHaveBeenCalled();
  });

  test("POST /api/chat/process with valid message -> response_text returned", async () => {
    ChatSession.findOne.mockResolvedValue(mockSessionDoc());

    callAIServer.mockResolvedValue({
      status: "ok",
      response_text: "Task added successfully.",
      handler_status: "success",
      route: {
        intent: "scheduling_add",
      },
      notifications: [],
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
    expect(response.body.intent).toBe("scheduling_add");
    expect(response.body.session_created).toBe(false);
    expect(response.body.data).toBeUndefined();
    expect(ChatSession.findByIdAndUpdate).toHaveBeenCalled();
    expect(chatService.saveConversationTurn).toHaveBeenCalledWith(
      SESSION_ID,
      expect.objectContaining({
        userMessage: "add physics quiz tomorrow 5pm",
        responseText: "Task added successfully.",
      }),
    );
  });

  test("POST /api/chat/process learning_create -> includes See roadmap action", async () => {
    ChatSession.findOne.mockResolvedValue(mockSessionDoc());

    callAIServer.mockResolvedValue({
      status: "ok",
      response_text: "Your Python plan is ready.",
      handler_status: "success",
      route: {
        intent: "learning_create",
        learning_goal_id: "507f1f77bcf86cd799439099",
      },
      notifications: [],
    });

    const response = await request(app)
      .post("/api/chat/process")
      .set("Authorization", `Bearer ${makeToken()}`)
      .send({
        message: "create python roadmap from monday",
        session_id: SESSION_ID,
        input_type: "text",
      });

    expect(response.status).toBe(200);
    expect(response.body.action).toEqual({
      type: "see_roadmap",
      id: "507f1f77bcf86cd799439099",
      label: "See roadmap",
    });
    expect(chatService.saveConversationTurn).toHaveBeenCalledWith(
      SESSION_ID,
      expect.objectContaining({
        action: {
          type: "see_roadmap",
          id: "507f1f77bcf86cd799439099",
          label: "See roadmap",
        },
      }),
    );
  });

  test("POST /api/chat/process without session_id -> creates session on first message", async () => {
    ChatSession.create.mockResolvedValue(mockSessionDoc());

    callAIServer.mockResolvedValue({
      status: "ok",
      response_text: "Task added successfully.",
      handler_status: "success",
      route: {
        intent: "scheduling_add",
      },
      notifications: [],
    });

    const response = await request(app)
      .post("/api/chat/process")
      .set("Authorization", `Bearer ${makeToken()}`)
      .send({
        message: "add physics quiz tomorrow 5pm",
        input_type: "text",
      });

    expect(response.status).toBe(200);
    expect(response.body.session_id).toBe(SESSION_ID);
    expect(response.body.session_created).toBe(true);
    expect(ChatSession.create).toHaveBeenCalled();
    expect(callAIServer).toHaveBeenCalledWith(
      expect.objectContaining({
        session_id: SESSION_ID,
        message: "add physics quiz tomorrow 5pm",
      }),
    );
  });

  test("POST /api/chat/process handles scheduling_update via same chat route", async () => {
    ChatSession.findOne.mockResolvedValue(mockSessionDoc());

    callAIServer.mockResolvedValue({
      status: "ok",
      response_text: "Please confirm the update.",
      handler_status: "pending",
      route: {
        intent: "scheduling_update",
      },
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

  test("POST /api/chat/process handles behavioral intent via same chat route", async () => {
    ChatSession.findOne.mockResolvedValue(mockSessionDoc());

    callAIServer.mockResolvedValue({
      status: "ok",
      response_text: "Your peak hours are 6PM and 10AM.",
      handler_status: "success",
      route: {
        intent: "behavioral",
      },
      notifications: [],
    });

    const response = await request(app)
      .post("/api/chat/process")
      .set("Authorization", `Bearer ${makeToken()}`)
      .send({
        message: "when am i most productive",
        session_id: SESSION_ID,
        input_type: "text",
      });

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");
    expect(response.body.intent).toBe("behavioral");
    expect(response.body.ai_status).toBe("success");
    expect(insert_and_dispatch).toHaveBeenCalledWith([]);
  });
});

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

jest.mock("../services/notification.service", () => ({
  insert_and_dispatch: jest.fn().mockResolvedValue({ sent: 1, skipped: 0 }),
}));

jest.mock("../config/logger", () => ({
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
  debug: jest.fn(),
  http: jest.fn(),
  add: jest.fn(),
  stream: { write: jest.fn() },
}));

jest.mock("../models", () => ({
  User: {
    findOne: jest.fn(),
    find: jest.fn(),
    findById: jest.fn(),
  },
  UserSetting: {
    findOne: jest.fn(),
    find: jest.fn(),
  },
  Friend: {
    buildPairKey: jest.fn((a, b) => [String(a), String(b)].sort().join(":")),
    findOne: jest.fn(),
    create: jest.fn(),
    find: jest.fn(),
    findById: jest.fn(),
  },
  ChatSession: {},
  ConversationHistory: {},
  Notification: {},
  ActivityLog: {},
  Integration: {},
  Task: {},
  LearningGoal: {},
}));

const app = require("../app");
const { User, UserSetting, Friend } = require("../models");

const REQUESTER_ID = "507f1f77bcf86cd799439011";
const TARGET_ID = "507f1f77bcf86cd799439022";

const makeToken = () =>
  jwt.sign({ userId: REQUESTER_ID }, process.env.JWT_ACCESS_SECRET, {
    expiresIn: "15m",
  });

const authHeaders = () => ({
  Authorization: `Bearer ${makeToken()}`,
});

describe("POST /api/friends/request allow_friend_requests", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    User.findById.mockResolvedValue({
      _id: REQUESTER_ID,
      is_active: true,
      timezone: "UTC",
    });
    User.findOne.mockResolvedValue({
      _id: TARGET_ID,
      username: "targetuser",
      is_active: true,
    });
    Friend.findOne.mockResolvedValue(null);
  });

  test("returns 403 when target has allow_friend_requests nobody", async () => {
    UserSetting.findOne.mockReturnValue({
      select: jest.fn().mockReturnValue({
        lean: jest.fn().mockResolvedValue({ allow_friend_requests: "nobody" }),
      }),
    });

    const response = await request(app)
      .post("/api/friends/request")
      .set(authHeaders())
      .send({ username: "targetuser" });

    expect(response.status).toBe(403);
    expect(response.body.message).toBe("This user is not accepting friend requests");
    expect(Friend.create).not.toHaveBeenCalled();
  });

  test("allows request when target accepts everyone", async () => {
    UserSetting.findOne.mockReturnValue({
      select: jest.fn().mockReturnValue({
        lean: jest.fn().mockResolvedValue({ allow_friend_requests: "everyone" }),
      }),
    });
    Friend.create.mockResolvedValue({
      _id: "507f1f77bcf86cd799439099",
      requester_id: REQUESTER_ID,
      recipient_id: TARGET_ID,
      status: "pending",
    });
    Friend.findById.mockReturnValue({
      populate: jest.fn().mockReturnThis(),
      lean: jest.fn().mockResolvedValue({
        _id: "507f1f77bcf86cd799439099",
        requester_id: {
          _id: REQUESTER_ID,
          name: "Ali",
          username: "ali",
        },
        recipient_id: {
          _id: TARGET_ID,
          name: "Target",
          username: "targetuser",
        },
        status: "pending",
      }),
    });

    const response = await request(app)
      .post("/api/friends/request")
      .set(authHeaders())
      .send({ username: "targetuser" });

    expect(response.status).toBe(201);
    expect(Friend.create).toHaveBeenCalled();
  });
});

describe("GET /api/friends/search allow_friend_requests", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    User.findById.mockResolvedValue({
      _id: REQUESTER_ID,
      is_active: true,
      timezone: "UTC",
    });
    Friend.find.mockReturnValue({
      select: jest.fn().mockReturnValue({
        lean: jest.fn().mockResolvedValue([]),
      }),
    });
  });

  test("hides users with allow_friend_requests nobody", async () => {
    User.find.mockReturnValue({
      select: jest.fn().mockReturnValue({
        sort: jest.fn().mockReturnValue({
          limit: jest.fn().mockReturnValue({
            lean: jest.fn().mockResolvedValue([
              {
                _id: TARGET_ID,
                name: "Closed User",
                username: "closeduser",
                email: "closed@example.com",
              },
              {
                _id: "507f1f77bcf86cd799439033",
                name: "Open User",
                username: "openuser",
                email: "open@example.com",
              },
            ]),
          }),
        }),
      }),
    });
    UserSetting.find.mockReturnValue({
      select: jest.fn().mockReturnValue({
        lean: jest.fn().mockResolvedValue([{ user_id: TARGET_ID }]),
      }),
    });

    const response = await request(app)
      .get("/api/friends/search")
      .query({ q: "user" })
      .set(authHeaders());

    expect(response.status).toBe(200);
    expect(response.body.data.users).toHaveLength(1);
    expect(response.body.data.users[0].username).toBe("openuser");
  });
});

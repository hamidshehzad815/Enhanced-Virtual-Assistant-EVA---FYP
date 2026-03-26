process.env.NODE_ENV = "test";
process.env.JWT_ACCESS_SECRET = process.env.JWT_ACCESS_SECRET || "test-access-secret";
process.env.JWT_REFRESH_SECRET =
  process.env.JWT_REFRESH_SECRET || "test-refresh-secret";
process.env.JWT_ACCESS_EXPIRES = process.env.JWT_ACCESS_EXPIRES || "15m";
process.env.JWT_REFRESH_EXPIRES = process.env.JWT_REFRESH_EXPIRES || "7d";

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

jest.mock("../services/email.service", () => ({
  sendVerificationEmail: jest.fn(),
}));

jest.mock("../models", () => ({
  User: {
    findOne: jest.fn(),
    create: jest.fn(),
    findById: jest.fn(),
  },
  UserSetting: {
    createDefaultSettings: jest.fn(),
    findOne: jest.fn(),
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
const { User, UserSetting } = require("../models");
const { sendVerificationEmail } = require("../services/email.service");

const USER_ID = "507f1f77bcf86cd799439011";

describe("Auth API", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("POST /api/auth/register -> 201 and user data", async () => {
    const publicProfile = {
      _id: USER_ID,
      name: "Hamid",
      username: "hamid",
      email: "hamid@example.com",
    };

    const createdUser = {
      _id: USER_ID,
      email: "hamid@example.com",
      name: "Hamid",
      toPublicProfile: jest.fn().mockReturnValue(publicProfile),
    };

    User.findOne.mockResolvedValueOnce(null).mockResolvedValueOnce(null);
    User.create.mockResolvedValue(createdUser);
    UserSetting.createDefaultSettings.mockResolvedValue({
      _id: "507f1f77bcf86cd799439099",
    });
    sendVerificationEmail.mockResolvedValue(true);

    const response = await request(app).post("/api/auth/register").send({
      name: "Hamid",
      username: "hamid",
      email: "hamid@example.com",
      password: "secret123",
      timezone: "Asia/Karachi",
    });

    expect(response.status).toBe(201);
    expect(response.body.status).toBe("success");
    expect(response.body.data.user).toEqual(publicProfile);
    expect(UserSetting.createDefaultSettings).toHaveBeenCalledWith(USER_ID);
    expect(sendVerificationEmail).toHaveBeenCalledTimes(1);
  });

  test("POST /api/auth/login -> 200 and tokens", async () => {
    const loginUser = {
      _id: USER_ID,
      email: "hamid@example.com",
      is_active: true,
      is_verified: true,
      password_hash: "hashed-password",
      comparePassword: jest.fn().mockResolvedValue(true),
      setRefreshToken: jest.fn().mockResolvedValue(),
      updateLastLogin: jest.fn().mockResolvedValue(),
      toPublicProfile: jest.fn().mockReturnValue({
        _id: USER_ID,
        name: "Hamid",
        username: "hamid",
        email: "hamid@example.com",
      }),
    };

    const select = jest.fn().mockResolvedValue(loginUser);
    User.findOne.mockReturnValue({ select });

    const response = await request(app).post("/api/auth/login").send({
      email: "hamid@example.com",
      password: "secret123",
    });

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");
    expect(response.body.data.tokens.access_token).toBeTruthy();
    expect(response.body.data.tokens.refresh_token).toBeTruthy();
    expect(loginUser.comparePassword).toHaveBeenCalledWith("secret123");
    expect(loginUser.setRefreshToken).toHaveBeenCalledTimes(1);
    expect(loginUser.updateLastLogin).toHaveBeenCalledTimes(1);
  });

  test("GET /api/auth/me with valid token -> 200", async () => {
    const authUser = {
      _id: USER_ID,
      is_active: true,
      toPublicProfile: jest.fn().mockReturnValue({
        _id: USER_ID,
        name: "Hamid",
        username: "hamid",
        email: "hamid@example.com",
      }),
    };

    User.findById.mockResolvedValue(authUser);
    UserSetting.findOne.mockResolvedValue({
      theme: "light",
      notifications_enabled: true,
    });

    const token = jwt.sign(
      { userId: USER_ID },
      process.env.JWT_ACCESS_SECRET,
      { expiresIn: "15m" },
    );

    const response = await request(app)
      .get("/api/auth/me")
      .set("Authorization", `Bearer ${token}`);

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");
    expect(response.body.data.user._id).toBe(USER_ID);
    expect(response.body.data.settings.theme).toBe("light");
  });

  test("GET /api/auth/me without token -> 401", async () => {
    const response = await request(app).get("/api/auth/me");

    expect(response.status).toBe(401);
    expect(response.body.status).toBe("fail");
    expect(response.body.message).toBe("Access token required");
  });
});

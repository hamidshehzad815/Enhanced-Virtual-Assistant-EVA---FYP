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
  stream: { write: jest.fn() },
}));

const mockFindById = jest.fn();
const mockSoftDeleteUserAccount = jest.fn();

jest.mock("../models", () => ({
  User: {
    findById: (...args) => mockFindById(...args),
  },
}));

jest.mock("../services/accountDelete.service", () => ({
  softDeleteUserAccount: (...args) => mockSoftDeleteUserAccount(...args),
}));

const app = require("../app");

const USER_ID = "507f1f77bcf86cd799439011";

const makeToken = () =>
  jwt.sign({ userId: USER_ID }, process.env.JWT_ACCESS_SECRET, {
    expiresIn: "15m",
  });

const authHeaders = () => ({
  Authorization: `Bearer ${makeToken()}`,
});

const mockUserDoc = (overrides = {}) => ({
  _id: USER_ID,
  name: "Hamid",
  username: "hamid",
  email: "hamid@example.com",
  profile_picture: null,
  timezone: "UTC",
  is_verified: true,
  is_active: true,
  toPublicProfile() {
    return {
      _id: this._id,
      name: this.name,
      username: this.username,
      email: this.email,
      profile_picture: this.profile_picture,
      timezone: this.timezone,
      is_verified: this.is_verified,
    };
  },
  ...overrides,
});

describe("DELETE /api/profile/account", () => {
  const setupAuthUser = (userOverrides = {}) => {
    const user = mockUserDoc({ is_active: true, ...userOverrides });
    mockFindById
      .mockResolvedValueOnce(user)
      .mockImplementationOnce(() => ({
        select: jest.fn().mockResolvedValue(user),
      }));
    return user;
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockSoftDeleteUserAccount.mockResolvedValue(undefined);
  });

  test("returns 401 without token", async () => {
    const response = await request(app).delete("/api/profile/account");

    expect(response.status).toBe(401);
    expect(mockSoftDeleteUserAccount).not.toHaveBeenCalled();
  });

  test("local user requires password", async () => {
    setupAuthUser({
      password_hash: "hashed",
      comparePassword: jest.fn(),
    });

    const response = await request(app)
      .delete("/api/profile/account")
      .set(authHeaders())
      .send({});

    expect(response.status).toBe(400);
    expect(response.body.message).toMatch(/password is required/i);
    expect(mockSoftDeleteUserAccount).not.toHaveBeenCalled();
  });

  test("local user rejects invalid password", async () => {
    const comparePassword = jest.fn().mockResolvedValue(false);
    setupAuthUser({
      password_hash: "hashed",
      comparePassword,
    });

    const response = await request(app)
      .delete("/api/profile/account")
      .set(authHeaders())
      .send({ password: "wrong" });

    expect(response.status).toBe(401);
    expect(response.body.message).toBe("Invalid password");
    expect(comparePassword).toHaveBeenCalledWith("wrong");
    expect(mockSoftDeleteUserAccount).not.toHaveBeenCalled();
  });

  test("local user deletes account with valid password", async () => {
    const userDoc = setupAuthUser({
      password_hash: "hashed",
      comparePassword: jest.fn().mockResolvedValue(true),
    });

    const response = await request(app)
      .delete("/api/profile/account")
      .set(authHeaders())
      .send({ password: "secret123" });

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");
    expect(response.body.message).toMatch(/deleted successfully/i);
    expect(mockSoftDeleteUserAccount).toHaveBeenCalledWith(userDoc);
  });

  test("google-only user deletes without password", async () => {
    const userDoc = setupAuthUser({
      password_hash: null,
    });

    const response = await request(app)
      .delete("/api/profile/account")
      .set(authHeaders())
      .send({});

    expect(response.status).toBe(200);
    expect(mockSoftDeleteUserAccount).toHaveBeenCalledWith(userDoc);
  });
});

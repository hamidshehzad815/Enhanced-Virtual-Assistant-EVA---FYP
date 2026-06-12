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
const mockFindByIdAndUpdate = jest.fn();
const mockFindOne = jest.fn();

jest.mock("../models", () => ({
  User: {
    findById: (...args) => mockFindById(...args),
    findByIdAndUpdate: (...args) => mockFindByIdAndUpdate(...args),
    findOne: (...args) => mockFindOne(...args),
  },
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

describe("PATCH /api/profile", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFindById.mockResolvedValue(mockUserDoc({ is_active: true }));
  });

  test("rejects profile_picture field", async () => {
    const response = await request(app)
      .patch("/api/profile")
      .set(authHeaders())
      .send({ profile_picture: "https://evil.com/avatar.jpg" });

    expect(response.status).toBe(400);
    expect(response.body.message).toMatch(/Invalid profile fields/i);
    expect(mockFindByIdAndUpdate).not.toHaveBeenCalled();
  });

  test("rejects removed fields such as bio", async () => {
    const response = await request(app)
      .patch("/api/profile")
      .set(authHeaders())
      .send({ bio: "Updated bio" });

    expect(response.status).toBe(400);
    expect(response.body.message).toMatch(/Invalid profile fields/i);
    expect(mockFindByIdAndUpdate).not.toHaveBeenCalled();
  });

  test("updates allowed fields such as name", async () => {
    const updatedUser = mockUserDoc({ name: "Updated Name" });
    mockFindByIdAndUpdate.mockResolvedValue(updatedUser);

    const response = await request(app)
      .patch("/api/profile")
      .set(authHeaders())
      .send({ name: "Updated Name" });

    expect(response.status).toBe(200);
    expect(response.body.data.user.name).toBe("Updated Name");
    expect(mockFindByIdAndUpdate).toHaveBeenCalledWith(
      USER_ID,
      { $set: { name: "Updated Name" } },
      expect.objectContaining({ new: true }),
    );
  });
});

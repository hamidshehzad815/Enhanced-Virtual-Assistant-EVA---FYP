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

const mockFindOneAndUpdate = jest.fn();
const mockFindOne = jest.fn();
const mockUpdateOne = jest.fn();
const mockUserSettingUpdate = jest.fn();

jest.mock("../models", () => ({
  User: {
    findById: jest.fn(),
  },
  UserSetting: {
    findOne: jest.fn(),
    findOneAndUpdate: (...args) => mockUserSettingUpdate(...args),
    createDefaultSettings: jest.fn(),
  },
  Task: {
    find: jest.fn(),
    countDocuments: jest.fn(),
    findOne: jest.fn(),
    findOneAndUpdate: jest.fn(),
  },
  Integration: {
    findOneAndUpdate: (...args) => mockFindOneAndUpdate(...args),
    findOne: (...args) => mockFindOne(...args),
    updateOne: (...args) => mockUpdateOne(...args),
    find: jest.fn(),
  },
  ChatSession: {},
  ConversationHistory: {},
  Notification: {},
  ActivityLog: {},
  LearningGoal: {},
}));

jest.mock("../utils/googleCalendarSync", () => ({
  resolveGoogleCalendarSync: jest.fn(),
}));

jest.mock("../services/googleCalendar.service", () => ({
  deleteEvent: jest.fn(),
}));

const app = require("../app");
const { User } = require("../models");

const USER_ID = "507f1f77bcf86cd799439011";

const makeToken = () =>
  jwt.sign({ userId: USER_ID }, process.env.JWT_ACCESS_SECRET, {
    expiresIn: "15m",
  });

describe("Integrations API", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    User.findById.mockResolvedValue({
      _id: USER_ID,
      is_active: true,
      timezone: "UTC",
      toPublicProfile: jest.fn(),
    });
  });

  test("POST /api/integrations/google/connect enables sync toggle", async () => {
    mockFindOneAndUpdate.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: "int1",
        user_id: USER_ID,
        provider: "google_calendar",
        calendar_id: "primary",
        is_active: true,
        created_at: new Date(),
        updated_at: new Date(),
      }),
    });
    mockUserSettingUpdate.mockResolvedValue({});

    const response = await request(app)
      .post("/api/integrations/google/connect")
      .set("Authorization", `Bearer ${makeToken()}`)
      .send({
        access_token: "access-token",
        refresh_token: "refresh-token",
        calendar_id: "primary",
      });

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("success");
    expect(response.body.data.google_calendar_sync_enabled).toBe(true);
    expect(mockUserSettingUpdate).toHaveBeenCalledWith(
      { user_id: USER_ID },
      expect.objectContaining({
        $set: expect.objectContaining({ google_calendar_sync_enabled: true }),
      }),
    );
  });

  test("DELETE /api/integrations/google disconnects and disables sync", async () => {
    mockFindOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: "int1",
        user_id: USER_ID,
        provider: "google_calendar",
        is_active: true,
      }),
    });
    mockUpdateOne.mockResolvedValue({ matchedCount: 1 });
    mockUserSettingUpdate.mockResolvedValue({});

    const response = await request(app)
      .delete("/api/integrations/google")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(response.status).toBe(200);
    expect(response.body.data.google_calendar_sync_enabled).toBe(false);
    expect(response.body.data.is_active).toBe(false);
    expect(mockUserSettingUpdate).toHaveBeenCalledWith(
      { user_id: USER_ID },
      expect.objectContaining({
        $set: expect.objectContaining({ google_calendar_sync_enabled: false }),
      }),
    );
  });
});

process.env.NODE_ENV = "test";

jest.mock("../config/logger", () => ({
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
  debug: jest.fn(),
}));

jest.mock("../utils/googleCalendarSync", () => ({
  resolveGoogleCalendarSync: jest.fn(),
}));

jest.mock("../services/googleCalendar.service", () => ({
  createEvent: jest.fn(),
  updateEvent: jest.fn(),
}));

const { Task, User, UserSetting, Integration } = require("../models");

jest.mock("../models", () => ({
  Task: {
    find: jest.fn(),
    updateOne: jest.fn(),
  },
  User: {
    findById: jest.fn(),
  },
  UserSetting: {
    findOne: jest.fn(),
  },
  Integration: {
    updateOne: jest.fn(),
  },
}));

const { resolveGoogleCalendarSync } = require("../utils/googleCalendarSync");
const { createEvent, updateEvent } = require("../services/googleCalendar.service");
const {
  backfillUserTasksToGoogleCalendar,
  scheduleGoogleCalendarBackfill,
} = require("../services/googleCalendarBackfill.service");

const USER_ID = "507f1f77bcf86cd799439011";

describe("googleCalendarBackfill.service", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    UserSetting.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({ google_calendar_sync_enabled: true }),
    });
    User.findById.mockReturnValue({
      select: jest.fn().mockReturnValue({
        lean: jest.fn().mockResolvedValue({ timezone: "Asia/Karachi" }),
      }),
    });
    Integration.updateOne.mockResolvedValue({ matchedCount: 1 });
  });

  test("skips when Google Calendar is not configured", async () => {
    resolveGoogleCalendarSync.mockResolvedValue(null);

    const result = await backfillUserTasksToGoogleCalendar(USER_ID);

    expect(result.skipped).toBe(true);
    expect(Task.find).not.toHaveBeenCalled();
  });

  test("creates events for tasks without google_calendar_event_id", async () => {
    resolveGoogleCalendarSync.mockResolvedValue({
      _id: "int1",
      access_token: "access",
      calendar_id: "primary",
    });
    Task.find.mockReturnValue({
      select: jest.fn().mockReturnValue({
        sort: jest.fn().mockReturnValue({
          lean: jest.fn().mockResolvedValue([
            {
              _id: "task1",
              title: "Physics exam",
              due_datetime: new Date("2026-07-13T15:00:00.000Z"),
              duration: 120,
              priority: "high",
              google_calendar_event_id: null,
            },
          ]),
        }),
      }),
    });
    createEvent.mockResolvedValue("evt_new");
    Task.updateOne.mockResolvedValue({ matchedCount: 1 });

    const result = await backfillUserTasksToGoogleCalendar(USER_ID);

    expect(result).toEqual({
      skipped: false,
      total: 1,
      created: 1,
      updated: 0,
      failed: 0,
    });
    expect(createEvent).toHaveBeenCalledTimes(1);
    expect(Task.updateOne).toHaveBeenCalledWith(
      { _id: "task1", owner_id: USER_ID },
      { $set: { google_calendar_event_id: "evt_new" } },
    );
  });

  test("updates events for tasks that already have google_calendar_event_id", async () => {
    resolveGoogleCalendarSync.mockResolvedValue({
      _id: "int1",
      access_token: "access",
      calendar_id: "primary",
    });
    Task.find.mockReturnValue({
      select: jest.fn().mockReturnValue({
        sort: jest.fn().mockReturnValue({
          lean: jest.fn().mockResolvedValue([
            {
              _id: "task2",
              title: "Chemistry exam",
              due_datetime: new Date("2026-07-14T15:00:00.000Z"),
              duration: 90,
              priority: "medium",
              google_calendar_event_id: "evt_existing",
            },
          ]),
        }),
      }),
    });
    updateEvent.mockResolvedValue(true);

    const result = await backfillUserTasksToGoogleCalendar(USER_ID);

    expect(result).toEqual({
      skipped: false,
      total: 1,
      created: 0,
      updated: 1,
      failed: 0,
    });
    expect(updateEvent).toHaveBeenCalledTimes(1);
    expect(createEvent).not.toHaveBeenCalled();
  });

  test("scheduleGoogleCalendarBackfill runs asynchronously", async () => {
    resolveGoogleCalendarSync.mockResolvedValue(null);

    await new Promise((resolve) => {
      scheduleGoogleCalendarBackfill(USER_ID);
      setImmediate(resolve);
    });

    expect(UserSetting.findOne).toHaveBeenCalledWith({ user_id: USER_ID });
  });
});

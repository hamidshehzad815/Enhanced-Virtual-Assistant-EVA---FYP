process.env.NODE_ENV = "test";

jest.mock("../config/logger", () => ({
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
  debug: jest.fn(),
}));

jest.mock("../models", () => ({
  Notification: {
    create: jest.fn(),
  },
  User: {
    findById: jest.fn(),
    updateOne: jest.fn(),
  },
  UserSetting: {
    findOne: jest.fn(),
  },
}));

const mongoose = require("mongoose");
const { Notification, User, UserSetting } = require("../models");
const {
  insert_and_dispatch,
  isMasterNotificationsEnabled,
  isPushEnabled,
  isEmailEnabled,
} = require("../services/notification.service");

const buildSavedNotification = (overrides = {}) => {
  const doc = {
    _id: new mongoose.Types.ObjectId(),
    user_id: overrides.user_id || new mongoose.Types.ObjectId(),
    type: overrides.type || "task_reminder",
    title: "Reminder",
    message: "Task due soon",
    delivery_channel: overrides.delivery_channel || ["in_app", "push", "email"],
    save: jest.fn().mockResolvedValue(true),
    ...overrides,
  };
  return doc;
};

describe("Notification Service", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    UserSetting.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        notifications_enabled: true,
        push_notifications_enabled: true,
        email_notifications_enabled: true,
      }),
    });
    User.findById.mockReturnValue({
      select: jest.fn().mockReturnValue({
        lean: jest.fn().mockResolvedValue({
          _id: new mongoose.Types.ObjectId(),
          name: "User",
          email: "user@example.com",
          push_tokens: [],
        }),
      }),
    });
  });

  test("insert_and_dispatch returns zero-summary for empty array", async () => {
    const result = await insert_and_dispatch([]);

    expect(result).toEqual({
      requested: 0,
      inserted: 0,
      dispatched_push: 0,
      dispatched_email: 0,
      skipped: 0,
      failed: 0,
      results: [],
    });
    expect(Notification.create).not.toHaveBeenCalled();
  });

  test("insert_and_dispatch returns zero-summary for non-array input", async () => {
    const result = await insert_and_dispatch(null);

    expect(result.skipped).toBe(0);
    expect(result.inserted).toBe(0);
    expect(Notification.create).not.toHaveBeenCalled();
  });

  test("skips notification when notifications_enabled is false", async () => {
    UserSetting.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        notifications_enabled: false,
        push_notifications_enabled: true,
        email_notifications_enabled: true,
      }),
    });

    const recipientId = new mongoose.Types.ObjectId();
    const result = await insert_and_dispatch([
      {
        user_id: String(recipientId),
        type: "task_reminder",
        title: "Reminder",
        message: "Due soon",
        delivery_channel: ["in_app", "push"],
      },
    ]);

    expect(result.requested).toBe(1);
    expect(result.skipped).toBe(1);
    expect(result.inserted).toBe(0);
    expect(Notification.create).not.toHaveBeenCalled();
    expect(result.results[0]).toMatchObject({
      skipped: true,
      reason: "User notifications disabled",
    });
  });

  test("inserts in_app and sets sent_at when only in_app channel requested", async () => {
    const recipientId = new mongoose.Types.ObjectId();
    const savedDoc = buildSavedNotification({
      user_id: recipientId,
      delivery_channel: ["in_app"],
    });
    Notification.create.mockResolvedValue(savedDoc);

    const result = await insert_and_dispatch([
      {
        user_id: String(recipientId),
        type: "learning_goal_deleted",
        title: "Shared learning plan removed",
        message: "Ali removed python basics from their plan.",
        delivery_channel: ["in_app"],
      },
    ]);

    expect(result.inserted).toBe(1);
    expect(result.failed).toBe(0);
    expect(Notification.create).toHaveBeenCalledTimes(1);
    expect(savedDoc.save).toHaveBeenCalled();
    expect(savedDoc.sent_at).toBeInstanceOf(Date);
  });

  test("does not set sent_at when push/email fail and in_app not in channels", async () => {
    const recipientId = new mongoose.Types.ObjectId();
    const savedDoc = buildSavedNotification({
      user_id: recipientId,
      delivery_channel: ["push", "email"],
    });
    Notification.create.mockResolvedValue(savedDoc);

    await insert_and_dispatch([
      {
        user_id: String(recipientId),
        type: "task_reminder",
        title: "Reminder",
        message: "Due soon",
        delivery_channel: ["push", "email"],
      },
    ]);

    expect(savedDoc.save).not.toHaveBeenCalled();
    expect(savedDoc.sent_at).toBeUndefined();
  });

  test("isEmailEnabled respects the email toggle for ALL types, including invites", () => {
    // Email OFF (master on): nothing emails — collaboration invites no longer
    // override the user's choice (issue #29).
    const emailOff = {
      notifications_enabled: true,
      email_notifications_enabled: false,
    };
    expect(isEmailEnabled(emailOff, "collaboration_invite")).toBe(false);
    expect(isEmailEnabled(emailOff, "learning_collaboration_invite")).toBe(false);
    expect(isEmailEnabled(emailOff, "task_reminder")).toBe(false);

    // Email ON: every type may email, including invites.
    const emailOn = {
      notifications_enabled: true,
      email_notifications_enabled: true,
    };
    expect(isEmailEnabled(emailOn, "collaboration_invite")).toBe(true);
    expect(isEmailEnabled(emailOn, "task_reminder")).toBe(true);
  });

  test("preference helpers respect master switch", () => {
    const disabled = { notifications_enabled: false };
    expect(isMasterNotificationsEnabled(disabled)).toBe(false);
    expect(isPushEnabled(disabled)).toBe(false);
    expect(isEmailEnabled(disabled, "collaboration_invite")).toBe(false);
  });
});

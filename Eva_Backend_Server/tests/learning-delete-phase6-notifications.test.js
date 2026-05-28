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
const { insert_and_dispatch } = require("../services/notification.service");

describe("learning delete phase 6 — notifications", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    UserSetting.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        push_notifications_enabled: true,
        email_notifications_enabled: false,
      }),
    });
    User.findById.mockReturnValue({
      select: jest.fn().mockReturnValue({
        lean: jest.fn().mockResolvedValue({
          _id: new mongoose.Types.ObjectId(),
          name: "Collaborator",
          email: "c@example.com",
          push_tokens: [],
        }),
      }),
    });
  });

  test("insert_and_dispatch accepts learning_goal_deleted type", async () => {
    const recipientId = new mongoose.Types.ObjectId();
    const senderId = new mongoose.Types.ObjectId();
    const goalId = new mongoose.Types.ObjectId();

    const savedDoc = {
      _id: new mongoose.Types.ObjectId(),
      user_id: recipientId,
      type: "learning_goal_deleted",
      delivery_channel: ["in_app"],
      save: jest.fn().mockResolvedValue(true),
    };
    Notification.create.mockResolvedValue(savedDoc);

    const result = await insert_and_dispatch([
      {
        user_id: String(recipientId),
        sender_id: String(senderId),
        type: "learning_goal_deleted",
        reference_type: "learning_goal",
        reference_id: String(goalId),
        title: "Shared learning plan removed",
        message: "Ali removed python basics from their plan. Your copy is unaffected.",
        action_required: false,
        delivery_channel: ["in_app"],
      },
    ]);

    expect(result.inserted).toBe(1);
    expect(result.failed).toBe(0);
    expect(Notification.create).toHaveBeenCalledTimes(1);
    expect(Notification.create.mock.calls[0][0].type).toBe("learning_goal_deleted");
    expect(savedDoc.save).toHaveBeenCalled();
  });
});

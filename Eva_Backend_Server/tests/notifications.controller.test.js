process.env.NODE_ENV = "test";

jest.mock("../models", () => ({
  Notification: {
    find: jest.fn(),
    countDocuments: jest.fn(),
    findOneAndUpdate: jest.fn(),
    updateMany: jest.fn(),
  },
}));

const mongoose = require("mongoose");
const { Notification } = require("../models");
const {
  listNotifications,
  getUnreadCount,
  markNotificationRead,
  markAllNotificationsRead,
} = require("../controllers/notifications.controller");

const USER_ID = new mongoose.Types.ObjectId();

const mockRes = () => {
  const res = {};
  res.status = jest.fn().mockReturnValue(res);
  res.json = jest.fn().mockReturnValue(res);
  return res;
};

const mockReq = (overrides = {}) => ({
  userId: USER_ID,
  user: { timezone: "UTC" },
  params: {},
  query: {},
  body: {},
  ...overrides,
});

describe("notifications.controller", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("listNotifications returns paginated notifications", async () => {
    const notificationId = new mongoose.Types.ObjectId();
    Notification.find.mockReturnValue({
      sort: jest.fn().mockReturnValue({
        skip: jest.fn().mockReturnValue({
          limit: jest.fn().mockReturnValue({
            populate: jest.fn().mockReturnValue({
              lean: jest.fn().mockResolvedValue([
                {
                  _id: notificationId,
                  type: "friend_request",
                  title: "New friend request",
                  message: "Alex sent you a friend request.",
                  is_read: false,
                  action_required: true,
                  delivery_channel: ["push", "in_app"],
                  created_at: new Date("2026-06-05T10:00:00.000Z"),
                  sender_id: {
                    _id: new mongoose.Types.ObjectId(),
                    name: "Alex",
                    username: "alex",
                  },
                },
              ]),
            }),
          }),
        }),
      }),
    });
    Notification.countDocuments
      .mockResolvedValueOnce(1)
      .mockResolvedValueOnce(1);

    const req = mockReq({ query: { limit: "10", skip: "0" } });
    const res = mockRes();
    const next = jest.fn();

    await listNotifications(req, res, next);

    expect(next).not.toHaveBeenCalled();
    expect(res.json).toHaveBeenCalledWith(
      expect.objectContaining({
        status: "success",
        data: expect.objectContaining({
          notifications: [
            expect.objectContaining({
              type: "friend_request",
              is_read: false,
            }),
          ],
          unread_count: 1,
        }),
      }),
    );
  });

  test("getUnreadCount returns count", async () => {
    Notification.countDocuments.mockResolvedValue(3);

    const req = mockReq();
    const res = mockRes();
    const next = jest.fn();

    await getUnreadCount(req, res, next);

    expect(res.json).toHaveBeenCalledWith({
      status: "success",
      data: expect.objectContaining({
        unread_count: 3,
        timezone: "UTC",
      }),
    });
  });

  test("markNotificationRead updates owned notification", async () => {
    const notificationId = new mongoose.Types.ObjectId();
    Notification.findOneAndUpdate.mockReturnValue({
      populate: jest.fn().mockReturnValue({
        lean: jest.fn().mockResolvedValue({
          _id: notificationId,
          type: "friend_accepted",
          title: "Friend request accepted",
          message: "Alex accepted your friend request.",
          is_read: true,
          action_required: false,
          delivery_channel: ["push", "in_app"],
          created_at: new Date(),
          sender_id: null,
        }),
      }),
    });

    const req = mockReq({ params: { id: String(notificationId) } });
    const res = mockRes();
    const next = jest.fn();

    await markNotificationRead(req, res, next);

    expect(Notification.findOneAndUpdate).toHaveBeenCalledWith(
      { _id: String(notificationId), user_id: USER_ID },
      { $set: { is_read: true } },
      { new: true },
    );
    expect(res.json).toHaveBeenCalledWith(
      expect.objectContaining({
        status: "success",
        data: expect.objectContaining({
          notification: expect.objectContaining({ is_read: true }),
        }),
      }),
    );
  });

  test("markAllNotificationsRead returns modified count", async () => {
    Notification.updateMany.mockResolvedValue({ modifiedCount: 5 });

    const req = mockReq();
    const res = mockRes();
    const next = jest.fn();

    await markAllNotificationsRead(req, res, next);

    expect(Notification.updateMany).toHaveBeenCalledWith(
      { user_id: USER_ID, is_read: false },
      { $set: { is_read: true } },
    );
    expect(res.json).toHaveBeenCalledWith({
      status: "success",
      data: expect.objectContaining({
        marked_read: 5,
        timezone: "UTC",
      }),
    });
  });
});

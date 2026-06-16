jest.mock("../config/logger", () => ({
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
}));

jest.mock("../services/cloudinary.service", () => ({
  deleteProfilePicture: jest.fn().mockResolvedValue(undefined),
}));

const mockDistinct = jest.fn();
const mockUpdateMany = jest.fn().mockResolvedValue({ modifiedCount: 1 });
const mockUpdateOne = jest.fn().mockResolvedValue({ modifiedCount: 1 });
const mockDeleteMany = jest.fn().mockResolvedValue({ deletedCount: 1 });
const mockFind = jest.fn();

jest.mock("../models", () => ({
  User: { updateOne: (...args) => mockUpdateOne(...args) },
  UserSetting: { updateOne: (...args) => mockUpdateOne(...args) },
  LearningGoal: {
    find: (...args) => mockFind(...args),
    updateMany: (...args) => mockUpdateMany(...args),
  },
  RoadmapTopic: { updateMany: (...args) => mockUpdateMany(...args) },
  Task: { updateMany: (...args) => mockUpdateMany(...args) },
  ChatSession: {
    find: (...args) => mockFind(...args),
    updateMany: (...args) => mockUpdateMany(...args),
  },
  ConversationHistory: { updateMany: (...args) => mockUpdateMany(...args) },
  Friend: { deleteMany: (...args) => mockDeleteMany(...args) },
  Integration: { updateMany: (...args) => mockUpdateMany(...args) },
}));

const { deleteProfilePicture } = require("../services/cloudinary.service");
const {
  softDeleteUserAccount,
  buildDeletedIdentity,
} = require("../services/accountDelete.service");

const USER_ID = "507f1f77bcf86cd799439011";

describe("accountDelete.service", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFind.mockReturnValue({ distinct: mockDistinct });
    mockDistinct.mockResolvedValue([]);
  });

  test("buildDeletedIdentity uses stable anonymized values", () => {
    expect(buildDeletedIdentity(USER_ID)).toEqual({
      email: `del_${USER_ID}@deleted.eva`,
      username: `del_${USER_ID}`,
      name: "Deleted User",
    });
  });

  test("soft-deletes user and clears avatar when present", async () => {
    mockDistinct.mockResolvedValueOnce(["goal1"]).mockResolvedValueOnce(["sess1"]);

    const user = {
      _id: USER_ID,
      profile_picture_public_id: "eva/profile-pictures/old",
    };

    await softDeleteUserAccount(user);

    expect(deleteProfilePicture).toHaveBeenCalledWith("eva/profile-pictures/old");
    expect(mockDeleteMany).toHaveBeenCalledWith({
      $or: [{ requester_id: USER_ID }, { recipient_id: USER_ID }],
    });
    expect(mockUpdateOne).toHaveBeenCalledWith(
      { _id: USER_ID },
      expect.objectContaining({
        $set: expect.objectContaining({
          email: `del_${USER_ID}@deleted.eva`,
          is_active: false,
        }),
        $unset: { password_hash: "" },
      }),
    );
  });

  test("skips avatar delete when no public id", async () => {
    await softDeleteUserAccount({
      _id: USER_ID,
      profile_picture_public_id: null,
    });

    expect(deleteProfilePicture).not.toHaveBeenCalled();
    expect(mockUpdateOne).toHaveBeenCalled();
  });
});

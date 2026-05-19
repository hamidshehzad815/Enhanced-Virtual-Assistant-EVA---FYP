jest.mock("../services/notification.service", () => ({
  insert_and_dispatch: jest.fn().mockResolvedValue({
    requested: 1,
    inserted: 1,
    dispatched_push: 1,
    dispatched_email: 0,
    failed: 0,
    results: [],
  }),
}));

jest.mock("../models", () => ({
  User: {
    findById: jest.fn(),
  },
}));

const { User } = require("../models");
const { insert_and_dispatch } = require("../services/notification.service");
const {
  notifyOwnerOfCollaborationResponse,
  buildOwnerResponsePayload,
} = require("../services/collaborationNotifications");

const OWNER_ID = "507f1f77bcf86cd799439011";
const COLLAB_ID = "507f1f77bcf86cd799439012";
const GOAL_ID = "507f1f77bcf86cd799439013";

describe("collaborationNotifications", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    User.findById.mockReturnValue({
      select: jest.fn().mockReturnValue({
        lean: jest.fn().mockResolvedValue({
          name: "Alex Collaborator",
          username: "alex",
          email: "alex@example.com",
        }),
      }),
    });
  });

  test("buildOwnerResponsePayload for learning accept", () => {
    const payload = buildOwnerResponsePayload({
      ownerId: OWNER_ID,
      collaboratorUserId: COLLAB_ID,
      collaboratorName: "Alex",
      action: "accept",
      referenceType: "learning_goal",
      referenceId: GOAL_ID,
      itemTitle: "Python roadmap",
    });

    expect(payload.type).toBe("learning_collaboration_response");
    expect(payload.user_id).toBe(OWNER_ID);
    expect(payload.sender_id).toBe(COLLAB_ID);
    expect(payload.title).toBe("Collaboration accepted");
    expect(payload.message).toContain("Alex");
    expect(payload.message).toContain("Python roadmap");
    expect(payload.delivery_channel).toEqual(["push", "in_app", "email"]);
  });

  test("notifyOwnerOfCollaborationResponse dispatches to owner", async () => {
    const result = await notifyOwnerOfCollaborationResponse({
      ownerId: OWNER_ID,
      collaboratorUserId: COLLAB_ID,
      action: "reject",
      referenceType: "task",
      referenceId: GOAL_ID,
      itemTitle: "Physics quiz",
    });

    expect(result.dispatched).toBe(true);
    expect(insert_and_dispatch).toHaveBeenCalledTimes(1);
    const payload = insert_and_dispatch.mock.calls[0][0][0];
    expect(payload.user_id).toBe(OWNER_ID);
    expect(payload.type).toBe("collaboration_response");
    expect(payload.title).toBe("Collaboration declined");
    expect(payload.message).toContain("declined");
  });

  test("skips when owner and collaborator are the same user", async () => {
    const result = await notifyOwnerOfCollaborationResponse({
      ownerId: OWNER_ID,
      collaboratorUserId: OWNER_ID,
      action: "accept",
      referenceType: "task",
      referenceId: GOAL_ID,
      itemTitle: "Self task",
    });

    expect(result.dispatched).toBe(false);
    expect(insert_and_dispatch).not.toHaveBeenCalled();
  });
});

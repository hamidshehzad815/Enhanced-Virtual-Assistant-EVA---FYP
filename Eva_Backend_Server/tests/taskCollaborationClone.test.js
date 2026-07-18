jest.mock("../services/collaborationNotifications", () => ({
  notifyOwnerOfCollaborationResponse: jest.fn().mockResolvedValue({}),
}));
jest.mock("../services/notification.service", () => ({
  insert_and_dispatch: jest.fn().mockResolvedValue([]),
}));
jest.mock("../services/googleCalendar.service", () => ({
  deleteEvent: jest.fn().mockResolvedValue({}),
}));
jest.mock("../utils/googleCalendarSync", () => ({
  resolveGoogleCalendarSync: jest.fn().mockResolvedValue(null),
}));
jest.mock("../models", () => ({
  Task: { findOne: jest.fn(), findOneAndUpdate: jest.fn(), create: jest.fn() },
  ActivityLog: { create: jest.fn() },
  Notification: { findOneAndUpdate: jest.fn().mockResolvedValue({}) },
  UserSetting: { findOne: jest.fn() },
  User: { find: jest.fn() },
}));

const mongoose = require("mongoose");
const { Task } = require("../models");
const {
  notifyOwnerOfCollaborationResponse,
} = require("../services/collaborationNotifications");
const {
  applyCollaborationAction,
  cloneTaskForCollaborator,
} = require("../controllers/tasks.controller");

const OWNER_ID = new mongoose.Types.ObjectId();
const COLLAB_ID = new mongoose.Types.ObjectId();
const TASK_ID = new mongoose.Types.ObjectId();
const NEW_TASK_ID = new mongoose.Types.ObjectId();

const lean = (value) => ({ lean: jest.fn().mockResolvedValue(value) });

describe("task collaboration accept clones the task for the collaborator", () => {
  beforeEach(() => jest.clearAllMocks());

  test("accept creates a copy owned by the collaborator", async () => {
    const pendingTask = {
      _id: TASK_ID,
      owner_id: OWNER_ID,
      title: "Group study",
      collaborators: [{ user_id: COLLAB_ID, status: "pending" }],
    };
    const updatedTask = {
      ...pendingTask,
      collaborators: [{ user_id: COLLAB_ID, status: "accepted" }],
    };

    Task.findOne
      .mockReturnValueOnce(lean(pendingTask)) // load pending task
      .mockReturnValueOnce(lean(null)); // no existing clone
    Task.findOneAndUpdate.mockReturnValue(lean(updatedTask));
    Task.create.mockResolvedValue({ _id: NEW_TASK_ID });

    const result = await applyCollaborationAction({
      taskId: String(TASK_ID),
      collaboratorUserId: String(COLLAB_ID),
      action: "accept",
    });

    expect(result.already_responded).toBe(false);
    expect(result.collaborator_task_id).toEqual(NEW_TASK_ID);
    expect(Task.create).toHaveBeenCalledTimes(1);
    const created = Task.create.mock.calls[0][0];
    expect(String(created.owner_id)).toBe(String(COLLAB_ID));
    expect(String(created.source_task_id)).toBe(String(TASK_ID));
    expect(created.status).toBe("pending");
    expect(created.collaborators).toEqual([]);
    expect(notifyOwnerOfCollaborationResponse).toHaveBeenCalled();
  });

  test("reject does not clone the task", async () => {
    const pendingTask = {
      _id: TASK_ID,
      owner_id: OWNER_ID,
      title: "Group study",
      collaborators: [{ user_id: COLLAB_ID, status: "pending" }],
    };

    Task.findOne.mockReturnValueOnce(lean(pendingTask));
    Task.findOneAndUpdate.mockReturnValue(
      lean({
        ...pendingTask,
        collaborators: [{ user_id: COLLAB_ID, status: "rejected" }],
      }),
    );

    const result = await applyCollaborationAction({
      taskId: String(TASK_ID),
      collaboratorUserId: String(COLLAB_ID),
      action: "reject",
    });

    expect(result.already_responded).toBe(false);
    expect(result.collaborator_task_id).toBeNull();
    expect(Task.create).not.toHaveBeenCalled();
  });

  test("already-responded invite does not clone again", async () => {
    Task.findOne.mockReturnValueOnce(
      lean({
        _id: TASK_ID,
        owner_id: OWNER_ID,
        title: "Group study",
        collaborators: [{ user_id: COLLAB_ID, status: "accepted" }],
      }),
    );

    const result = await applyCollaborationAction({
      taskId: String(TASK_ID),
      collaboratorUserId: String(COLLAB_ID),
      action: "accept",
    });

    expect(result.already_responded).toBe(true);
    expect(Task.findOneAndUpdate).not.toHaveBeenCalled();
    expect(Task.create).not.toHaveBeenCalled();
  });

  test("cloneTaskForCollaborator is idempotent when a copy exists", async () => {
    const existing = { _id: NEW_TASK_ID, owner_id: COLLAB_ID };
    Task.findOne.mockReturnValueOnce(lean(existing));

    const result = await cloneTaskForCollaborator(
      { _id: TASK_ID, title: "Group study" },
      String(COLLAB_ID),
    );

    expect(result).toBe(existing);
    expect(Task.create).not.toHaveBeenCalled();
  });
});

const mongoose = require("mongoose");

jest.mock("../models", () => ({
  Task: { find: jest.fn() },
  User: { findById: jest.fn() },
  UserSetting: { findOne: jest.fn() },
}));

const { Task, User, UserSetting } = require("../models");
const {
  findUserCalendarConflicts,
  formatCollaboratorConflictMessage,
} = require("../utils/userCalendarConflicts");

const USER_ID = new mongoose.Types.ObjectId();

describe("userCalendarConflicts", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    User.findById.mockReturnValue({
      select: jest.fn().mockReturnValue({
        lean: jest.fn().mockResolvedValue({ timezone: "UTC" }),
      }),
    });
    Task.find.mockReturnValue({
      select: jest.fn().mockReturnValue({
        lean: jest.fn().mockResolvedValue([]),
      }),
    });
    UserSetting.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        preferred_learning_schedules: [
          {
            id: "s1",
            label: "Evening study",
            slots: [{ day: 1, time: "18:00", duration_minutes: 60 }],
          },
        ],
      }),
    });
  });

  test("detects learning schedule overlap for collaborator", async () => {
    const due = new Date(Date.UTC(2026, 0, 6, 18, 15, 0));
    const conflict = await findUserCalendarConflicts(USER_ID, due, 30, "UTC");
    expect(conflict).not.toBeNull();
    expect(conflict.kind).toBe("learning_schedule");
    expect(conflict.schedule_label).toBe("Evening study");
  });

  test("formatCollaboratorConflictMessage for learning schedule", () => {
    const msg = formatCollaboratorConflictMessage("Ali", {
      kind: "learning_schedule",
      schedule_label: "Study",
      slot: { day: 2, time: "19:00" },
    });
    expect(msg).toContain("Ali");
    expect(msg).toContain("Study");
  });
});

const {
  dueDatetimeMatchesSlot,
} = require("../utils/learningScheduleConflict");

describe("learningScheduleConflict", () => {
  test("dueDatetimeMatchesSlot: Monday 10:30 UTC matches day 0 slot", () => {
    const due = new Date(Date.UTC(2026, 0, 5, 10, 30, 0));
    expect(dueDatetimeMatchesSlot(due, "UTC", 0, "10:30")).toBe(true);
  });

  test("dueDatetimeMatchesSlot: same instant wrong weekday does not match", () => {
    const due = new Date(Date.UTC(2026, 0, 5, 10, 30, 0));
    expect(dueDatetimeMatchesSlot(due, "UTC", 1, "10:30")).toBe(false);
  });

  test("dueDatetimeMatchesSlot: same weekday wrong clock does not match", () => {
    const due = new Date(Date.UTC(2026, 0, 5, 10, 30, 0));
    expect(dueDatetimeMatchesSlot(due, "UTC", 0, "11:00")).toBe(false);
  });
});

describe("findLearningScheduleTaskConflicts", () => {
  const { findLearningScheduleTaskConflicts } = require("../utils/learningScheduleConflict");

  test("ignores tasks belonging to excluded learning plans", async () => {
    const saturday = new Date("2026-07-04T00:47:00+05:00");
    const TaskModel = {
      find: jest.fn().mockReturnValue({
        select: jest.fn().mockReturnValue({
          lean: jest.fn().mockResolvedValue([
            {
              _id: "task1",
              title: "Learn: Python Hello World",
              due_datetime: saturday,
              status: "pending",
              duration: 60,
              learning_plan_id: "goal1",
            },
            {
              _id: "task2",
              title: "Buy groceries",
              due_datetime: saturday,
              status: "pending",
              duration: 60,
              learning_plan_id: null,
            },
          ]),
        }),
      }),
    };

    const schedule = [{ day: 5, time: "01:05", duration_minutes: 60 }];
    const withExclusion = await findLearningScheduleTaskConflicts(
      "user1",
      schedule,
      "Asia/Karachi",
      TaskModel,
      { excludeLearningPlanIds: ["goal1"] },
    );
    expect(withExclusion).toHaveLength(1);
    expect(withExclusion[0].task._id).toBe("task2");

    const withoutExclusion = await findLearningScheduleTaskConflicts(
      "user1",
      schedule,
      "Asia/Karachi",
      TaskModel,
    );
    expect(withoutExclusion).toHaveLength(2);
  });
});
describe("dueDatetimeOverlapsSlot", () => {
  const { dueDatetimeOverlapsSlot } = require("../utils/learningScheduleConflict");

  test("overlaps when task spans into slot", () => {
    const due = new Date(Date.UTC(2026, 0, 5, 10, 0, 0));
    expect(dueDatetimeOverlapsSlot(due, "UTC", 0, "11:00", 60, 120)).toBe(true);
  });

  test("no overlap on different weekday", () => {
    const due = new Date(Date.UTC(2026, 0, 6, 10, 0, 0));
    expect(dueDatetimeOverlapsSlot(due, "UTC", 0, "10:30", 60, 120)).toBe(false);
  });
});

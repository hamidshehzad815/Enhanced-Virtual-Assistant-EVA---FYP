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

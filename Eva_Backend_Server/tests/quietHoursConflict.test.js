const {
  findQuietHourLearningConflicts,
  windowOverlapsQuietBlock,
  weeklySlotOverlapsQuietHours,
} = require("../utils/quietHoursConflict");

describe("quietHoursConflict", () => {
  test("full window overlap when task starts before quiet block", () => {
    expect(windowOverlapsQuietBlock(9 * 60 + 30, 90, 10 * 60, 12 * 60)).toBe(true);
  });

  test("no overlap when windows are separate", () => {
    expect(windowOverlapsQuietBlock(15 * 60, 60, 22 * 60, 7 * 60)).toBe(false);
  });

  test("weekly slot overlaps overnight quiet hours", () => {
    const hits = weeklySlotOverlapsQuietHours("22:30", 60, [
      { label: "sleep", start: "22:00", end: "07:00" },
    ]);
    expect(hits).toHaveLength(1);
  });

  test("findQuietHourLearningConflicts detects schedule vs quiet hours", () => {
    const settingsDoc = {
      quiet_hours_enabled: true,
      quiet_hours: [{ label: "uni", start: "09:00", end: "13:00", enabled: true }],
      preferred_learning_schedules: [
        {
          id: "s1",
          label: "Morning",
          slots: [{ day: 1, time: "10:00", duration_minutes: 90 }],
        },
      ],
    };
    const conflicts = findQuietHourLearningConflicts(settingsDoc);
    expect(conflicts).toHaveLength(1);
    expect(conflicts[0].schedule_label).toBe("Morning");
  });
});

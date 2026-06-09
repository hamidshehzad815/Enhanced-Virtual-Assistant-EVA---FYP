const {
  findCrossScheduleSlotConflicts,
  assertNoDuplicateSlotsAcrossSchedules,
  normalizePreferredLearningSchedules,
} = require("../utils/learningSchedules");

describe("learningSchedules cross-schedule slots", () => {
  test("findCrossScheduleSlotConflicts detects same day and time", () => {
    const existing = [
      {
        id: "a",
        label: "Schedule A",
        slots: [{ day: 0, time: "18:00", duration_minutes: 60 }],
      },
    ];
    const candidate = [{ day: 0, time: "18:00", duration_minutes: 90 }];
    const conflicts = findCrossScheduleSlotConflicts(candidate, existing);
    expect(conflicts).toHaveLength(1);
    expect(conflicts[0].conflicting_schedule.label).toBe("Schedule A");
  });

  test("same day different time is allowed", () => {
    const existing = [
      {
        id: "a",
        label: "Schedule A",
        slots: [{ day: 0, time: "18:00", duration_minutes: 60 }],
      },
    ];
    const candidate = [{ day: 0, time: "20:00", duration_minutes: 90 }];
    expect(findCrossScheduleSlotConflicts(candidate, existing)).toHaveLength(0);
  });

  test("bulk normalize rejects duplicate slots across schedules", () => {
    expect(() =>
      normalizePreferredLearningSchedules([
        {
          label: "A",
          slots: [{ day: 0, time: "18:00", duration_minutes: 60 }],
        },
        {
          label: "B",
          slots: [{ day: 0, time: "18:00", duration_minutes: 75 }],
        },
      ]),
    ).toThrow(/Monday 18:00|same weekday/i);
  });

  test("bulk normalize requires duration_minutes on each slot", () => {
    expect(() =>
      normalizePreferredLearningSchedules([
        {
          label: "Morning",
          slots: [{ day: 0, time: "09:00" }],
        },
      ]),
    ).toThrow(/duration_minutes is required/i);
  });

  test("assertNoDuplicateSlotsAcrossSchedules passes for non-overlapping", () => {
    expect(() =>
      assertNoDuplicateSlotsAcrossSchedules([
        {
          id: "1",
          label: "A",
          slots: [{ day: 0, time: "18:00", duration_minutes: 60 }],
        },
        {
          id: "2",
          label: "B",
          slots: [{ day: 0, time: "20:00", duration_minutes: 60 }],
        },
      ]),
    ).not.toThrow();
  });
});

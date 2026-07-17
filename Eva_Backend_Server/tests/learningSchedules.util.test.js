const {
  findCrossScheduleSlotConflicts,
  assertNoDuplicateSlotsAcrossSchedules,
  normalizePreferredLearningSchedules,
  resolveLearningSlotsForGoal,
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

  test("allows multiple non-overlapping slots on the same weekday", () => {
    const schedules = normalizePreferredLearningSchedules([
      {
        label: "Double Monday",
        slots: [
          { day: 0, time: "09:00", duration_minutes: 60 },
          { day: 0, time: "19:00", duration_minutes: 60 },
        ],
      },
    ]);
    expect(schedules[0].slots).toHaveLength(2);
  });

  test("rejects overlapping slots on the same weekday", () => {
    expect(() =>
      normalizePreferredLearningSchedules([
        {
          label: "Overlap",
          slots: [
            { day: 0, time: "09:00", duration_minutes: 90 },
            { day: 0, time: "10:00", duration_minutes: 60 },
          ],
        },
      ]),
    ).toThrow(/overlapping slots on Monday/i);
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

describe("resolveLearningSlotsForGoal", () => {
  const settings = {
    preferred_learning_schedules: [
      {
        id: "seed-weekday-evenings",
        label: "Weekday evenings",
        slots: [{ day: 0, time: "18:00", duration_minutes: 90 }],
      },
      {
        id: "python-learning",
        label: "Python learning",
        slots: [{ day: 4, time: "23:30", duration_minutes: 60 }],
      },
    ],
  };

  test("uses goal learning_schedule_id when set", () => {
    const slots = resolveLearningSlotsForGoal(settings, {
      learning_schedule_id: "python-learning",
    });
    expect(slots).toEqual([{ day: 4, time: "23:30", duration_minutes: 60 }]);
  });

  test("falls back to sole schedule when id missing", () => {
    const single = {
      preferred_learning_schedules: [
        {
          id: "only",
          label: "Only",
          slots: [{ day: 2, time: "20:00", duration_minutes: 75 }],
        },
      ],
    };
    expect(resolveLearningSlotsForGoal(single, {})).toEqual([
      { day: 2, time: "20:00", duration_minutes: 75 },
    ]);
  });

  test("returns empty when multiple schedules and no linked id", () => {
    expect(resolveLearningSlotsForGoal(settings, {})).toEqual([]);
  });
});

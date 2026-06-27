const { buildPlanScheduleDates } = require("../utils/planScheduleDates");

describe("planScheduleDates", () => {
  const goal = {
    _id: "674a1b2c3d4e5f6789012301",
    learning_schedule_id: "sched-1",
    end_date: new Date("2026-08-01T00:00:00.000Z"),
    status: "active",
  };

  const settings = {
    preferred_learning_schedules: [
      {
        id: "sched-1",
        label: "Evening",
        slots: [
          { day: 0, time: "18:00", duration_minutes: 90 },
          { day: 2, time: "19:00", duration_minutes: 60 },
        ],
      },
    ],
  };

  test("returns only Mon/Wed dates from today through horizon", () => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date("2026-06-27T10:00:00.000Z"));

    const result = buildPlanScheduleDates(goal, settings, "Asia/Karachi", {
      horizonWeeks: 2,
    });

    expect(result.weekdays).toHaveLength(2);
    expect(result.weekdays.map((w) => w.day)).toEqual([0, 2]);
    expect(result.dates.length).toBeGreaterThan(0);
    result.dates.forEach((row) => {
      expect([0, 2]).toContain(row.day);
      expect(row.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(row.scheduled_datetime).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    });
    expect(result.range.from).toBe("2026-06-27");

    jest.useRealTimers();
  });

  test("returns empty dates when plan has no learning slots", () => {
    const empty = buildPlanScheduleDates(
      goal,
      { preferred_learning_schedules: [{ id: "sched-1", label: "X", slots: [] }] },
      "UTC",
    );
    expect(empty.dates).toEqual([]);
    expect(empty.weekdays).toEqual([]);
  });
});

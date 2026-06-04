const {
  computeSessionState,
  computeUnlockTime,
  enrichSessionsForGoal,
  validateTopicAction,
} = require("../utils/learningSessionState");

const session = (scheduled, status = "pending") => ({
  _id: "507f1f77bcf86cd799439099",
  order: 2,
  status,
  scheduled_date: scheduled,
});

describe("learningSessionState", () => {
  test("completed and skipped passthrough", () => {
    const now = new Date("2025-06-10T12:00:00Z");
    expect(
      computeSessionState(
        session(now, "completed"),
        now,
      ),
    ).toBe("completed");
    expect(
      computeSessionState(
        session(now, "skipped"),
        now,
      ),
    ).toBe("skipped");
  });

  test("locked when more than 24h before schedule", () => {
    const scheduled = new Date("2025-06-15T18:00:00Z");
    const now = new Date("2025-06-10T12:00:00Z");
    expect(computeSessionState(session(scheduled), now)).toBe("locked");
  });

  test("unlocked_future within 24h before schedule", () => {
    const scheduled = new Date("2025-06-10T18:00:00Z");
    const now = new Date("2025-06-10T10:00:00Z");
    expect(computeSessionState(session(scheduled), now)).toBe("unlocked_future");
  });

  test("overdue after scheduled time", () => {
    const scheduled = new Date("2025-06-10T09:00:00Z");
    const now = new Date("2025-06-10T12:00:00Z");
    expect(computeSessionState(session(scheduled), now)).toBe("overdue");
  });

  test("short gap unlocks after previous resolved", () => {
    const prevScheduled = new Date("2025-06-10T09:00:00Z");
    const scheduled = new Date("2025-06-10T15:00:00Z");
    const prevResolved = new Date("2025-06-10T10:00:00Z");
    const now = new Date("2025-06-10T11:00:00Z");
    expect(
      computeSessionState(session(scheduled), now, {
        previousScheduledDate: prevScheduled,
        previousResolvedAt: prevResolved,
      }),
    ).toBe("unlocked_future");
  });

  test("short gap stays locked until previous resolved", () => {
    const prevScheduled = new Date("2025-06-10T09:00:00Z");
    const scheduled = new Date("2025-06-10T15:00:00Z");
    const now = new Date("2025-06-10T11:00:00Z");
    expect(
      computeSessionState(session(scheduled), now, {
        previousScheduledDate: prevScheduled,
        previousResolvedAt: null,
      }),
    ).toBe("locked");
  });

  test("enrichSessionsForGoal marks current and upcoming", () => {
    const now = new Date("2026-06-03T12:00:00Z");
    const topics = [
      {
        _id: "507f1f77bcf86cd799439011",
        order: 1,
        status: "completed",
        scheduled_date: new Date("2026-06-01T18:00:00Z"),
        completed_at: new Date("2026-06-02T10:00:00Z"),
      },
      {
        _id: "507f1f77bcf86cd799439012",
        order: 2,
        status: "pending",
        scheduled_date: new Date("2026-06-10T18:00:00Z"),
      },
      {
        _id: "507f1f77bcf86cd799439013",
        order: 3,
        status: "pending",
        scheduled_date: new Date("2026-06-15T18:00:00Z"),
      },
    ];
    const enriched = enrichSessionsForGoal(topics, now);
    expect(enriched[0]).toEqual({
      session_state: "completed",
      is_current: false,
      unlock_at: null,
    });
    expect(enriched[1].is_current).toBe(true);
    expect(enriched[1].session_state).toBe("locked");
    expect(enriched[1].unlock_at).toBeTruthy();
    expect(enriched[2]).toEqual({
      session_state: "upcoming",
      is_current: false,
      unlock_at: null,
    });
  });

  test("validateTopicAction blocks skip when locked", () => {
    const topics = [
      {
        _id: "a",
        order: 1,
        status: "pending",
        scheduled_date: new Date("2026-06-20T18:00:00Z"),
      },
    ];
    const err = validateTopicAction({
      topics,
      topicId: "a",
      action: "skip",
      now: new Date("2026-06-01T12:00:00Z"),
    });
    expect(err?.message).toMatch(/still locked/i);
  });

  test("computeUnlockTime matches locked window", () => {
    const scheduled = new Date("2025-06-15T18:00:00Z");
    const unlock = computeUnlockTime(session(scheduled));
    expect(unlock.toISOString()).toBe("2025-06-14T18:00:00.000Z");
  });
});

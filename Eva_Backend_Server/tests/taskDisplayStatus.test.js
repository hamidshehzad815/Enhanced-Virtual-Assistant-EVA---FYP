const {
  computeTaskDisplayStatus,
  normalizeStoredStatus,
  enrichTaskForApi,
  serializeTaskForApi,
} = require("../utils/taskDisplayStatus");

describe("taskDisplayStatus", () => {
  const now = new Date("2026-05-19T12:00:00.000Z");

  test("normalizeStoredStatus maps legacy ongoing to pending", () => {
    expect(normalizeStoredStatus("ongoing")).toBe("pending");
    expect(normalizeStoredStatus("pending")).toBe("pending");
    expect(normalizeStoredStatus("complete")).toBe("complete");
    expect(normalizeStoredStatus("completed")).toBe("complete");
  });

  test("computeTaskDisplayStatus returns complete when stored complete", () => {
    const task = {
      status: "complete",
      due_datetime: new Date("2026-05-19T08:00:00.000Z"),
      duration: 60,
    };
    expect(computeTaskDisplayStatus(task, now)).toBe("complete");
  });

  test("computeTaskDisplayStatus returns pending before start", () => {
    const task = {
      status: "pending",
      due_datetime: new Date("2026-05-19T13:00:00.000Z"),
      duration: 60,
    };
    expect(computeTaskDisplayStatus(task, now)).toBe("pending");
  });

  test("computeTaskDisplayStatus returns ongoing during window", () => {
    const task = {
      status: "pending",
      due_datetime: new Date("2026-05-19T11:30:00.000Z"),
      duration: 60,
    };
    expect(computeTaskDisplayStatus(task, now)).toBe("ongoing");
  });

  test("computeTaskDisplayStatus returns overdue after window", () => {
    const task = {
      status: "pending",
      due_datetime: new Date("2026-05-19T09:00:00.000Z"),
      duration: 30,
    };
    expect(computeTaskDisplayStatus(task, now)).toBe("overdue");
  });

  test("legacy ongoing stored status still computes time-based display", () => {
    const task = {
      status: "ongoing",
      due_datetime: new Date("2026-05-19T09:00:00.000Z"),
      duration: 30,
    };
    expect(computeTaskDisplayStatus(task, now)).toBe("overdue");
    expect(enrichTaskForApi(task, now).status).toBe("pending");
    expect(enrichTaskForApi(task, now).display_status).toBe("overdue");
  });

  test("serializeTaskForApi returns slim list shape", () => {
    const task = {
      _id: "507f1f77bcf86cd799439012",
      owner_id: "507f1f77bcf86cd799439011",
      title: "Learn: Python",
      due_datetime: new Date("2026-06-12T08:00:00.000Z"),
      duration: 75,
      priority: "medium",
      status: "pending",
      source: "eva",
      learning_plan_id: "507f1f77bcf86cd799439099",
      learning_topic_id: "507f1f77bcf86cd799439088",
      is_deleted: false,
      created_at: new Date("2026-06-04T08:00:00.000Z"),
    };
    const out = serializeTaskForApi(task, now, "UTC");
    expect(out).toEqual(
      expect.objectContaining({
        id: "507f1f77bcf86cd799439012",
        title: "Learn: Python",
        duration: 75,
        status: "pending",
        display_status: "pending",
        is_learning_task: true,
        learning_goal_id: "507f1f77bcf86cd799439099",
      }),
    );
    expect(out).not.toHaveProperty("owner_id");
    expect(out).not.toHaveProperty("learning_topic_id");
    expect(out).not.toHaveProperty("description");
  });
});

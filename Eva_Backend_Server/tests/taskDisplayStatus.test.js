const {
  computeTaskDisplayStatus,
  normalizeStoredStatus,
  enrichTaskForApi,
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
});

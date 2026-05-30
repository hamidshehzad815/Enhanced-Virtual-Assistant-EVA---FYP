process.env.NODE_ENV = "test";

jest.mock("../config/logger", () => ({
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
  debug: jest.fn(),
  http: jest.fn(),
  add: jest.fn(),
  stream: { write: jest.fn() },
}));

jest.mock("axios", () => ({
  post: jest.fn(),
}));

jest.mock("../models", () => ({
  RoadmapTopic: { find: jest.fn() },
  LearningGoal: { find: jest.fn() },
}));

describe("Learning auto-complete job", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.AI_SERVER_URL = "http://ai.test";
    jest.resetModules();
  });

  test("computeDeadline adds duration + 180min", () => {
    // require after env setup (job reads env at module load)
    const { computeDeadline } = require("../jobs/learning_auto_complete.job");
    const topic = {
      scheduled_date: new Date("2026-06-01T10:00:00.000Z"),
      estimated_duration: 90,
    };
    const deadline = computeDeadline(topic);
    expect(deadline.toISOString()).toBe("2026-06-01T14:30:00.000Z");
  });

  test("findDueTopics returns only topics whose active goal exists", async () => {
    const { findDueTopics } = require("../jobs/learning_auto_complete.job");
    const { RoadmapTopic, LearningGoal } = require("../models");
    const now = new Date("2026-06-01T20:00:00.000Z");

    const leanTopics = jest.fn().mockResolvedValue([
      {
        _id: "t1",
        goal_id: "g1",
        scheduled_date: new Date("2026-06-01T10:00:00.000Z"),
        estimated_duration: 90,
        status: "pending",
        is_deleted: false,
      },
      {
        _id: "t2",
        goal_id: "g2",
        scheduled_date: new Date("2026-06-01T19:00:00.000Z"),
        estimated_duration: 90,
        status: "pending",
        is_deleted: false,
      },
    ]);
    RoadmapTopic.find.mockReturnValue({
      select: jest.fn().mockReturnValue({ lean: leanTopics }),
    });

    // only g1 is active
    LearningGoal.find.mockReturnValue({
      lean: jest.fn().mockResolvedValue([{ _id: "g1", user_id: "u1" }]),
    });

    const due = await findDueTopics(now);
    expect(due).toHaveLength(1);
    expect(String(due[0].topic._id)).toBe("t1");
    expect(String(due[0].goal._id)).toBe("g1");
  });

  test("runAutoCompleteCycle posts to AI server for due topics", async () => {
    const { runAutoCompleteCycle } = require("../jobs/learning_auto_complete.job");
    const axios = require("axios");
    const { RoadmapTopic, LearningGoal } = require("../models");
    const now = new Date("2026-06-01T20:00:00.000Z");
    jest.useFakeTimers().setSystemTime(now);

    const leanTopics = jest.fn().mockResolvedValue([
      {
        _id: "t1",
        goal_id: "g1",
        scheduled_date: new Date("2026-06-01T10:00:00.000Z"),
        estimated_duration: 90,
        status: "pending",
        is_deleted: false,
      },
    ]);
    RoadmapTopic.find.mockReturnValue({
      select: jest.fn().mockReturnValue({ lean: leanTopics }),
    });
    LearningGoal.find.mockReturnValue({
      lean: jest.fn().mockResolvedValue([
        { _id: "g1", user_id: "u1", status: "active", is_deleted: false },
      ]),
    });

    axios.post.mockResolvedValue({ data: { status: "success" } });

    const result = await runAutoCompleteCycle();
    expect(result.checked).toBe(1);
    expect(result.completed).toBe(1);
    expect(axios.post).toHaveBeenCalledTimes(1);
    expect(axios.post.mock.calls[0][0]).toBe(
      "http://ai.test/internal/auto-complete-topic",
    );

    jest.useRealTimers();
  });
});


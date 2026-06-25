process.env.NODE_ENV = "test";
process.env.JWT_ACCESS_SECRET = process.env.JWT_ACCESS_SECRET || "test-access-secret";

const jwt = require("jsonwebtoken");
const request = require("supertest");

jest.mock("../config/db", () => ({
  connectDB: jest.fn().mockResolvedValue(true),
}));

jest.mock("../jobs/reminder.job", () => ({
  startReminderJob: jest.fn(),
  stopReminderJob: jest.fn(),
}));

jest.mock("../config/logger", () => ({
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
  debug: jest.fn(),
  http: jest.fn(),
  add: jest.fn(),
  stream: { write: jest.fn() },
}));

jest.mock("../services/learningDelete.service", () => ({
  softDeleteLearningGoalById: jest.fn(),
}));

jest.mock("../services/notification.service", () => ({
  insert_and_dispatch: jest.fn(),
}));

jest.mock("../services/ai.service", () => ({
  callAIServer: jest.fn(),
  callAIAnalytics: jest.fn(),
  callAIInternal: jest.fn(),
}));

jest.mock("../models", () => ({
  User: { findById: jest.fn() },
  LearningGoal: {
    find: jest.fn(),
    findOne: jest.fn(),
    findOneAndUpdate: jest.fn(),
    updateOne: jest.fn(),
  },
  RoadmapTopic: {
    find: jest.fn(),
    findOne: jest.fn(),
    findOneAndUpdate: jest.fn(),
  },
  Task: {
    updateMany: jest.fn(),
    updateOne: jest.fn(),
  },
  UserSetting: { findOne: jest.fn() },
  ChatSession: {},
  ConversationHistory: {},
  Notification: {},
  ActivityLog: {},
  Integration: {},
  Friend: {},
}));

const app = require("../app");
const { User, LearningGoal, RoadmapTopic, Task } = require("../models");
const { softDeleteLearningGoalById } = require("../services/learningDelete.service");
const { insert_and_dispatch } = require("../services/notification.service");
const { callAIInternal } = require("../services/ai.service");

const USER_ID = "507f1f77bcf86cd799439011";
const GOAL_ID = "507f1f77bcf86cd799439099";
const TOPIC_ID = "507f1f77bcf86cd799439088";
const TASK_ID = "507f1f77bcf86cd799439077";

const makeToken = () =>
  jwt.sign({ userId: USER_ID }, process.env.JWT_ACCESS_SECRET, {
    expiresIn: "15m",
  });

const mockGoalTopicsForValidation = (topics) => {
  RoadmapTopic.find.mockReturnValue({
    select: jest.fn().mockReturnThis(),
    sort: jest.fn().mockReturnValue({
      lean: jest.fn().mockResolvedValue(topics),
    }),
  });
};

const mockGoalRefresh = (goal, topics = []) => {
  LearningGoal.findOne.mockReturnValue({
    lean: jest.fn().mockResolvedValue(goal),
  });
  RoadmapTopic.find.mockReturnValue({
    select: jest.fn().mockReturnThis(),
    sort: jest.fn().mockReturnValue({
      lean: jest.fn().mockResolvedValue(topics),
    }),
  });
};

/** Current session overdue — allowed for POST complete */
const overdueCurrentTopic = () => ({
  _id: TOPIC_ID,
  goal_id: GOAL_ID,
  order: 1,
  status: "pending",
  scheduled_date: new Date(Date.now() - 2 * 60 * 60 * 1000),
});

/** Current session within unlock window before schedule — allowed for POST skip */
const skippableCurrentTopic = () => ({
  _id: TOPIC_ID,
  goal_id: GOAL_ID,
  order: 1,
  status: "pending",
  scheduled_date: new Date(Date.now() + 2 * 60 * 60 * 1000),
});

describe("Learning API", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    LearningGoal.findOne.mockReset();
    LearningGoal.find.mockReset();
    LearningGoal.findOneAndUpdate.mockReset();
    RoadmapTopic.find.mockReset();
    RoadmapTopic.findOne.mockReset();
    RoadmapTopic.findOneAndUpdate.mockReset();
    LearningGoal.updateOne.mockReset();
    Task.updateMany.mockReset();
    Task.updateOne.mockReset();
    callAIInternal.mockReset();
    User.findById.mockResolvedValue({
      _id: USER_ID,
      is_active: true,
    });
  });

  test("GET /api/learning list route removed → 404", async () => {
    const res = await request(app)
      .get("/api/learning")
      .set("Authorization", `Bearer ${makeToken()}`);
    expect(res.status).toBe(404);
  });

  test("GET /api/learning/:goalId/sessions/:sessionId returns session detail", async () => {
    const savedGoal = {
      _id: GOAL_ID,
      user_id: USER_ID,
      subject: "python",
      title: "Python basics",
      roadmap_key: "basics",
      status: "active",
      start_date: new Date("2026-06-01"),
      end_date: new Date("2026-07-01"),
      total_topics: 2,
      completed_topics: 1,
      is_deleted: false,
    };

    const topics = [
      {
        _id: "507f1f77bcf86cd799439010",
        goal_id: GOAL_ID,
        order: 1,
        title: "Session 1",
        status: "completed",
        scheduled_date: new Date("2026-06-02T18:00:00Z"),
        estimated_duration: 90,
        completed_at: new Date("2026-06-03T18:00:00Z"),
        resources: [{ title: "Intro", url: "https://youtu.be/x" }],
      },
      {
        _id: TOPIC_ID,
        goal_id: GOAL_ID,
        order: 2,
        title: "Session 2",
        status: "pending",
        scheduled_date: new Date("2026-06-10T18:00:00Z"),
        estimated_duration: 90,
        resources: [{ title: "Control flow", url: "https://youtu.be/y" }],
      },
    ];

    LearningGoal.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue(savedGoal),
    });

    RoadmapTopic.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue(topics[1]),
    });

    RoadmapTopic.find.mockReturnValue({
      select: jest.fn().mockReturnThis(),
      sort: jest.fn().mockReturnValue({
        lean: jest.fn().mockResolvedValue(topics),
      }),
    });

    const res = await request(app)
      .get(`/api/learning/${GOAL_ID}/sessions/${TOPIC_ID}`)
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(res.status).toBe(200);
    expect(res.body.data.session).toEqual(
      expect.objectContaining({
        id: TOPIC_ID,
        order: 2,
        title: "Session 2",
        status: "pending",
        resources: [{ title: "Control flow", url: "https://youtu.be/y" }],
      }),
    );
    expect(res.body.data.session.is_current).toBe(true);
    expect(res.body.data.session.session_state).toBeDefined();
    expect(res.body.data.roadmap).toEqual(
      expect.objectContaining({
        id: GOAL_ID,
        title: "Python basics",
        language_key: "python",
      }),
    );
    expect(res.body.data.roadmap.sessions).toBeUndefined();
    expect(res.body.data.sessions).toBeUndefined();
    expect(res.body.data.language).toEqual({ key: "python", label: "Python" });
  });

  test("GET /api/learning/:goalId/sessions/:sessionId not found → 404", async () => {
    LearningGoal.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: GOAL_ID,
        user_id: USER_ID,
        is_deleted: false,
      }),
    });

    RoadmapTopic.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue(null),
    });

    const res = await request(app)
      .get(`/api/learning/${GOAL_ID}/sessions/${TOPIC_ID}`)
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(res.status).toBe(404);
  });

  test("PATCH /api/learning/:goalId/sessions/:sessionId reschedules via AI", async () => {
    const savedGoal = {
      _id: GOAL_ID,
      user_id: USER_ID,
      subject: "python",
      title: "Python",
      roadmap_key: "basics",
      status: "active",
      total_topics: 2,
      completed_topics: 0,
      is_deleted: false,
    };

    LearningGoal.findOne
      .mockReturnValueOnce({
        lean: jest.fn().mockResolvedValue(savedGoal),
      })
      .mockReturnValueOnce({
        lean: jest.fn().mockResolvedValue(savedGoal),
      });

    RoadmapTopic.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: TOPIC_ID,
        goal_id: GOAL_ID,
        order: 1,
        status: "pending",
      }),
    });

    RoadmapTopic.find.mockReturnValue({
      select: jest.fn().mockReturnThis(),
      sort: jest.fn().mockReturnValue({
        lean: jest.fn().mockResolvedValue([]),
      }),
    });

    callAIInternal.mockResolvedValue({ status: "success", rebased: false });

    const res = await request(app)
      .patch(`/api/learning/${GOAL_ID}/sessions/${TOPIC_ID}`)
      .set("Authorization", `Bearer ${makeToken()}`)
      .send({ scheduled_date: "2026-12-01" });

    expect(res.status).toBe(200);
    expect(callAIInternal).toHaveBeenCalledWith("/internal/reschedule-topic", {
      topic_id: TOPIC_ID,
      goal_id: GOAL_ID,
      user_id: USER_ID,
      scheduled_date: "2026-12-01",
    });
    expect(res.body.data.roadmap).toBeDefined();
  });

  test("PATCH /api/learning/:id/status pause → paused", async () => {
    LearningGoal.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: GOAL_ID,
        user_id: USER_ID,
        status: "active",
        is_deleted: false,
      }),
    });

    LearningGoal.findOneAndUpdate.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: GOAL_ID,
        status: "paused",
        paused_at: new Date(),
      }),
    });

    const res = await request(app)
      .patch(`/api/learning/${GOAL_ID}/status`)
      .set("Authorization", `Bearer ${makeToken()}`)
      .send({ status: "paused" });

    expect(res.status).toBe(200);
    expect(res.body.data.goal.status).toBe("paused");
  });

  test("PATCH /api/learning/:id/status resume → active", async () => {
    LearningGoal.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: GOAL_ID,
        user_id: USER_ID,
        status: "paused",
        is_deleted: false,
      }),
    });

    LearningGoal.findOneAndUpdate.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: GOAL_ID,
        status: "active",
        paused_at: null,
      }),
    });

    const res = await request(app)
      .patch(`/api/learning/${GOAL_ID}/status`)
      .set("Authorization", `Bearer ${makeToken()}`)
      .send({ status: "active" });

    expect(res.status).toBe(200);
    expect(res.body.data.goal.status).toBe("active");
  });

  test("PATCH /api/learning/:id/status cancel → soft-deletes and dispatches notifications", async () => {
    const collabId = "507f1f77bcf86cd799439066";
    LearningGoal.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: GOAL_ID,
        user_id: USER_ID,
        status: "active",
        is_deleted: false,
      }),
    });

    softDeleteLearningGoalById.mockResolvedValue({
      goal: { _id: GOAL_ID, is_deleted: true, title: "Python basics" },
      notifications: [
        {
          user_id: collabId,
          type: "learning_goal_deleted",
          title: "Shared learning plan removed",
          message: "Ali removed python basics from their plan.",
        },
      ],
    });
    insert_and_dispatch.mockResolvedValue({
      requested: 1,
      inserted: 1,
      dispatched_push: 0,
      dispatched_email: 0,
      failed: 0,
      results: [{ notification_id: "n1" }],
    });

    const res = await request(app)
      .patch(`/api/learning/${GOAL_ID}/status`)
      .set("Authorization", `Bearer ${makeToken()}`)
      .send({ status: "cancelled" });

    expect(res.status).toBe(200);
    expect(softDeleteLearningGoalById).toHaveBeenCalledWith(GOAL_ID, USER_ID);
    expect(insert_and_dispatch).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({ type: "learning_goal_deleted" }),
      ]),
    );
    expect(res.body.data.notifications.inserted).toBe(1);
    expect(res.body.data.goal.is_deleted).toBe(true);
  });

  test("PATCH status completed → 400", async () => {
    LearningGoal.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: GOAL_ID,
        user_id: USER_ID,
        status: "active",
        is_deleted: false,
      }),
    });

    const res = await request(app)
      .patch(`/api/learning/${GOAL_ID}/status`)
      .set("Authorization", `Bearer ${makeToken()}`)
      .send({ status: "completed" });

    expect(res.status).toBe(400);
  });

  test("PATCH /api/learning/:id/status resume triggers AI rebuild-schedule (non-blocking)", async () => {
    LearningGoal.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: GOAL_ID,
        user_id: USER_ID,
        is_deleted: false,
        status: "paused",
      }),
    });

    LearningGoal.findOneAndUpdate.mockReturnValue({
      lean: jest.fn().mockResolvedValue({ _id: GOAL_ID, status: "active" }),
    });

    const leanSettings = jest.fn().mockResolvedValue({
      preferred_learning_schedules: [{ id: "s1", label: "Default", slots: [{ day: 0, time: "18:00" }] }],
    });
    const { UserSetting } = require("../models");
    UserSetting.findOne.mockReturnValue({ lean: leanSettings });

    callAIInternal.mockResolvedValue({ status: "success", goals_updated: 1 });

    const res = await request(app)
      .patch(`/api/learning/${GOAL_ID}/status`)
      .set("Authorization", `Bearer ${makeToken()}`)
      .send({ status: "active" });

    expect(res.status).toBe(200);
    expect(callAIInternal).toHaveBeenCalledWith("/internal/rebuild-schedule", {
      user_id: USER_ID,
      new_schedule: [{ day: 0, time: "18:00" }],
    });
  });

  test("PATCH /api/learning/:goalId/sessions/:sessionId complete calls AI internal auto-complete-topic", async () => {
    const activeGoal = {
      _id: GOAL_ID,
      user_id: USER_ID,
      subject: "python",
      title: "Python",
      roadmap_key: "basics",
      is_deleted: false,
      status: "active",
      total_topics: 8,
      completed_topics: 3,
    };

    LearningGoal.findOne
      .mockReturnValueOnce({ lean: jest.fn().mockResolvedValue(activeGoal) })
      .mockReturnValueOnce({ lean: jest.fn().mockResolvedValue(activeGoal) });

    RoadmapTopic.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: TOPIC_ID,
        goal_id: GOAL_ID,
        order: 1,
        status: "pending",
      }),
    });

    mockGoalTopicsForValidation([overdueCurrentTopic()]);

    callAIInternal.mockResolvedValue({ status: "success", goal_completed: false, next_session: null });

    const res = await request(app)
      .patch(`/api/learning/${GOAL_ID}/sessions/${TOPIC_ID}`)
      .set("Authorization", `Bearer ${makeToken()}`)
      .send({ status: "completed" });

    expect(res.status).toBe(200);
    expect(callAIInternal).toHaveBeenCalledWith("/internal/auto-complete-topic", {
      topic_id: expect.any(String),
      goal_id: expect.any(String),
      user_id: USER_ID,
    });
    expect(res.body.data.roadmap).toBeDefined();
  });

  test("PATCH /api/learning/:goalId/sessions/:sessionId skip calls AI internal skip-topic", async () => {
    const activeGoal = {
      _id: GOAL_ID,
      user_id: USER_ID,
      subject: "python",
      title: "Python",
      roadmap_key: "basics",
      is_deleted: false,
      status: "active",
      total_topics: 8,
      completed_topics: 1,
    };

    LearningGoal.findOne
      .mockReturnValueOnce({ lean: jest.fn().mockResolvedValue(activeGoal) })
      .mockReturnValueOnce({ lean: jest.fn().mockResolvedValue(activeGoal) });

    RoadmapTopic.findOne.mockReturnValue({
      lean: jest.fn().mockResolvedValue({
        _id: TOPIC_ID,
        goal_id: GOAL_ID,
        order: 1,
        status: "pending",
      }),
    });

    mockGoalTopicsForValidation([skippableCurrentTopic()]);

    callAIInternal.mockResolvedValue({ status: "success" });

    const res = await request(app)
      .patch(`/api/learning/${GOAL_ID}/sessions/${TOPIC_ID}`)
      .set("Authorization", `Bearer ${makeToken()}`)
      .send({ status: "skipped" });

    expect(res.status).toBe(200);
    expect(callAIInternal).toHaveBeenCalledWith("/internal/skip-topic", {
      topic_id: expect.any(String),
      goal_id: expect.any(String),
      user_id: USER_ID,
    });
    expect(res.body.data.roadmap).toBeDefined();
  });
});

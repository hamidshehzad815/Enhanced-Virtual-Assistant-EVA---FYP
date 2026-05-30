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

jest.mock("../models", () => ({
  Task: { find: jest.fn(), updateMany: jest.fn() },
  User: { find: jest.fn() },
  LearningGoal: { find: jest.fn() },
}));

jest.mock("../services/notification.service", () => ({
  insert_and_dispatch: jest.fn(),
}));

const { sendReminderNotifications, sendLearningOverdueAlerts } = require("../jobs/reminder.job");
const { Task, User, LearningGoal } = require("../models");
const { insert_and_dispatch } = require("../services/notification.service");

const USER_ID = "507f1f77bcf86cd799439011";
const PLAN_ID = "507f1f77bcf86cd799439022";
const TOPIC_ID = "507f1f77bcf86cd799439033";

describe("Reminder job — learning topics", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    Task.updateMany.mockResolvedValue({});
    insert_and_dispatch.mockResolvedValue({
      requested: 1,
      inserted: 1,
      dispatched_push: 0,
      dispatched_email: 0,
      failed: 0,
      results: [],
    });
  });

  test("learning-linked task emits topic_reminder with push_data", async () => {
    const now = new Date("2026-05-13T12:00:00.000Z");
    const due = new Date(now.getTime() + 29.5 * 60 * 1000);

    const leanTasks = jest.fn().mockResolvedValue([
      {
        _id: "task1",
        owner_id: USER_ID,
        title: "Learn: Session 1",
        due_datetime: due,
        reminder_minutes_before: 30,
        learning_plan_id: PLAN_ID,
        learning_topic_id: TOPIC_ID,
      },
    ]);
    Task.find.mockReturnValue({
      select: jest.fn().mockReturnValue({ lean: leanTasks }),
    });

    User.find.mockReturnValue({
      lean: jest.fn().mockResolvedValue([{ _id: USER_ID, timezone: "UTC" }]),
    });

    const leanGoals = jest.fn().mockResolvedValue([
      { _id: PLAN_ID, title: "Learn Python — basics" },
    ]);
    LearningGoal.find.mockReturnValue({
      select: jest.fn().mockReturnValue({ lean: leanGoals }),
    });

    await sendReminderNotifications(now);

    expect(insert_and_dispatch).toHaveBeenCalledTimes(1);
    const batch = insert_and_dispatch.mock.calls[0][0];
    expect(batch).toHaveLength(1);
    expect(batch[0].type).toBe("topic_reminder");
    expect(batch[0].reference_type).toBe("topic");
    expect(batch[0].reference_id).toBe(TOPIC_ID);
    expect(batch[0].action_required).toBe(true);
    expect(batch[0].push_data.learning_goal_id).toBe(PLAN_ID);
    expect(batch[0].push_data.learning_topic_id).toBe(TOPIC_ID);
    expect(batch[0].push_data.suggested_action).toBe("complete_learning_topic");
  });

  test("overdue learning-linked task emits learning overdue topic_reminder and marks overdue_notified_at", async () => {
    const now = new Date("2026-05-13T12:00:00.000Z");
    const due = new Date(now.getTime() - 60 * 1000);

    const leanTasks = jest.fn().mockResolvedValue([
      {
        _id: "task1",
        owner_id: USER_ID,
        title: "Learn: Session 1",
        due_datetime: due,
        learning_plan_id: PLAN_ID,
        learning_topic_id: TOPIC_ID,
      },
    ]);
    Task.find.mockReturnValue({
      select: jest.fn().mockReturnValue({ lean: leanTasks }),
    });

    User.find.mockReturnValue({
      lean: jest.fn().mockResolvedValue([{ _id: USER_ID, timezone: "UTC" }]),
    });

    LearningGoal.find.mockReturnValue({
      lean: jest.fn().mockResolvedValue([
        { _id: PLAN_ID, title: "Learn Python — basics", status: "active", is_deleted: false },
      ]),
    });

    await sendLearningOverdueAlerts(now);

    expect(insert_and_dispatch).toHaveBeenCalledTimes(1);
    const batch = insert_and_dispatch.mock.calls[0][0];
    expect(batch).toHaveLength(1);
    expect(batch[0].type).toBe("topic_reminder");
    expect(batch[0].title).toBe("Learning session overdue");
    expect(batch[0].reference_id).toBe(TOPIC_ID);
    expect(Task.updateMany).toHaveBeenCalledTimes(1);
    expect(Task.updateMany.mock.calls[0][0]._id.$in).toEqual(["task1"]);
  });
});

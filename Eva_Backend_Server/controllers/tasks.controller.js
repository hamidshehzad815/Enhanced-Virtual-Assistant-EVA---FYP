/**
 * Tasks Controller
 * Phase 10 task page endpoints.
 */

const mongoose = require("mongoose");
const jwt = require("jsonwebtoken");
const { Task, ActivityLog, Notification, UserSetting } = require("../models");
const { isBehavioralAnalyticsEnabled } = require("../utils/behavioralSettings");
const { toLocalDayRangeUtc } = require("../utils/timezone");
const {
  BadRequestError,
  NotFoundError,
  ConflictError,
} = require("../middleware/errorHandler");
const { serializeTaskForApi, isLearningTask, LEARNING_TASK_EDIT_BLOCKED_MESSAGE } = require("../utils/taskDisplayStatus");
const {
  collectCollaboratorUserIds,
  loadCollaboratorProfiles,
  serializeCollaborators,
} = require("../utils/collaboratorDetails");

const TASK_LIST_PROJECTION =
  "title description due_datetime duration priority status learning_plan_id learning_topic_id completed_at collaborators";

/**
 * Serialize many tasks, batch-populating collaborator profiles in one query.
 */
const serializeTasksWithCollaborators = async (
  tasks,
  now,
  timezone,
  options = {},
) => {
  const list = Array.isArray(tasks) ? tasks : [];
  const profileMap = await loadCollaboratorProfiles(
    collectCollaboratorUserIds(list),
  );
  return list.map((task) =>
    serializeTaskForApi(task, now, timezone, {
      ...options,
      collaborators: serializeCollaborators(task.collaborators, profileMap),
    }),
  );
};

/**
 * Serialize a single task with its collaborators populated.
 */
const serializeTaskWithCollaborators = async (
  task,
  now,
  timezone,
  options = {},
) => {
  const [serialized] = await serializeTasksWithCollaborators(
    [task],
    now,
    timezone,
    options,
  );
  return serialized;
};
const { withApiTimezone } = require("../utils/apiDateTime");
const {
  notifyOwnerOfCollaborationResponse,
} = require("../services/collaborationNotifications");
const { insert_and_dispatch } = require("../services/notification.service");
const { buildTaskRescheduledNotification } = require("../utils/taskRescheduleNotification");
const { resolveGoogleCalendarSync } = require("../utils/googleCalendarSync");
const { deleteEvent } = require("../services/googleCalendar.service");

const STATUS_VALUES = new Set(["pending", "complete"]);
const STORED_STATUS_FILTER = {
  pending: ["pending", "ongoing"],
  complete: ["complete"],
};
const PRIORITY_VALUES = new Set(["low", "medium", "high"]);
const COLLAB_ACTIONS = new Set(["accept", "reject"]);

const resolveUserTimezone = (req) => req.user?.timezone || "UTC";

const assertTaskIsEditable = (task) => {
  if (!isLearningTask(task)) {
    return;
  }
  throw new ConflictError(LEARNING_TASK_EDIT_BLOCKED_MESSAGE, {
    conflict_type: "learning_session_read_only",
    learning_goal_id: String(task.learning_plan_id),
    learning_session_id: task.learning_topic_id
      ? String(task.learning_topic_id)
      : null,
  });
};

const PRIORITY_ALIASES = new Map([
  ["high", "high"],
  ["urgent", "high"],
  ["critical", "high"],
  ["immediate", "high"],
  ["asap", "high"],
  ["important", "high"],
  ["medium", "medium"],
  ["normal", "medium"],
  ["standard", "medium"],
  ["moderate", "medium"],
  ["average", "medium"],
  ["regular", "medium"],
  ["low", "low"],
  ["minor", "low"],
  ["trivial", "low"],
  ["backburner", "low"],
  ["back burner", "low"],
  ["background", "low"],
  ["optional", "low"],
]);

const STATUS_ALIASES = new Map([
  ["pending", "pending"],
  ["ongoing", "pending"],
  ["in progress", "pending"],
  ["inprogress", "pending"],
  ["active", "pending"],
  ["complete", "complete"],
  ["completed", "complete"],
  ["done", "complete"],
  ["finished", "complete"],
  ["resolved", "complete"],
  ["closed", "complete"],
  ["delivered", "complete"],
  ["fulfilled", "complete"],
]);

const normalizeEnumInput = (value) => String(value || "")
  .toLowerCase()
  .replace(/[_-]+/g, " ")
  .replace(/\s+/g, " ")
  .trim();

const normalizePriorityValue = (value) => {
  const normalized = normalizeEnumInput(value);
  return PRIORITY_ALIASES.get(normalized) || "";
};

const normalizeStatusValue = (value) => {
  const normalized = normalizeEnumInput(value);
  return STATUS_ALIASES.get(normalized) || "";
};

const normalizeCollaborationAction = (value) => {
  const normalized = normalizeEnumInput(value);
  return COLLAB_ACTIONS.has(normalized) ? normalized : "";
};

const toDateOrNull = (value) => {
  if (!value) {
    return null;
  }
  const parsed = value instanceof Date ? value : new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};

const getIsoWeekNumber = (inputDate) => {
  const date = new Date(Date.UTC(
    inputDate.getUTCFullYear(),
    inputDate.getUTCMonth(),
    inputDate.getUTCDate(),
  ));
  const dayNum = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  return Math.ceil((((date - yearStart) / 86400000) + 1) / 7);
};

const buildCompletedLogPayload = (task) => {
  const completedAt = toDateOrNull(task.completed_at) || new Date();
  const dueAt = toDateOrNull(task.due_datetime);
  const createdAt = toDateOrNull(task.created_at);

  let wasOnTime = null;
  if (dueAt) {
    wasOnTime = completedAt.getTime() <= dueAt.getTime();
  }

  let timeTakenMinutes = null;
  if (createdAt) {
    const minutes = Math.floor(
      (completedAt.getTime() - createdAt.getTime()) / (1000 * 60),
    );
    timeTakenMinutes = Math.max(0, minutes);
  }

  return {
    user_id: task.owner_id,
    task_id: task._id,
    action_type: "task_completed",
    action_timestamp: completedAt,
    day_of_week: completedAt.getUTCDay() === 0 ? 6 : completedAt.getUTCDay() - 1,
    hour_of_day: completedAt.getUTCHours(),
    week_number: getIsoWeekNumber(completedAt),
    task_priority: task.priority || null,
    subject: task.title || null,
    source: "tasks_page",
    time_taken_minutes: timeTakenMinutes,
    was_on_time: wasOnTime,
    scheduled_hour: dueAt ? dueAt.getUTCHours() : null,
    scheduled_day: dueAt
      ? (dueAt.getUTCDay() === 0 ? 6 : dueAt.getUTCDay() - 1)
      : null,
  };
};

const getCollaborationTokenSecret = () =>
  process.env.COLLAB_ACTION_SECRET || process.env.JWT_ACCESS_SECRET || "";

const verifyCollaborationToken = (token) => {
  const secret = getCollaborationTokenSecret();
  if (!secret) {
    throw new BadRequestError("Collaboration response is not configured");
  }

  try {
    return jwt.verify(token, secret);
  } catch (_error) {
    throw new BadRequestError("Invalid or expired collaboration response link");
  }
};

const sameObjectId = (a, b) => String(a) === String(b);

/**
 * Give an accepting collaborator their own copy of a shared task, so it shows
 * on their calendar/tasks (which are filtered by owner_id). Mirrors the
 * learning-plan clone flow. Idempotent: skips if a copy already exists.
 */
const cloneTaskForCollaborator = async (ownerTask, collaboratorUserId) => {
  const collabOid = new mongoose.Types.ObjectId(collaboratorUserId);

  const existing = await Task.findOne({
    source_task_id: ownerTask._id,
    owner_id: collabOid,
    is_deleted: { $ne: true },
  }).lean();
  if (existing) {
    return existing;
  }

  const now = new Date();
  return Task.create({
    owner_id: collabOid,
    title: ownerTask.title,
    description: ownerTask.description,
    due_datetime: ownerTask.due_datetime,
    duration: ownerTask.duration,
    priority: ownerTask.priority,
    status: "pending",
    source: ownerTask.source || "eva",
    scheduled_by: ownerTask.scheduled_by || "manual",
    collaborators: [],
    source_task_id: ownerTask._id,
    reminder_minutes_before: ownerTask.reminder_minutes_before,
    is_deleted: false,
    created_at: now,
    updated_at: now,
  });
};

const markCollaborationNotificationHandled = async ({
  userId,
  taskId,
  action,
  notificationId = null,
}) => {
  const query = {
    user_id: userId,
    type: "collaboration_invite",
    reference_type: "task",
    reference_id: taskId,
  };

  if (notificationId && mongoose.Types.ObjectId.isValid(notificationId)) {
    query._id = new mongoose.Types.ObjectId(notificationId);
  }

  await Notification.findOneAndUpdate(
    query,
    {
      $set: {
        is_read: true,
        action_taken: action === "accept" ? "accepted" : "rejected",
        action_required: false,
        updated_at: new Date(),
      },
    },
    {
      sort: { created_at: -1 },
    },
  );
};

const applyCollaborationAction = async ({
  taskId,
  collaboratorUserId,
  action,
  notificationId = null,
}) => {
  if (!mongoose.Types.ObjectId.isValid(taskId)) {
    throw new BadRequestError("Invalid task id");
  }

  if (!mongoose.Types.ObjectId.isValid(collaboratorUserId)) {
    throw new BadRequestError("Invalid collaborator id");
  }

  const taskObjectId = new mongoose.Types.ObjectId(taskId);
  const collaboratorObjectId = new mongoose.Types.ObjectId(collaboratorUserId);
  const newStatus = action === "accept" ? "accepted" : "rejected";

  const task = await Task.findOne({
    _id: taskObjectId,
    is_deleted: false,
    collaborators: {
      $elemMatch: {
        user_id: collaboratorObjectId,
      },
    },
  }).lean();

  if (!task) {
    throw new NotFoundError("Task not found for this collaborator");
  }

  const collaboratorRow = Array.isArray(task.collaborators)
    ? task.collaborators.find((row) => sameObjectId(row.user_id, collaboratorObjectId))
    : null;

  if (!collaboratorRow) {
    throw new NotFoundError("Collaborator record not found");
  }

  if (String(collaboratorRow.status || "").toLowerCase() !== "pending") {
    await markCollaborationNotificationHandled({
      userId: collaboratorObjectId,
      taskId: taskObjectId,
      action,
      notificationId,
    });
    return {
      task,
      already_responded: true,
      current_status: collaboratorRow.status,
    };
  }

  const updatedTask = await Task.findOneAndUpdate(
    {
      _id: taskObjectId,
      is_deleted: false,
      collaborators: {
        $elemMatch: {
          user_id: collaboratorObjectId,
          status: "pending",
        },
      },
    },
    {
      $set: {
        "collaborators.$.status": newStatus,
        updated_at: new Date(),
      },
    },
    { new: true },
  ).lean();

  if (!updatedTask) {
    throw new ConflictError("This collaboration invite was already handled");
  }

  // On accept, give the collaborator their own copy so it shows on their side.
  let collaboratorTaskId = null;
  if (action === "accept") {
    const collabTask = await cloneTaskForCollaborator(
      updatedTask,
      collaboratorUserId,
    );
    collaboratorTaskId = collabTask ? collabTask._id : null;
  }

  await markCollaborationNotificationHandled({
    userId: collaboratorObjectId,
    taskId: taskObjectId,
    action,
    notificationId,
  });

  await notifyOwnerOfCollaborationResponse({
    ownerId: updatedTask.owner_id,
    collaboratorUserId,
    action,
    referenceType: "task",
    referenceId: taskObjectId,
    itemTitle: updatedTask.title,
  });

  return {
    task: updatedTask,
    collaborator_task_id: collaboratorTaskId,
    already_responded: false,
    current_status: newStatus,
  };
};

const renderCollaborationHtml = ({ title, message }) => `
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>${title}</title>
    <style>
      body { font-family: Arial, sans-serif; background:#f5f7fb; padding:24px; color:#111827; }
      .card { max-width:620px; margin:0 auto; background:#fff; border-radius:10px; padding:24px; box-shadow:0 8px 28px rgba(0,0,0,0.08); }
      h1 { margin:0 0 10px; font-size:22px; }
      p { margin:0; color:#374151; line-height:1.5; }
    </style>
  </head>
  <body>
    <div class="card">
      <h1>${title}</h1>
      <p>${message}</p>
    </div>
  </body>
</html>
`;

const parsePositiveInt = (value, fallback) => {
  const parsed = Number.parseInt(value, 10);
  if (Number.isNaN(parsed) || parsed <= 0) {
    return fallback;
  }
  return parsed;
};

const parseDateRange = (dateValue, timezoneValue) => {
  if (!dateValue) {
    return null;
  }

  const range = toLocalDayRangeUtc(dateValue, timezoneValue);
  if (!range) {
    throw new BadRequestError("Invalid date query format");
  }
  return { start: range.start, end: range.end };
};

const applyTaskListFilters = (query, req, { skipUpcomingOnly = false } = {}) => {
  let normalizedStatus = null;

  if (req.query.status) {
    normalizedStatus = normalizeStatusValue(req.query.status);
    if (!STATUS_VALUES.has(normalizedStatus)) {
      throw new BadRequestError("Invalid status filter");
    }
    query.status = { $in: STORED_STATUS_FILTER[normalizedStatus] };
  }

  if (req.query.priority) {
    const priority = normalizePriorityValue(req.query.priority);
    if (!PRIORITY_VALUES.has(priority)) {
      throw new BadRequestError("Invalid priority filter");
    }
    query.priority = priority;
  }

  if (req.query.date) {
    const range = parseDateRange(req.query.date, req.user?.timezone);
    query.due_datetime = {
      $gte: range.start,
      $lte: range.end,
    };
  } else if (!skipUpcomingOnly && normalizedStatus !== "complete") {
    query.due_datetime = {
      $gte: new Date(),
    };
  }

  if (req.query.subject) {
    const subject = String(req.query.subject).trim();
    if (subject) {
      query.title = { $regex: subject, $options: "i" };
    }
  }

  return normalizedStatus;
};

/**
 * GET /api/tasks
 * Fetch paginated task list for authenticated user.
 */
const getTasks = async (req, res, next) => {
  try {
    const page = parsePositiveInt(req.query.page, 1);
    const limit = Math.min(parsePositiveInt(req.query.limit, 20), 100);
    const skip = (page - 1) * limit;
    let normalizedStatus = null;

    const query = {
      owner_id: req.userId,
      is_deleted: false,
    };

    normalizedStatus = applyTaskListFilters(query, req);

    const [tasks, total] = await Promise.all([
      Task.find(query)
        .select(TASK_LIST_PROJECTION)
        .sort({ due_datetime: 1 })
        .skip(skip)
        .limit(limit)
        .lean(),
      Task.countDocuments(query),
    ]);

    const now = new Date();
    const timezone = resolveUserTimezone(req);
    const serializedTasks = await serializeTasksWithCollaborators(
      tasks,
      now,
      timezone,
    );
    res.json({
      status: "success",
      data: withApiTimezone(
        {
        tasks: serializedTasks,
        pagination: {
          page,
          limit,
          total,
          total_pages: Math.max(1, Math.ceil(total / limit)),
        },
        filters: {
          date: req.query.date || null,
          priority: req.query.priority || null,
          status: req.query.status || null,
          subject: req.query.subject || null,
        },
      },
        timezone,
      ),
    });
  } catch (error) {
    next(error);
  }
};

/**
 * GET /api/tasks/calendar
 * Fetch all user tasks for calendar view (no date-range params).
 */
const getCalendarTasks = async (req, res, next) => {
  try {
    const timezone = resolveUserTimezone(req);

    const query = {
      owner_id: req.userId,
      is_deleted: false,
    };

    applyTaskListFilters(query, req, { skipUpcomingOnly: true });

    const tasks = await Task.find(query)
      .select(TASK_LIST_PROJECTION)
      .sort({ due_datetime: 1 })
      .lean();

    const now = new Date();
    const serializedTasks = await serializeTasksWithCollaborators(
      tasks,
      now,
      timezone,
    );
    res.json({
      status: "success",
      data: withApiTimezone(
        {
          tasks: serializedTasks,
          total: serializedTasks.length,
        },
        timezone,
      ),
    });
  } catch (error) {
    next(error);
  }
};

/**
 * GET /api/tasks/:id
 * Fetch single task owned by authenticated user.
 */
const getTaskById = async (req, res, next) => {
  try {
    const { id } = req.params;
    if (!mongoose.Types.ObjectId.isValid(id)) {
      throw new BadRequestError("Invalid task id");
    }

    const task = await Task.findOne({
      _id: id,
      owner_id: req.userId,
      is_deleted: false,
    })
      .select(TASK_LIST_PROJECTION)
      .lean();

    if (!task) {
      throw new NotFoundError("Task not found");
    }

    const timezone = resolveUserTimezone(req);
    res.json({
      status: "success",
      data: withApiTimezone(
        {
          task: await serializeTaskWithCollaborators(task, new Date(), timezone, {
            includeDescription: true,
          }),
        },
        timezone,
      ),
    });
  } catch (error) {
    next(error);
  }
};

/**
 * PATCH /api/tasks/:id
 * Update editable task fields (calendar / task detail).
 */
const updateTask = async (req, res, next) => {
  try {
    const { id } = req.params;
    if (!mongoose.Types.ObjectId.isValid(id)) {
      throw new BadRequestError("Invalid task id");
    }

    const existingTask = await Task.findOne({
      _id: id,
      owner_id: req.userId,
      is_deleted: false,
    }).lean();

    if (!existingTask) {
      throw new NotFoundError("Task not found");
    }

    assertTaskIsEditable(existingTask);

    const update = {};
    const body = req.body || {};

    if (Object.prototype.hasOwnProperty.call(body, "title")) {
      const title = String(body.title || "").trim();
      if (!title) {
        throw new BadRequestError("title cannot be empty");
      }
      if (title.length > 200) {
        throw new BadRequestError("title cannot exceed 200 characters");
      }
      update.title = title;
    }

    if (Object.prototype.hasOwnProperty.call(body, "description")) {
      if (body.description == null || body.description === "") {
        update.description = null;
      } else {
        const description = String(body.description).trim();
        if (description.length > 1000) {
          throw new BadRequestError("description cannot exceed 1000 characters");
        }
        update.description = description;
      }
    }

    if (Object.prototype.hasOwnProperty.call(body, "due_datetime")) {
      const dueDate = toDateOrNull(body.due_datetime);
      if (!dueDate) {
        throw new BadRequestError("due_datetime must be a valid datetime");
      }
      update.due_datetime = dueDate;
      update.reminder_sent_at = null;
      update.overdue_notified_at = null;
    }

    if (Object.prototype.hasOwnProperty.call(body, "duration")) {
      const duration = Number(body.duration);
      if (!Number.isFinite(duration) || duration < 5 || duration > 1440) {
        throw new BadRequestError("duration must be between 5 and 1440 minutes");
      }
      update.duration = duration;
    }

    if (Object.prototype.hasOwnProperty.call(body, "priority")) {
      const priority = normalizePriorityValue(body.priority);
      if (!PRIORITY_VALUES.has(priority)) {
        throw new BadRequestError("priority must be one of low, medium, high");
      }
      update.priority = priority;
    }

    let normalizedStatus = null;
    if (Object.prototype.hasOwnProperty.call(body, "status")) {
      normalizedStatus = normalizeStatusValue(body.status);
      if (!STATUS_VALUES.has(normalizedStatus)) {
        throw new BadRequestError("status must be one of pending, complete");
      }
      update.status = normalizedStatus;
      update.completed_at = normalizedStatus === "complete" ? new Date() : null;
    }

    if (!Object.keys(update).length) {
      throw new BadRequestError("At least one updatable field is required");
    }

    update.updated_at = new Date();

    const task = await Task.findOneAndUpdate(
      { _id: id, owner_id: req.userId, is_deleted: false },
      { $set: update },
      { new: true },
    ).lean();

    if (!task) {
      throw new NotFoundError("Task not found");
    }

    const dueDatetimeChanged =
      Object.prototype.hasOwnProperty.call(body, "due_datetime")
      && toDateOrNull(existingTask.due_datetime)?.getTime()
        !== toDateOrNull(task.due_datetime)?.getTime();

    if (dueDatetimeChanged) {
      try {
        await insert_and_dispatch([
          buildTaskRescheduledNotification({
            userId: req.userId,
            user: req.user,
            taskTitle: task.title,
            dueDatetime: task.due_datetime,
            timezone: resolveUserTimezone(req),
            referenceType: "task",
            referenceId: String(task._id),
            taskId: String(task._id),
          }),
        ]);
      } catch (error) {
        console.warn(
          `[TasksController] Failed to dispatch reschedule notification for task ${task._id}: ${error.message}`,
        );
      }
    }

    if (
      normalizedStatus === "complete"
      && String(existingTask.status || "").toLowerCase() !== "complete"
    ) {
      try {
        const userSettings = await UserSetting.findOne({ user_id: req.userId }).lean();
        if (isBehavioralAnalyticsEnabled(userSettings)) {
          await ActivityLog.create(buildCompletedLogPayload(task));
        }
      } catch (error) {
        console.warn(
          `[TasksController] Failed to insert task_completed log for task ${task._id}: ${error.message}`,
        );
      }
    }

    const timezone = resolveUserTimezone(req);
    res.json({
      status: "success",
      message: "Task updated",
      data: withApiTimezone(
        {
          task: await serializeTaskWithCollaborators(task, new Date(), timezone, {
            includeDescription: true,
          }),
        },
        timezone,
      ),
    });
  } catch (error) {
    next(error);
  }
};

/**
 * PATCH /api/tasks/:id/status
 * Update task status from tasks page UI.
 */
const updateTaskStatus = async (req, res, next) => {
  try {
    const { id } = req.params;
    const { status } = req.body;

    if (!mongoose.Types.ObjectId.isValid(id)) {
      throw new BadRequestError("Invalid task id");
    }

    const normalizedStatus = normalizeStatusValue(status);
    if (!STATUS_VALUES.has(normalizedStatus)) {
      throw new BadRequestError(
        "status must be one of pending, complete",
      );
    }

    const existingTask = await Task.findOne({
      _id: id,
      owner_id: req.userId,
      is_deleted: false,
    }).lean();

    if (!existingTask) {
      throw new NotFoundError("Task not found");
    }

    assertTaskIsEditable(existingTask);

    const update = {
      status: normalizedStatus,
      updated_at: new Date(),
    };

    if (normalizedStatus === "complete") {
      update.completed_at = new Date();
    } else {
      update.completed_at = null;
    }

    const task = await Task.findOneAndUpdate(
      { _id: id, owner_id: req.userId, is_deleted: false },
      { $set: update },
      { new: true },
    ).lean();

    if (!task) {
      throw new NotFoundError("Task not found");
    }

    if (
      normalizedStatus === "complete"
      && String(existingTask.status || "").toLowerCase() !== "complete"
    ) {
      try {
        const userSettings = await UserSetting.findOne({ user_id: req.userId }).lean();
        if (isBehavioralAnalyticsEnabled(userSettings)) {
          await ActivityLog.create(
            buildCompletedLogPayload(task),
          );
        }
      } catch (error) {
        console.warn(
          `[TasksController] Failed to insert task_completed log for task ${task._id}: ${error.message}`,
        );
      }
    }

    const timezone = resolveUserTimezone(req);
    res.json({
      status: "success",
      message: "Task status updated",
      data: withApiTimezone(
        {
          task: await serializeTaskWithCollaborators(task, new Date(), timezone, {
            includeDescription: true,
          }),
        },
        timezone,
      ),
    });
  } catch (error) {
    next(error);
  }
};

/**
 * DELETE /api/tasks/:id
 * Soft delete task from tasks page UI.
 */
const deleteTask = async (req, res, next) => {
  try {
    const { id } = req.params;
    if (!mongoose.Types.ObjectId.isValid(id)) {
      throw new BadRequestError("Invalid task id");
    }

    const existingTask = await Task.findOne({
      _id: id,
      owner_id: req.userId,
      is_deleted: false,
    }).lean();

    if (!existingTask) {
      throw new NotFoundError("Task not found");
    }

    assertTaskIsEditable(existingTask);

    const now = new Date();
    const task = await Task.findOneAndUpdate(
      {
        _id: id,
        owner_id: req.userId,
        is_deleted: false,
      },
      {
        $set: {
          is_deleted: true,
          deleted_at: now,
          updated_at: now,
        },
      },
      { new: true },
    ).lean();

    if (!task) {
      throw new NotFoundError("Task not found");
    }

    try {
      const userSettings = await UserSetting.findOne({ user_id: req.userId }).lean();
      const googleIntegration = await resolveGoogleCalendarSync(req.userId, userSettings);
      const eventId = String(task.google_calendar_event_id || "").trim();
      if (googleIntegration && eventId) {
        await deleteEvent(
          googleIntegration.access_token,
          googleIntegration.calendar_id || "primary",
          eventId,
        );
      }
    } catch (_error) {
      // Calendar sync is best-effort and must not block task deletion.
    }

    res.json({
      status: "success",
      message: "Task deleted",
      data: {
        task_id: task._id,
        is_deleted: true,
      },
    });
  } catch (error) {
    next(error);
  }
};

/**
 * POST /api/tasks/:id/collaborators/respond
 * Authenticated collaborator accepts/rejects invite.
 */
const respondToCollaborationInvite = async (req, res, next) => {
  try {
    const { id } = req.params;
    const action = normalizeCollaborationAction(req.body?.action);
    if (!action) {
      throw new BadRequestError('action must be "accept" or "reject"');
    }

    const result = await applyCollaborationAction({
      taskId: id,
      collaboratorUserId: req.userId,
      action,
    });

    const verb = action === "accept" ? "accepted" : "rejected";
    const message = result.already_responded
      ? `Invite already ${String(result.current_status || "").toLowerCase()}.`
      : `Collaboration invite ${verb}.`;

    res.json({
      status: "success",
      message,
      data: {
        task_id: String(result.task._id),
        collaboration_status: result.current_status,
        already_responded: result.already_responded,
      },
    });
  } catch (error) {
    next(error);
  }
};

/**
 * GET /api/tasks/collaboration/respond?token=...
 * Web/email testing endpoint for Accept/Reject links.
 */
const respondToCollaborationInviteViaLink = async (req, res, next) => {
  try {
    const token = String(req.query?.token || "").trim();
    if (!token) {
      throw new BadRequestError("Missing response token");
    }

    const payload = verifyCollaborationToken(token);
    const action = normalizeCollaborationAction(payload?.action);
    if (!action) {
      throw new BadRequestError("Invalid action in response token");
    }

    const referenceType = String(payload?.reference_type || "").toLowerCase();
    const referenceId = String(payload?.reference_id || payload?.task_id || "");
    const userId = String(payload?.user_id || "");
    const notificationId = payload?.notification_id ? String(payload.notification_id) : null;

    const { applyLearningCollaborationAction } = require("../services/learningCollaboration.service");

    let result;
    let isLearningInvite = referenceType === "learning_goal";

    if (isLearningInvite) {
      result = await applyLearningCollaborationAction({
        goalId: referenceId,
        collaboratorUserId: userId,
        action,
        notificationId,
      });
    } else {
      try {
        result = await applyCollaborationAction({
          taskId: referenceId,
          collaboratorUserId: userId,
          action,
          notificationId,
        });
      } catch (taskErr) {
        if (taskErr instanceof NotFoundError && referenceId) {
          result = await applyLearningCollaborationAction({
            goalId: referenceId,
            collaboratorUserId: userId,
            action,
            notificationId,
          });
          isLearningInvite = true;
        } else {
          throw taskErr;
        }
      }
    }

    const verbPast = action === "accept" ? "accepted" : "rejected";
    let successMessage = result.already_responded
      ? `This invitation was already ${String(result.current_status || "").toLowerCase()}.`
      : `You have ${verbPast} this collaboration invite successfully.`;

    if (
      !result.already_responded
      && action === "accept"
      && isLearningInvite
      && result.collaborator_goal_id
    ) {
      successMessage += " Your own copy of the learning plan is ready in EVA.";
    }

    const html = renderCollaborationHtml({
      title: result.already_responded ? "Already Responded" : "Response Saved",
      message: successMessage,
    });

    res.status(200).type("html").send(html);
  } catch (error) {
    if (error instanceof BadRequestError || error instanceof NotFoundError || error instanceof ConflictError) {
      const html = renderCollaborationHtml({
        title: "Unable to Process Invite",
        message: error.message,
      });
      return res.status(error.statusCode || 400).type("html").send(html);
    }
    return next(error);
  }
};

module.exports = {
  getTasks,
  getCalendarTasks,
  getTaskById,
  updateTask,
  updateTaskStatus,
  deleteTask,
  respondToCollaborationInvite,
  respondToCollaborationInviteViaLink,
  // Exported for tests.
  applyCollaborationAction,
  cloneTaskForCollaborator,
};

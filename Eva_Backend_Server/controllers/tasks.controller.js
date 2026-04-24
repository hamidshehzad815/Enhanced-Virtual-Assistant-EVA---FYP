/**
 * Tasks Controller
 * Phase 10 task page endpoints.
 */

const mongoose = require("mongoose");
const { Task, ActivityLog } = require("../models");
const { toLocalDayRangeUtc } = require("../utils/timezone");
const {
  BadRequestError,
  NotFoundError,
} = require("../middleware/errorHandler");

const STATUS_VALUES = new Set(["pending", "ongoing", "complete"]);
const PRIORITY_VALUES = new Set(["low", "medium", "high"]);

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
  ["ongoing", "ongoing"],
  ["in progress", "ongoing"],
  ["inprogress", "ongoing"],
  ["active", "ongoing"],
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

    if (req.query.status) {
      normalizedStatus = normalizeStatusValue(req.query.status);
      if (!STATUS_VALUES.has(normalizedStatus)) {
        throw new BadRequestError("Invalid status filter");
      }
      query.status = normalizedStatus;
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
    } else if (normalizedStatus !== "complete") {
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

    const [tasks, total] = await Promise.all([
      Task.find(query).sort({ due_datetime: 1 }).skip(skip).limit(limit).lean(),
      Task.countDocuments(query),
    ]);

    res.json({
      status: "success",
      data: {
        tasks,
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
    }).lean();

    if (!task) {
      throw new NotFoundError("Task not found");
    }

    res.json({
      status: "success",
      data: { task },
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
        "status must be one of pending, ongoing, complete",
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
        await ActivityLog.create(
          buildCompletedLogPayload(task),
        );
      } catch (error) {
        console.warn(
          `[TasksController] Failed to insert task_completed log for task ${task._id}: ${error.message}`,
        );
      }
    }

    res.json({
      status: "success",
      message: "Task status updated",
      data: { task },
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

module.exports = {
  getTasks,
  getTaskById,
  updateTaskStatus,
  deleteTask,
};

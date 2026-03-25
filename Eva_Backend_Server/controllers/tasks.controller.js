/**
 * Tasks Controller
 * Phase 10 task page endpoints.
 */

const mongoose = require("mongoose");
const { Task } = require("../models");
const {
  BadRequestError,
  NotFoundError,
} = require("../middleware/errorHandler");

const STATUS_VALUES = new Set(["pending", "ongoing", "complete"]);
const PRIORITY_VALUES = new Set(["low", "medium", "high"]);

const parsePositiveInt = (value, fallback) => {
  const parsed = Number.parseInt(value, 10);
  if (Number.isNaN(parsed) || parsed <= 0) {
    return fallback;
  }
  return parsed;
};

const parseDateRange = (dateValue) => {
  if (!dateValue) {
    return null;
  }

  const base = new Date(dateValue);
  if (Number.isNaN(base.getTime())) {
    throw new BadRequestError("Invalid date query format");
  }

  const start = new Date(base);
  start.setUTCHours(0, 0, 0, 0);
  const end = new Date(base);
  end.setUTCHours(23, 59, 59, 999);

  return { start, end };
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

    const query = {
      owner_id: req.userId,
      is_deleted: false,
    };

    if (req.query.status) {
      const status = String(req.query.status).toLowerCase();
      if (!STATUS_VALUES.has(status)) {
        throw new BadRequestError("Invalid status filter");
      }
      query.status = status;
    }

    if (req.query.priority) {
      const priority = String(req.query.priority).toLowerCase();
      if (!PRIORITY_VALUES.has(priority)) {
        throw new BadRequestError("Invalid priority filter");
      }
      query.priority = priority;
    }

    if (req.query.date) {
      const range = parseDateRange(req.query.date);
      query.due_datetime = {
        $gte: range.start,
        $lte: range.end,
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

    const normalizedStatus = String(status || "").toLowerCase();
    if (!STATUS_VALUES.has(normalizedStatus)) {
      throw new BadRequestError(
        "status must be one of pending, ongoing, complete",
      );
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
      {
        _id: id,
        owner_id: req.userId,
        is_deleted: false,
      },
      { $set: update },
      { new: true },
    ).lean();

    if (!task) {
      throw new NotFoundError("Task not found");
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

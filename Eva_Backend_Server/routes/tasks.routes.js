/**
 * Task Routes
 * Phase 10 tasks page APIs.
 */

const express = require("express");
const router = express.Router();

const { protect } = require("../middleware/auth");
const {
  getTasks,
  getTaskById,
  updateTaskStatus,
  deleteTask,
} = require("../controllers/tasks.controller");

router.get("/", protect, getTasks);
router.get("/:id", protect, getTaskById);
router.patch("/:id/status", protect, updateTaskStatus);
router.delete("/:id", protect, deleteTask);

module.exports = router;

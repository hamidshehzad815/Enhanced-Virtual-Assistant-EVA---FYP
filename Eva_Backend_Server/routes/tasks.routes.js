/**
 * Task Routes
 * Phase 10 tasks page APIs.
 */

const express = require("express");
const router = express.Router();

const { protect } = require("../middleware/auth");
const {
  getTasks,
  getCalendarTasks,
  getTaskById,
  updateTask,
  updateTaskStatus,
  deleteTask,
  respondToCollaborationInvite,
  respondToCollaborationInviteViaLink,
} = require("../controllers/tasks.controller");

router.get("/collaboration/respond", respondToCollaborationInviteViaLink);
router.get("/calendar", protect, getCalendarTasks);
router.get("/", protect, getTasks);
router.post("/:id/collaborators/respond", protect, respondToCollaborationInvite);
router.get("/:id", protect, getTaskById);
router.patch("/:id", protect, updateTask);
router.patch("/:id/status", protect, updateTaskStatus);
router.delete("/:id", protect, deleteTask);

module.exports = router;

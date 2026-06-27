const { formatDateInTimezone, resolveTimezone } = require("./timezone");

const resolveDisplayName = (user) => {
  const name = String(user?.name || user || "").trim();
  if (name) {
    return name.split(/\s+/)[0];
  }

  const username = String(user?.username || "").trim();
  if (username) {
    return username;
  }

  return "there";
};

const buildTaskRescheduledNotification = ({
  userId,
  user,
  taskTitle,
  dueDatetime,
  timezone,
  referenceType = "task",
  referenceId,
  taskId = null,
}) => {
  const tz = resolveTimezone(timezone);
  const when = formatDateInTimezone(dueDatetime, tz);
  const who = resolveDisplayName(user);
  const title = String(taskTitle || "Your task").trim() || "Your task";

  return {
    user_id: String(userId),
    sender_id: null,
    type: "task_rescheduled",
    reference_type: referenceType,
    reference_id: referenceId || taskId,
    title: "Task rescheduled",
    message: `Hey ${who}, ${title} was rescheduled to ${when}.`,
    action_required: false,
    delivery_channel: ["push", "in_app", "email"],
    scheduled_at: new Date(),
  };
};

module.exports = {
  buildTaskRescheduledNotification,
  resolveDisplayName,
};

/**
 * Learning roadmap session lock state (mirrors Eva_AI_Server utils/learning_utils.py).
 * Computed at read time — not stored in MongoDB.
 */

const SESSION_UNLOCK_MS = 24 * 60 * 60 * 1000;
const DEFAULT_SESSION_DURATION_MINUTES = 90;

const TERMINAL_STATUSES = new Set(["completed", "skipped"]);

const coerceDate = (value) => {
  if (value == null) {
    return null;
  }
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value;
  }
  const text = String(value).trim();
  if (!text) {
    return null;
  }
  const parsed = new Date(text.replace("Z", "+00:00"));
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};

const normalizeStatus = (status) => String(status || "").trim().toLowerCase();

const sessionDurationMinutes = (session) => {
  for (const key of ["estimated_duration", "duration"]) {
    const parsed = Number(session?.[key]);
    if (Number.isFinite(parsed) && parsed > 0) {
      return parsed;
    }
  }
  return DEFAULT_SESSION_DURATION_MINUTES;
};

const sessionWindowEnd = (session) => {
  const scheduled = coerceDate(session?.scheduled_date);
  if (!scheduled) {
    return null;
  }
  return new Date(
    scheduled.getTime() + sessionDurationMinutes(session) * 60 * 1000,
  );
};

const previousResolvedAt = (topic) => {
  if (!topic) {
    return null;
  }
  return coerceDate(topic.completed_at) || coerceDate(topic.updated_at) || null;
};

/**
 * When a pending session becomes interactable (24h rule + short-gap rule).
 * @returns {Date|null}
 */
const computeUnlockTime = (
  session,
  { previousScheduledDate = null, previousResolvedAt = null } = {},
) => {
  const scheduled = coerceDate(session?.scheduled_date);
  if (!scheduled) {
    return null;
  }

  let unlockTime = new Date(scheduled.getTime() - SESSION_UNLOCK_MS);
  const prevScheduled = coerceDate(previousScheduledDate);
  const prevResolved = coerceDate(previousResolvedAt);

  if (prevScheduled) {
    const gap = scheduled.getTime() - prevScheduled.getTime();
    if (gap < SESSION_UNLOCK_MS) {
      unlockTime = prevResolved || scheduled;
    }
  }

  return unlockTime;
};

/**
 * @returns {"locked"|"unlocked_future"|"ongoing"|"overdue"|"completed"|"skipped"}
 */
const computeSessionState = (
  session,
  now = new Date(),
  { previousScheduledDate = null, previousResolvedAt = null } = {},
) => {
  const status = normalizeStatus(session?.status);
  if (TERMINAL_STATUSES.has(status)) {
    return status;
  }

  const scheduled = coerceDate(session?.scheduled_date);
  if (!scheduled) {
    return "locked";
  }

  const unlockTime = computeUnlockTime(session, {
    previousScheduledDate,
    previousResolvedAt,
  });
  if (!unlockTime) {
    return "locked";
  }

  const nowMs = now.getTime();
  if (nowMs < unlockTime.getTime()) {
    return "locked";
  }
  if (nowMs < scheduled.getTime()) {
    return "unlocked_future";
  }

  const windowEnd = sessionWindowEnd(session);
  if (windowEnd && nowMs < windowEnd.getTime()) {
    return "ongoing";
  }
  return "overdue";
};

const sortTopicsByOrder = (topics) =>
  [...topics].sort((a, b) => Number(a.order || 0) - Number(b.order || 0));

/**
 * Lowest-order pending topic (current interactable session in chat).
 */
const findCurrentPendingTopic = (topics) => {
  const sorted = sortTopicsByOrder(topics);
  return sorted.find((t) => normalizeStatus(t.status) === "pending") || null;
};

const contextForTopic = (sortedTopics, topic) => {
  const order = Number(topic?.order || 0);
  const prev = sortedTopics.find((t) => Number(t.order || 0) === order - 1);
  if (!prev) {
    return { previousScheduledDate: null, previousResolvedAt: null };
  }
  return {
    previousScheduledDate: prev.scheduled_date,
    previousResolvedAt: previousResolvedAt(prev),
  };
};

/**
 * Attach session_state, is_current, unlock_at to serialized sessions for API.
 */
const enrichSessionsForGoal = (topics, now = new Date()) => {
  const sorted = sortTopicsByOrder(topics);
  const current = findCurrentPendingTopic(sorted);
  const currentId = current ? String(current._id) : null;

  return sorted.map((topic) => {
    const id = String(topic._id);
    const status = normalizeStatus(topic.status);
    const isCurrent = currentId != null && id === currentId;

    if (!isCurrent) {
      if (TERMINAL_STATUSES.has(status)) {
        return {
          session_state: status,
          is_current: false,
          unlock_at: null,
        };
      }
      return {
        session_state: "upcoming",
        is_current: false,
        unlock_at: null,
      };
    }

    const ctx = contextForTopic(sorted, topic);
    const sessionState = computeSessionState(topic, now, ctx);
    const unlockTime = computeUnlockTime(topic, ctx);

    return {
      session_state: sessionState,
      is_current: true,
      unlock_at:
        sessionState === "locked" && unlockTime ? unlockTime.toISOString() : null,
    };
  });
};

const ACTION_MESSAGES = {
  skip_locked:
    "That session is still locked. It unlocks within 24 hours of its scheduled time.",
  skip_ongoing:
    "That session is in progress — mark it complete or reschedule it, but you cannot skip it.",
  skip_overdue:
    "That session is overdue — mark it complete or reschedule it, but you cannot skip it.",
  skip_not_current: "Only the current session can be skipped.",
  complete_not_started:
    "That session has not started yet. Reschedule or skip it instead of marking it complete.",
  complete_locked:
    "That session is still locked. It unlocks within 24 hours of its scheduled time.",
  complete_not_current: "Only the current session can be marked complete.",
};

/**
 * Validate skip/complete against session_state rules (chat-aligned).
 * @returns {{ message: string }|null}
 */
const validateTopicAction = ({
  topics,
  topicId,
  action,
  now = new Date(),
}) => {
  const sorted = sortTopicsByOrder(topics);
  const topic = sorted.find((t) => String(t._id) === String(topicId));
  if (!topic) {
    return { message: "Topic not found" };
  }

  const current = findCurrentPendingTopic(sorted);
  if (!current || String(current._id) !== String(topicId)) {
    return {
      message:
        action === "skip"
          ? ACTION_MESSAGES.skip_not_current
          : ACTION_MESSAGES.complete_not_current,
    };
  }

  const ctx = contextForTopic(sorted, topic);
  const sessionState = computeSessionState(topic, now, ctx);

  if (action === "skip") {
    if (sessionState === "locked") {
      return { message: ACTION_MESSAGES.skip_locked };
    }
    if (sessionState === "ongoing") {
      return { message: ACTION_MESSAGES.skip_ongoing };
    }
    if (sessionState === "overdue") {
      return { message: ACTION_MESSAGES.skip_overdue };
    }
    if (sessionState !== "unlocked_future") {
      return { message: "That session cannot be skipped right now." };
    }
    return null;
  }

  if (action === "complete") {
    if (sessionState === "locked") {
      return { message: ACTION_MESSAGES.complete_locked };
    }
    if (sessionState === "unlocked_future") {
      return { message: ACTION_MESSAGES.complete_not_started };
    }
    if (sessionState !== "ongoing" && sessionState !== "overdue") {
      return { message: "That session cannot be completed right now." };
    }
    return null;
  }

  return { message: "Unsupported action" };
};

module.exports = {
  SESSION_UNLOCK_MS,
  DEFAULT_SESSION_DURATION_MINUTES,
  coerceDate,
  sessionDurationMinutes,
  sessionWindowEnd,
  computeUnlockTime,
  computeSessionState,
  findCurrentPendingTopic,
  enrichSessionsForGoal,
  validateTopicAction,
  ACTION_MESSAGES,
};

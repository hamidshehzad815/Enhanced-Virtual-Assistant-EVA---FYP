/**
 * Google Calendar REST client for Eva -> Google one-way sync.
 */
const axios = require("axios");
const { resolveTimezone } = require("../utils/timezone");

const BASE_URL = "https://www.googleapis.com/calendar/v3";

const buildHeaders = (accessToken) => ({
  Authorization: `Bearer ${accessToken}`,
  "Content-Type": "application/json",
});

const buildEventPayload = (taskData = {}) => {
  const dueRaw = taskData.due_datetime;
  if (!dueRaw) {
    throw new Error("task_data.due_datetime is required");
  }

  const dueDate = dueRaw instanceof Date ? dueRaw : new Date(dueRaw);
  if (Number.isNaN(dueDate.getTime())) {
    throw new Error("task_data.due_datetime must be a valid date/time");
  }

  const durationMinutes = Number.parseInt(
    taskData.duration_minutes ?? taskData.duration ?? 120,
    10,
  );
  const timezoneName = resolveTimezone(taskData.timezone || "UTC");
  const endDate = new Date(dueDate.getTime() + durationMinutes * 60 * 1000);

  const payload = {
    summary: taskData.title || "EVA Task",
    start: {
      dateTime: dueDate.toISOString(),
      timeZone: timezoneName,
    },
    end: {
      dateTime: endDate.toISOString(),
      timeZone: timezoneName,
    },
  };

  if (taskData.description) {
    payload.description = taskData.description;
  }

  return payload;
};

const createEvent = async (token, calendarId, taskData) => {
  if (!token || !calendarId) {
    return null;
  }

  try {
    const payload = buildEventPayload(taskData);
    const response = await axios.post(
      `${BASE_URL}/calendars/${encodeURIComponent(calendarId)}/events`,
      payload,
      {
        headers: buildHeaders(token),
        timeout: 10000,
        validateStatus: () => true,
      },
    );

    if (response.status === 200 || response.status === 201) {
      return response.data?.id || null;
    }
    return null;
  } catch (_error) {
    return null;
  }
};

const updateEvent = async (token, calendarId, eventId, taskData) => {
  if (!token || !calendarId || !eventId) {
    return false;
  }

  try {
    const payload = buildEventPayload(taskData);
    const response = await axios.patch(
      `${BASE_URL}/calendars/${encodeURIComponent(calendarId)}/events/${encodeURIComponent(eventId)}`,
      payload,
      {
        headers: buildHeaders(token),
        timeout: 10000,
        validateStatus: () => true,
      },
    );
    return response.status === 200 || response.status === 204;
  } catch (_error) {
    return false;
  }
};

const deleteEvent = async (token, calendarId, eventId) => {
  if (!token || !calendarId || !eventId) {
    return false;
  }

  try {
    const response = await axios.delete(
      `${BASE_URL}/calendars/${encodeURIComponent(calendarId)}/events/${encodeURIComponent(eventId)}`,
      {
        headers: buildHeaders(token),
        timeout: 10000,
        validateStatus: () => true,
      },
    );
    return response.status === 200 || response.status === 204;
  } catch (_error) {
    return false;
  }
};

module.exports = {
  createEvent,
  updateEvent,
  deleteEvent,
};

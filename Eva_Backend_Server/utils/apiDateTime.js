/**
 * Serialize UTC-naive Mongo datetimes for API responses in the user's timezone.
 *
 * Storage convention: due_datetime / scheduled_date are UTC instants (naive in DB).
 * API convention: return ISO-8601 with offset in the user's IANA timezone.
 */

const { normalizeTimezone, toLocalDayRangeUtc } = require("./timezone");

const INSTANT_DATETIME_KEYS = new Set([
  "due_datetime",
  "scheduled_date",
  "scheduled_datetime",
  "unlock_at",
  "completed_at",
  "created_at",
  "updated_at",
  "deleted_at",
  "started_at",
  "paused_at",
  "last_login",
  "reminder_sent_at",
  "overdue_notified_at",
  "token_expires",
  "last_synced_at",
  "responded_at",
  "since",
  "blocked_at",
]);

const DATE_ONLY_KEYS = new Set(["start_date", "end_date"]);

/**
 * MongoDB ObjectId / Buffer must become strings before JSON — otherwise
 * recursive payload walking exposes internal { buffer: { 0: n, ... } }.
 */
const serializeMongoSpecial = (value) => {
  if (value == null) {
    return undefined;
  }
  if (Buffer.isBuffer(value)) {
    return value.toString("hex");
  }
  if (typeof value.toHexString === "function") {
    try {
      return value.toHexString();
    } catch {
      return String(value);
    }
  }
  if (value._bsontype === "ObjectId" || value._bsontype === "ObjectID") {
    return String(value);
  }
  return undefined;
};

const coerceDate = (value) => {
  if (!value) {
    return null;
  }
  const parsed = value instanceof Date ? value : new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};

const getTimeZoneOffsetMillis = (utcDate, timeZone) => {
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  });

  const parts = formatter.formatToParts(utcDate);
  const map = {};
  parts.forEach((part) => {
    if (part.type !== "literal") {
      map[part.type] = part.value;
    }
  });

  const asUtc = Date.UTC(
    Number.parseInt(map.year, 10),
    Number.parseInt(map.month, 10) - 1,
    Number.parseInt(map.day, 10),
    Number.parseInt(map.hour, 10),
    Number.parseInt(map.minute, 10),
    Number.parseInt(map.second, 10),
  );

  return asUtc - utcDate.getTime();
};

const formatOffset = (offsetMs) => {
  const sign = offsetMs >= 0 ? "+" : "-";
  const abs = Math.abs(offsetMs);
  const hours = String(Math.floor(abs / 3600000)).padStart(2, "0");
  const minutes = String(Math.floor((abs % 3600000) / 60000)).padStart(2, "0");
  return `${sign}${hours}:${minutes}`;
};

/**
 * UTC instant → local ISO with offset, e.g. 2026-06-05T09:40:00+05:00
 */
const serializeInstantForApi = (value, timezoneValue) => {
  const date = coerceDate(value);
  if (!date) {
    return value ?? null;
  }

  const timezone = normalizeTimezone(timezoneValue);
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  });

  const parts = formatter.formatToParts(date);
  const map = {};
  parts.forEach((part) => {
    if (part.type !== "literal") {
      map[part.type] = part.value;
    }
  });

  const localIso = `${map.year}-${map.month}-${map.day}T${map.hour}:${map.minute}:${map.second || "00"}`;
  const offset = formatOffset(getTimeZoneOffsetMillis(date, timezone));
  return `${localIso}${offset}`;
};

/**
 * Calendar date fields (goal start/end) → YYYY-MM-DD in user timezone.
 */
const serializeDateOnlyForApi = (value, timezoneValue) => {
  const date = coerceDate(value);
  if (!date) {
    return value ?? null;
  }

  const timezone = normalizeTimezone(timezoneValue);
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });

  const parts = formatter.formatToParts(date);
  const map = {};
  parts.forEach((part) => {
    if (part.type !== "literal") {
      map[part.type] = part.value;
    }
  });

  return `${map.year}-${map.month}-${map.day}`;
};

const localizeValueForApi = (key, value, timezoneValue) => {
  if (value == null) {
    return value;
  }
  if (DATE_ONLY_KEYS.has(key)) {
    return serializeDateOnlyForApi(value, timezoneValue);
  }
  if (INSTANT_DATETIME_KEYS.has(key)) {
    return serializeInstantForApi(value, timezoneValue);
  }
  return value;
};

/**
 * Recursively localize known datetime fields in API payloads (max depth guard).
 */
const localizeApiPayload = (value, timezoneValue, depth = 0) => {
  if (value == null || depth > 10) {
    return value;
  }

  const mongoSerialized = serializeMongoSpecial(value);
  if (mongoSerialized !== undefined) {
    return mongoSerialized;
  }

  if (value instanceof Date) {
    return serializeInstantForApi(value, timezoneValue);
  }

  if (Array.isArray(value)) {
    return value.map((item) => localizeApiPayload(item, timezoneValue, depth + 1));
  }

  if (typeof value !== "object") {
    return value;
  }

  const output = {};
  for (const [key, nested] of Object.entries(value)) {
    if (nested instanceof Date || INSTANT_DATETIME_KEYS.has(key) || DATE_ONLY_KEYS.has(key)) {
      output[key] = localizeValueForApi(key, nested, timezoneValue);
    } else if (typeof nested === "object") {
      const serialized = serializeMongoSpecial(nested);
      output[key] = serialized !== undefined
        ? serialized
        : localizeApiPayload(nested, timezoneValue, depth + 1);
    } else {
      output[key] = nested;
    }
  }
  return output;
};

const withApiTimezone = (data, timezoneValue) => ({
  ...data,
  timezone: normalizeTimezone(timezoneValue),
});

module.exports = {
  INSTANT_DATETIME_KEYS,
  DATE_ONLY_KEYS,
  serializeInstantForApi,
  serializeDateOnlyForApi,
  localizeApiPayload,
  withApiTimezone,
  toLocalDayRangeUtc,
};

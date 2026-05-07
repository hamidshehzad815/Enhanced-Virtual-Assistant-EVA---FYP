/**
 * Timezone helpers for backend date filtering and display formatting.
 */

const TIMEZONE_ALIASES = {
  UTC: "UTC",
  GMT: "UTC",
  PKT: "Asia/Karachi",
  IST: "Asia/Kolkata",
  PST: "America/Los_Angeles",
  PDT: "America/Los_Angeles",
  MST: "America/Denver",
  MDT: "America/Denver",
  CST: "America/Chicago",
  CDT: "America/Chicago",
  EST: "America/New_York",
  EDT: "America/New_York",
};

const resolveTimezone = (timezoneValue) => {
  const normalized = String(timezoneValue || "").trim();
  if (!normalized) {
    return "UTC";
  }

  const aliasKey = normalized.toUpperCase();
  return TIMEZONE_ALIASES[aliasKey] || normalized;
};

const isValidTimezone = (timezone) => {
  try {
    Intl.DateTimeFormat("en-US", { timeZone: timezone }).format(new Date());
    return true;
  } catch (_error) {
    return false;
  }
};

const normalizeTimezone = (timezoneValue) => {
  const resolved = resolveTimezone(timezoneValue);
  return isValidTimezone(resolved) ? resolved : "UTC";
};

const parseDateOnly = (dateValue) => {
  const match = String(dateValue || "")
    .trim()
    .match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) {
    return null;
  }

  const year = Number.parseInt(match[1], 10);
  const month = Number.parseInt(match[2], 10);
  const day = Number.parseInt(match[3], 10);

  if (
    !Number.isInteger(year) ||
    !Number.isInteger(month) ||
    !Number.isInteger(day)
  ) {
    return null;
  }
  if (month < 1 || month > 12 || day < 1 || day > 31) {
    return null;
  }

  return { year, month, day };
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

const toUtcFromLocalParts = (
  year,
  month,
  day,
  hour,
  minute,
  second,
  timeZone,
) => {
  const guessUtc = Date.UTC(year, month - 1, day, hour, minute, second, 0);
  let utcTs = guessUtc - getTimeZoneOffsetMillis(new Date(guessUtc), timeZone);

  // Stabilize around DST boundaries.
  const stableOffset = getTimeZoneOffsetMillis(new Date(utcTs), timeZone);
  utcTs = guessUtc - stableOffset;

  return new Date(utcTs);
};

const toLocalDayRangeUtc = (dateValue, timezoneValue) => {
  const parsed = parseDateOnly(dateValue);
  if (!parsed) {
    return null;
  }

  const timezone = normalizeTimezone(timezoneValue);
  const { year, month, day } = parsed;
  const start = toUtcFromLocalParts(year, month, day, 0, 0, 0, timezone);
  const nextDayStart = toUtcFromLocalParts(
    year,
    month,
    day + 1,
    0,
    0,
    0,
    timezone,
  );
  const end = new Date(nextDayStart.getTime() - 1);

  return {
    start,
    end,
    timezone,
  };
};

const formatDateInTimezone = (value, timezoneValue, options = {}) => {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "your scheduled time";
  }

  const timezone = normalizeTimezone(timezoneValue);
  const formatOptions = {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
    ...options,
  };

  try {
    return parsed.toLocaleString("en-US", formatOptions);
  } catch (_error) {
    return parsed.toLocaleString("en-US", {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  }
};

module.exports = {
  resolveTimezone,
  normalizeTimezone,
  toLocalDayRangeUtc,
  formatDateInTimezone,
};

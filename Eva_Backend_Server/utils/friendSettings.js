/** Privacy setting for who may send friend requests. */
const ALLOW_FRIEND_REQUESTS_EVERYONE = "everyone";
const ALLOW_FRIEND_REQUESTS_NOBODY = "nobody";
const ALLOW_FRIEND_REQUESTS_VALUES = new Set([
  ALLOW_FRIEND_REQUESTS_EVERYONE,
  ALLOW_FRIEND_REQUESTS_NOBODY,
]);

const normalizeAllowFriendRequests = (value) => {
  if (value === undefined) {
    return undefined;
  }
  const normalized = String(value || "").trim().toLowerCase();
  if (!ALLOW_FRIEND_REQUESTS_VALUES.has(normalized)) {
    throw new Error(
      `allow_friend_requests must be "${ALLOW_FRIEND_REQUESTS_EVERYONE}" or "${ALLOW_FRIEND_REQUESTS_NOBODY}"`,
    );
  }
  return normalized;
};

/** Missing or legacy settings default to accepting requests. */
const isAcceptingFriendRequests = (settings) => {
  if (!settings) {
    return true;
  }
  const raw = settings.allow_friend_requests;
  if (raw == null || raw === "") {
    return true;
  }
  return String(raw).trim().toLowerCase() !== ALLOW_FRIEND_REQUESTS_NOBODY;
};

module.exports = {
  ALLOW_FRIEND_REQUESTS_EVERYONE,
  ALLOW_FRIEND_REQUESTS_NOBODY,
  ALLOW_FRIEND_REQUESTS_VALUES,
  normalizeAllowFriendRequests,
  isAcceptingFriendRequests,
};

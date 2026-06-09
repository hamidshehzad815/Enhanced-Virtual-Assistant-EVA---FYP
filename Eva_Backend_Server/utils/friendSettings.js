/**
 * Privacy setting for who may send friend requests.
 * Stored as boolean; legacy "everyone"/"nobody" strings are still read safely.
 */

const LEGACY_CLOSED_VALUES = new Set(["nobody", "false"]);
const LEGACY_OPEN_VALUES = new Set(["everyone", "true"]);

/** Missing or legacy settings default to accepting requests. */
const isAcceptingFriendRequests = (settings) => {
  if (!settings) {
    return true;
  }

  const raw = settings.allow_friend_requests;
  if (raw == null || raw === "") {
    return true;
  }

  if (typeof raw === "boolean") {
    return raw;
  }

  const normalized = String(raw).trim().toLowerCase();
  if (LEGACY_CLOSED_VALUES.has(normalized)) {
    return false;
  }
  if (LEGACY_OPEN_VALUES.has(normalized)) {
    return true;
  }

  return true;
};

/** Normalize stored value to boolean for API responses. */
const allowFriendRequestsToBoolean = (value) =>
  isAcceptingFriendRequests({ allow_friend_requests: value });

/** Mongo filter for users who are not accepting new friend requests. */
const closedToFriendRequestsFilter = () => ({
  allow_friend_requests: { $in: [false, "nobody"] },
});

module.exports = {
  isAcceptingFriendRequests,
  allowFriendRequestsToBoolean,
  closedToFriendRequestsFilter,
};

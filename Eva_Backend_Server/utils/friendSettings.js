/**
 * Privacy setting for who may send friend requests.
 * Stored and exposed as boolean only (true = accept, false = reject).
 */

/** Missing or non-boolean values default to accepting requests. */
const isAcceptingFriendRequests = (settings) => {
  if (!settings || typeof settings.allow_friend_requests !== "boolean") {
    return true;
  }

  return settings.allow_friend_requests;
};

/** Normalize stored value to boolean for API responses. */
const allowFriendRequestsToBoolean = (value) =>
  typeof value === "boolean" ? value : true;

/** Mongo filter for users who are not accepting new friend requests. */
const closedToFriendRequestsFilter = () => ({
  allow_friend_requests: false,
});

module.exports = {
  isAcceptingFriendRequests,
  allowFriendRequestsToBoolean,
  closedToFriendRequestsFilter,
};

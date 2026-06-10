const {
  isAcceptingFriendRequests,
  allowFriendRequestsToBoolean,
  closedToFriendRequestsFilter,
} = require("../utils/friendSettings");

describe("friendSettings utils", () => {
  test("isAcceptingFriendRequests accepts true and rejects false", () => {
    expect(isAcceptingFriendRequests({ allow_friend_requests: true })).toBe(true);
    expect(isAcceptingFriendRequests({ allow_friend_requests: false })).toBe(false);
  });

  test("isAcceptingFriendRequests defaults to true when missing or non-boolean", () => {
    expect(isAcceptingFriendRequests(null)).toBe(true);
    expect(isAcceptingFriendRequests({})).toBe(true);
    expect(isAcceptingFriendRequests({ allow_friend_requests: "nobody" })).toBe(
      true,
    );
    expect(isAcceptingFriendRequests({ allow_friend_requests: "everyone" })).toBe(
      true,
    );
  });

  test("allowFriendRequestsToBoolean returns boolean only", () => {
    expect(allowFriendRequestsToBoolean(true)).toBe(true);
    expect(allowFriendRequestsToBoolean(false)).toBe(false);
    expect(allowFriendRequestsToBoolean(undefined)).toBe(true);
    expect(allowFriendRequestsToBoolean("nobody")).toBe(true);
  });

  test("closedToFriendRequestsFilter matches boolean false only", () => {
    expect(closedToFriendRequestsFilter()).toEqual({
      allow_friend_requests: false,
    });
  });
});

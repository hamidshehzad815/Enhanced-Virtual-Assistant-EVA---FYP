const {
  isAcceptingFriendRequests,
  allowFriendRequestsToBoolean,
  closedToFriendRequestsFilter,
} = require("../utils/friendSettings");

describe("friendSettings utils", () => {
  test("isAcceptingFriendRequests defaults to true when settings missing", () => {
    expect(isAcceptingFriendRequests(null)).toBe(true);
    expect(isAcceptingFriendRequests(undefined)).toBe(true);
    expect(isAcceptingFriendRequests({})).toBe(true);
  });

  test("isAcceptingFriendRequests respects boolean values", () => {
    expect(isAcceptingFriendRequests({ allow_friend_requests: true })).toBe(true);
    expect(isAcceptingFriendRequests({ allow_friend_requests: false })).toBe(false);
  });

  test("isAcceptingFriendRequests maps legacy everyone/nobody strings", () => {
    expect(isAcceptingFriendRequests({ allow_friend_requests: "nobody" })).toBe(
      false,
    );
    expect(isAcceptingFriendRequests({ allow_friend_requests: "NOBODY" })).toBe(
      false,
    );
    expect(
      isAcceptingFriendRequests({ allow_friend_requests: "everyone" }),
    ).toBe(true);
  });

  test("allowFriendRequestsToBoolean normalizes stored values", () => {
    expect(allowFriendRequestsToBoolean("nobody")).toBe(false);
    expect(allowFriendRequestsToBoolean("everyone")).toBe(true);
    expect(allowFriendRequestsToBoolean(false)).toBe(false);
    expect(allowFriendRequestsToBoolean(true)).toBe(true);
  });

  test("closedToFriendRequestsFilter includes legacy nobody", () => {
    expect(closedToFriendRequestsFilter()).toEqual({
      allow_friend_requests: { $in: [false, "nobody"] },
    });
  });
});

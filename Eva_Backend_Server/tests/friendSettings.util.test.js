const {
  normalizeAllowFriendRequests,
  isAcceptingFriendRequests,
} = require("../utils/friendSettings");

describe("friendSettings utils", () => {
  test("normalizeAllowFriendRequests accepts everyone and nobody", () => {
    expect(normalizeAllowFriendRequests("everyone")).toBe("everyone");
    expect(normalizeAllowFriendRequests("NOBODY")).toBe("nobody");
  });

  test("normalizeAllowFriendRequests rejects invalid values", () => {
    expect(() => normalizeAllowFriendRequests("friends_only")).toThrow(
      /allow_friend_requests must be/i,
    );
  });

  test("isAcceptingFriendRequests defaults to true when settings missing", () => {
    expect(isAcceptingFriendRequests(null)).toBe(true);
    expect(isAcceptingFriendRequests(undefined)).toBe(true);
    expect(isAcceptingFriendRequests({})).toBe(true);
  });

  test("isAcceptingFriendRequests respects nobody", () => {
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
});

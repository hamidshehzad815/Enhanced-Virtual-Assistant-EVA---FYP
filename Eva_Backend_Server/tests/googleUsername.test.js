jest.mock("../models", () => ({
  User: { findOne: jest.fn() },
}));

const { User } = require("../models");
const { generateUniqueUsername } = require("../utils/googleUsername");

const USERNAME_RE = /^[a-z]{3,30}$/;

describe("generateUniqueUsername (name-based, letters-only)", () => {
  beforeEach(() => jest.clearAllMocks());

  it("uses the first name word when it is long enough (ignores the email)", async () => {
    User.findOne.mockResolvedValue(null); // no collision
    // Roll-number email has no useful letters, so the name must drive it.
    const username = await generateUniqueUsername(
      "f2022266297@umt.edu.pk",
      "Hamid Shehzad",
    );
    expect(username).toMatch(USERNAME_RE);
    expect(username).toBe("hamid");
  });

  it("appends the second word when the first is too short", async () => {
    User.findOne.mockResolvedValue(null);
    const username = await generateUniqueUsername("x@y.com", "Al Rehman");
    expect(username).toMatch(USERNAME_RE);
    expect(username).toBe("alrehman");
  });

  it("falls back to evauser when the name has no usable letters", async () => {
    User.findOne.mockResolvedValue(null);
    const username = await generateUniqueUsername("f2022266297@umt.edu.pk", "");
    expect(username).toMatch(USERNAME_RE);
    expect(username).toBe("evauser");
  });

  it("appends an alphabetic suffix on collision (still letters-only)", async () => {
    User.findOne
      .mockResolvedValueOnce({ _id: "taken" }) // "hamid" is taken
      .mockResolvedValueOnce(null); // "hamida" is free
    const username = await generateUniqueUsername("x@y.com", "Hamid");
    expect(username).toMatch(USERNAME_RE);
    expect(username).toBe("hamida");
  });
});

jest.mock("../models", () => ({
  User: { findOne: jest.fn() },
}));

const { User } = require("../models");
const { generateUniqueUsername } = require("../utils/googleUsername");

const USERNAME_RE = /^[a-z]{3,30}$/;

describe("generateUniqueUsername (letters-only)", () => {
  beforeEach(() => jest.clearAllMocks());

  it("strips digits/symbols to produce a letters-only username", async () => {
    User.findOne.mockResolvedValue(null); // no collision
    const username = await generateUniqueUsername("Hamid.815@gmail.com", "Hamid Shehzad");
    expect(username).toMatch(USERNAME_RE);
    expect(username).toBe("hamid");
  });

  it("falls back to a valid default when the source has no letters", async () => {
    User.findOne.mockResolvedValue(null);
    const username = await generateUniqueUsername("12345@x.com", "");
    expect(username).toMatch(USERNAME_RE);
  });

  it("appends an alphabetic suffix on collision (still letters-only)", async () => {
    User.findOne
      .mockResolvedValueOnce({ _id: "taken" }) // "hamid" is taken
      .mockResolvedValueOnce(null); // "hamida" is free
    const username = await generateUniqueUsername("hamid@x.com", "Hamid");
    expect(username).toMatch(USERNAME_RE);
    expect(username).toBe("hamida");
  });
});

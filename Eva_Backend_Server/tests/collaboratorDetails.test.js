jest.mock("../models", () => ({
  User: { find: jest.fn() },
}));

const mongoose = require("mongoose");
const { User } = require("../models");
const {
  collectCollaboratorUserIds,
  loadCollaboratorProfiles,
  serializeCollaborators,
  buildCollaboratorsForDoc,
} = require("../utils/collaboratorDetails");

const mockUserFind = (users) => {
  User.find.mockReturnValue({
    select: jest.fn().mockReturnValue({
      lean: jest.fn().mockResolvedValue(users),
    }),
  });
};

describe("collaboratorDetails util", () => {
  beforeEach(() => jest.clearAllMocks());

  test("collectCollaboratorUserIds dedupes ids across docs", () => {
    const a = new mongoose.Types.ObjectId();
    const b = new mongoose.Types.ObjectId();
    const ids = collectCollaboratorUserIds([
      { collaborators: [{ user_id: a }, { user_id: b }] },
      { collaborators: [{ user_id: a }] },
      { collaborators: [] },
      {},
    ]);
    expect(ids.sort()).toEqual([String(a), String(b)].sort());
  });

  test("serializeCollaborators maps public profile + normalizes status", () => {
    const a = new mongoose.Types.ObjectId();
    const profileMap = new Map([
      [String(a), { _id: String(a), name: "Aisha", username: "aisha", profile_picture: null }],
    ]);
    const out = serializeCollaborators(
      [{ user_id: a, status: "ACCEPTED" }],
      profileMap,
    );
    expect(out).toEqual([
      {
        user: { _id: String(a), name: "Aisha", username: "aisha", profile_picture: null },
        status: "accepted",
      },
    ]);
  });

  test("serializeCollaborators skips collaborators whose user is missing", () => {
    const a = new mongoose.Types.ObjectId();
    const out = serializeCollaborators([{ user_id: a, status: "pending" }], new Map());
    expect(out).toEqual([]);
  });

  test("serializeCollaborators defaults unknown status to pending and merges extra fields", () => {
    const a = new mongoose.Types.ObjectId();
    const profileMap = new Map([
      [String(a), { _id: String(a), name: "X", username: "x", profile_picture: null }],
    ]);
    const out = serializeCollaborators(
      [{ user_id: a, status: "weird" }],
      profileMap,
      () => ({ progress: null }),
    );
    expect(out[0].status).toBe("pending");
    expect(out[0].progress).toBeNull();
  });

  test("loadCollaboratorProfiles never selects private fields", async () => {
    const a = new mongoose.Types.ObjectId();
    const selectSpy = jest.fn().mockReturnValue({
      lean: jest.fn().mockResolvedValue([
        { _id: a, name: "Aisha", username: "aisha", profile_picture: "pic.png" },
      ]),
    });
    User.find.mockReturnValue({ select: selectSpy });

    const map = await loadCollaboratorProfiles([a]);
    expect(selectSpy).toHaveBeenCalledWith("name username profile_picture");
    expect(map.get(String(a))).toEqual({
      _id: String(a),
      name: "Aisha",
      username: "aisha",
      profile_picture: "pic.png",
    });
  });

  test("buildCollaboratorsForDoc loads + serializes in one call", async () => {
    const a = new mongoose.Types.ObjectId();
    mockUserFind([{ _id: a, name: "Aisha", username: "aisha", profile_picture: null }]);

    const out = await buildCollaboratorsForDoc([{ user_id: a, status: "pending" }]);
    expect(out).toHaveLength(1);
    expect(out[0].user.username).toBe("aisha");
    expect(out[0].status).toBe("pending");
  });

  test("empty / missing collaborators return an empty list", async () => {
    expect(await buildCollaboratorsForDoc([])).toEqual([]);
    expect(await buildCollaboratorsForDoc(undefined)).toEqual([]);
    expect(User.find).not.toHaveBeenCalled();
  });
});

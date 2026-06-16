process.env.NODE_ENV = "test";
process.env.JWT_ACCESS_SECRET = process.env.JWT_ACCESS_SECRET || "test-access-secret";

const jwt = require("jsonwebtoken");
const request = require("supertest");

jest.mock("../config/db", () => ({
  connectDB: jest.fn().mockResolvedValue(true),
}));

jest.mock("../jobs/reminder.job", () => ({
  startReminderJob: jest.fn(),
  stopReminderJob: jest.fn(),
}));

jest.mock("../services/ai.service", () => ({
  callAIServer: jest.fn(),
  callAIAnalytics: jest.fn(),
  callAIInternal: jest.fn(),
}));

jest.mock("../config/logger", () => ({
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
  debug: jest.fn(),
  http: jest.fn(),
  add: jest.fn(),
  stream: { write: jest.fn() },
}));

const mockFindById = jest.fn();
const mockFindByIdAndUpdate = jest.fn();
const mockReplaceProfilePicture = jest.fn();
const mockDeleteProfilePicture = jest.fn();

jest.mock("../models", () => ({
  User: {
    findById: (...args) => mockFindById(...args),
    findByIdAndUpdate: (...args) => mockFindByIdAndUpdate(...args),
  },
}));

jest.mock("../services/cloudinary.service", () => ({
  replaceProfilePicture: (...args) => mockReplaceProfilePicture(...args),
  deleteProfilePicture: (...args) => mockDeleteProfilePicture(...args),
}));

const app = require("../app");

const USER_ID = "507f1f77bcf86cd799439011";

const makeToken = () =>
  jwt.sign({ userId: USER_ID }, process.env.JWT_ACCESS_SECRET, {
    expiresIn: "15m",
  });

const authHeaders = () => ({
  Authorization: `Bearer ${makeToken()}`,
});

const mockUserDoc = (overrides = {}) => ({
  _id: USER_ID,
  name: "Hamid",
  username: "hamid",
  email: "hamid@example.com",
  profile_picture: null,
  profile_picture_public_id: null,
  timezone: "UTC",
  is_verified: true,
  is_active: true,
  toPublicProfile() {
    return {
      _id: this._id,
      name: this.name,
      username: this.username,
      email: this.email,
      profile_picture: this.profile_picture,
      timezone: this.timezone,
      is_verified: this.is_verified,
    };
  },
  ...overrides,
});

describe("POST /api/profile/avatar", () => {
  const setupAuthUser = (userOverrides = {}) => {
    const user = mockUserDoc({ is_active: true, ...userOverrides });
    mockFindById
      .mockResolvedValueOnce(user)
      .mockImplementationOnce(() => ({
        select: jest.fn().mockResolvedValue(user),
      }));
    return user;
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("uploads avatar and returns updated profile", async () => {
    setupAuthUser();
    mockReplaceProfilePicture.mockResolvedValue({
      secure_url: "https://res.cloudinary.com/demo/image/upload/v1/avatar.jpg",
      public_id: "eva/profile-pictures/user_1",
    });

    const updatedUser = mockUserDoc({
      profile_picture: "https://res.cloudinary.com/demo/image/upload/v1/avatar.jpg",
      profile_picture_public_id: "eva/profile-pictures/user_1",
    });
    mockFindByIdAndUpdate.mockResolvedValue(updatedUser);

    const response = await request(app)
      .post("/api/profile/avatar")
      .set(authHeaders())
      .attach("avatar", Buffer.from("fake-image"), {
        filename: "avatar.png",
        contentType: "image/png",
      });

    expect(response.status).toBe(200);
    expect(response.body.message).toBe("Profile picture updated");
    expect(response.body.data.user.profile_picture).toContain("cloudinary.com");
    expect(mockReplaceProfilePicture).toHaveBeenCalled();
    expect(mockFindByIdAndUpdate).toHaveBeenCalledWith(
      USER_ID,
      {
        $set: {
          profile_picture: "https://res.cloudinary.com/demo/image/upload/v1/avatar.jpg",
          profile_picture_public_id: "eva/profile-pictures/user_1",
        },
      },
      expect.objectContaining({ new: true }),
    );
  });

  test("replaces avatar and passes previous public_id to Cloudinary service", async () => {
    setupAuthUser({
      profile_picture: "https://res.cloudinary.com/demo/old.jpg",
      profile_picture_public_id: "eva/profile-pictures/old",
    });
    mockReplaceProfilePicture.mockResolvedValue({
      secure_url: "https://res.cloudinary.com/demo/new.jpg",
      public_id: "eva/profile-pictures/new",
    });
    mockFindByIdAndUpdate.mockResolvedValue(
      mockUserDoc({
        profile_picture: "https://res.cloudinary.com/demo/new.jpg",
      }),
    );

    const response = await request(app)
      .post("/api/profile/avatar")
      .set(authHeaders())
      .attach("avatar", Buffer.from("fake-image"), {
        filename: "avatar.webp",
        contentType: "image/webp",
      });

    expect(response.status).toBe(200);
    expect(mockReplaceProfilePicture).toHaveBeenCalledWith(
      USER_ID,
      expect.objectContaining({ mimetype: "image/webp" }),
      "eva/profile-pictures/old",
    );
  });

  test("returns 400 when avatar file is missing", async () => {
    setupAuthUser();
    const response = await request(app)
      .post("/api/profile/avatar")
      .set(authHeaders())
      .send({});

    expect(response.status).toBe(400);
    expect(response.body.message).toMatch(/avatar file is required/i);
    expect(mockReplaceProfilePicture).not.toHaveBeenCalled();
  });

  test("returns 401 without auth token", async () => {
    const response = await request(app)
      .post("/api/profile/avatar")
      .attach("avatar", Buffer.from("fake-image"), {
        filename: "avatar.png",
        contentType: "image/png",
      });

    expect(response.status).toBe(401);
  });
});

describe("DELETE /api/profile/avatar", () => {
  const setupAuthUser = (userOverrides = {}) => {
    const user = mockUserDoc({ is_active: true, ...userOverrides });
    // findById is used in two different ways in the code:
    // - protect: `await User.findById(...)`
    // - controller: `await User.findById(...).select(...)` (note: `.select` is
    //   called on the return value of findById, before `await`)
    //
    // So we must return an object that both:
    // - is awaitable (plain object is fine), and
    // - has a `.select()` function.
    mockFindById.mockImplementation(() => ({
      ...user,
      select: jest.fn().mockResolvedValue(user),
    }));
    return user;
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockFindById.mockReset();
    mockFindByIdAndUpdate.mockReset();
    mockDeleteProfilePicture.mockResolvedValue(undefined);
  });

  test("removes avatar from Cloudinary and clears user fields", async () => {
    setupAuthUser({
      profile_picture: "https://res.cloudinary.com/demo/old.jpg",
      profile_picture_public_id: "eva/profile-pictures/old",
    });
    const updatedUser = mockUserDoc({
      profile_picture: null,
      profile_picture_public_id: null,
    });
    mockFindByIdAndUpdate.mockResolvedValue(updatedUser);

    const response = await request(app)
      .delete("/api/profile/avatar")
      .set(authHeaders());

    expect(response.status).toBe(200);
    expect(response.body.message).toBe("Profile picture removed");
    expect(response.body.data.user.profile_picture).toBeNull();
    expect(mockDeleteProfilePicture).toHaveBeenCalledWith("eva/profile-pictures/old");
    expect(mockFindByIdAndUpdate).toHaveBeenCalledWith(
      USER_ID,
      {
        $set: {
          profile_picture: null,
          profile_picture_public_id: null,
        },
      },
      expect.objectContaining({ new: true }),
    );
  });

  test("returns success when user has no profile picture", async () => {
    setupAuthUser({
      profile_picture: null,
      profile_picture_public_id: null,
    });

    const response = await request(app)
      .delete("/api/profile/avatar")
      .set(authHeaders());

    expect(response.status).toBe(200);
    expect(response.body.message).toBe("No profile picture to remove");
    expect(response.body.data.user.profile_picture).toBeNull();
    expect(mockDeleteProfilePicture).not.toHaveBeenCalled();
    expect(mockFindByIdAndUpdate).not.toHaveBeenCalled();
  });

  test("clears DB when only profile_picture URL exists without public_id", async () => {
    setupAuthUser({
      profile_picture: "https://res.cloudinary.com/demo/legacy.jpg",
      profile_picture_public_id: null,
    });
    mockFindByIdAndUpdate.mockResolvedValue(
      mockUserDoc({ profile_picture: null, profile_picture_public_id: null }),
    );

    const response = await request(app)
      .delete("/api/profile/avatar")
      .set(authHeaders());

    expect(response.status).toBe(200);
    expect(response.body.message).toBe("Profile picture removed");
    expect(mockDeleteProfilePicture).not.toHaveBeenCalled();
    expect(mockFindByIdAndUpdate).toHaveBeenCalled();
  });

  test("returns 401 without auth token", async () => {
    const response = await request(app).delete("/api/profile/avatar");

    expect(response.status).toBe(401);
  });
});

process.env.NODE_ENV = "test";

jest.mock("../config/logger", () => ({
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
  debug: jest.fn(),
}));

jest.mock("../models", () => ({
  Notification: {
    create: jest.fn(),
  },
  User: {
    findById: jest.fn(),
    updateOne: jest.fn(),
  },
  UserSetting: {
    findOne: jest.fn(),
  },
}));

const { Notification } = require("../models");
const { insert_and_dispatch } = require("../services/notification.service");

describe("Notification Service", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("insert_and_dispatch returns zero-summary for empty array", async () => {
    const result = await insert_and_dispatch([]);

    expect(result).toEqual({
      requested: 0,
      inserted: 0,
      dispatched_push: 0,
      dispatched_email: 0,
      failed: 0,
      results: [],
    });
    expect(Notification.create).not.toHaveBeenCalled();
  });

  test("insert_and_dispatch returns zero-summary for non-array input", async () => {
    const result = await insert_and_dispatch(null);

    expect(result).toEqual({
      requested: 0,
      inserted: 0,
      dispatched_push: 0,
      dispatched_email: 0,
      failed: 0,
      results: [],
    });
    expect(Notification.create).not.toHaveBeenCalled();
  });
});

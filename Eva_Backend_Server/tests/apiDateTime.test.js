const mongoose = require("mongoose");
const {
  localizeApiPayload,
  serializeInstantForApi,
} = require("../utils/apiDateTime");

describe("apiDateTime", () => {
  test("serializeInstantForApi uses user timezone offset", () => {
    const utc = new Date("2026-06-05T04:40:00.000Z");
    expect(serializeInstantForApi(utc, "Asia/Karachi")).toBe(
      "2026-06-05T09:40:00+05:00",
    );
  });

  test("localizeApiPayload stringifies Mongo ObjectIds", () => {
    const id = new mongoose.Types.ObjectId();
    const ownerId = new mongoose.Types.ObjectId();

    const localized = localizeApiPayload(
      {
        _id: id,
        owner_id: ownerId,
        learning_topic_id: new mongoose.Types.ObjectId(),
        due_datetime: new Date("2026-06-05T04:40:00.000Z"),
        created_at: new Date("2026-06-05T04:06:34.000Z"),
      },
      "Asia/Karachi",
    );

    expect(localized._id).toBe(String(id));
    expect(localized.owner_id).toBe(String(ownerId));
    expect(localized.learning_topic_id).toMatch(/^[a-f0-9]{24}$/);
    expect(localized._id).not.toHaveProperty("buffer");
    expect(localized.due_datetime).toBe("2026-06-05T09:40:00+05:00");
  });
});

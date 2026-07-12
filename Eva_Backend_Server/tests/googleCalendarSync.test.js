const {
  isGoogleCalendarSyncEnabled,
} = require("../utils/googleCalendarSyncSettings");
const {
  pickActiveGoogleIntegration,
  tokenNeedsRefresh,
  refreshGoogleAccessToken,
} = require("../utils/googleCalendarSync");

describe("googleCalendarSync utils", () => {
  test("isGoogleCalendarSyncEnabled requires explicit true", () => {
    expect(isGoogleCalendarSyncEnabled({})).toBe(false);
    expect(isGoogleCalendarSyncEnabled({ google_calendar_sync_enabled: false })).toBe(
      false,
    );
    expect(isGoogleCalendarSyncEnabled({ google_calendar_sync_enabled: true })).toBe(
      true,
    );
  });

  test("pickActiveGoogleIntegration selects active google row", () => {
    const picked = pickActiveGoogleIntegration([
      { provider: "google_calendar", is_active: false },
      { provider: "google_calendar", is_active: true, access_token: "tok" },
    ]);
    expect(picked.access_token).toBe("tok");
  });

  test("tokenNeedsRefresh when expiry is near", () => {
    const soon = new Date(Date.now() + 60 * 1000);
    expect(
      tokenNeedsRefresh({
        access_token: "token",
        token_expires: soon,
        refresh_token: "refresh",
      }),
    ).toBe(true);
    expect(
      tokenNeedsRefresh({
        access_token: "token",
        token_expires: new Date(Date.now() + 60 * 60 * 1000),
        refresh_token: "refresh",
      }),
    ).toBe(false);
  });

  test("refreshGoogleAccessToken returns null without env credentials", async () => {
    const originalId = process.env.GOOGLE_CLIENT_ID;
    const originalSecret = process.env.GOOGLE_CLIENT_SECRET;
    delete process.env.GOOGLE_CLIENT_ID;
    delete process.env.GOOGLE_CLIENT_SECRET;

    await expect(refreshGoogleAccessToken("refresh-token")).resolves.toBeNull();

    process.env.GOOGLE_CLIENT_ID = originalId;
    process.env.GOOGLE_CLIENT_SECRET = originalSecret;
  });
});

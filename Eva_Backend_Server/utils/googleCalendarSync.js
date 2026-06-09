/**
 * Google Calendar sync gating, integration lookup, and token refresh.
 */
const axios = require("axios");
const { Integration } = require("../models");
const { isGoogleCalendarSyncEnabled } = require("./googleCalendarSyncSettings");

const REFRESH_BUFFER_MS = 5 * 60 * 1000;

const pickActiveGoogleIntegration = (integrations = []) => {
  if (integrations.length > 0) {
    return (
      integrations.find(
        (row) =>
          String(row?.provider || "").toLowerCase() === "google_calendar"
          && row?.is_active === true,
      ) || null
    );
  }
  return null;
};

const parseTokenExpires = (value) => {
  if (!value) {
    return null;
  }
  const parsed = value instanceof Date ? value : new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};

const tokenNeedsRefresh = (integration) => {
  const accessToken = String(integration?.access_token || "").trim();
  if (!accessToken) {
    return Boolean(String(integration?.refresh_token || "").trim());
  }

  const expires = parseTokenExpires(integration?.token_expires);
  if (!expires) {
    return false;
  }
  return expires.getTime() <= Date.now() + REFRESH_BUFFER_MS;
};

const refreshGoogleAccessToken = async (refreshToken) => {
  const clientId = process.env.GOOGLE_CLIENT_ID || "";
  const clientSecret = process.env.GOOGLE_CLIENT_SECRET || "";
  if (!clientId || !clientSecret || !refreshToken) {
    return null;
  }

  try {
    const response = await axios.post(
      "https://oauth2.googleapis.com/token",
      new URLSearchParams({
        client_id: clientId,
        client_secret: clientSecret,
        refresh_token: refreshToken,
        grant_type: "refresh_token",
      }).toString(),
      {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        timeout: 10000,
        validateStatus: () => true,
      },
    );

    if (response.status !== 200 || !response.data?.access_token) {
      return null;
    }

    let tokenExpires = null;
    if (response.data.expires_in != null) {
      tokenExpires = new Date(Date.now() + Number(response.data.expires_in) * 1000);
    }

    return {
      access_token: String(response.data.access_token).trim(),
      token_expires: tokenExpires,
    };
  } catch (_error) {
    return null;
  }
};

const persistRefreshedTokens = async (integrationId, accessToken, tokenExpires) => {
  await Integration.updateOne(
    { _id: integrationId },
    {
      $set: {
        access_token: accessToken,
        token_expires: tokenExpires,
        updated_at: new Date(),
      },
    },
  );
};

const ensureFreshAccessToken = async (userId, integration) => {
  const row = { ...(integration || {}) };
  if (!tokenNeedsRefresh(row)) {
    return row;
  }

  const refreshToken = String(row.refresh_token || "").trim();
  const refreshed = await refreshGoogleAccessToken(refreshToken);
  if (!refreshed?.access_token) {
    return row;
  }

  await persistRefreshedTokens(row._id, refreshed.access_token, refreshed.token_expires);
  row.access_token = refreshed.access_token;
  row.token_expires = refreshed.token_expires;
  return row;
};

const loadActiveGoogleIntegration = async (userId) => {
  return Integration.findOne({
    user_id: userId,
    provider: "google_calendar",
    is_active: true,
  })
    .select("+access_token +refresh_token")
    .lean();
};

const resolveGoogleCalendarSync = async (userId, userSettings, integrations = null) => {
  if (!isGoogleCalendarSyncEnabled(userSettings)) {
    return null;
  }

  let integration = pickActiveGoogleIntegration(integrations || []);
  if (!integration) {
    integration = await loadActiveGoogleIntegration(userId);
  }
  if (!integration) {
    return null;
  }

  integration = await ensureFreshAccessToken(userId, integration);
  if (!String(integration.access_token || "").trim()) {
    return null;
  }

  return integration;
};

module.exports = {
  pickActiveGoogleIntegration,
  tokenNeedsRefresh,
  refreshGoogleAccessToken,
  ensureFreshAccessToken,
  loadActiveGoogleIntegration,
  resolveGoogleCalendarSync,
};

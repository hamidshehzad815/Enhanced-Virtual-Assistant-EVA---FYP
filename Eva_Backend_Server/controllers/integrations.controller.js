/**
 * Integrations Controller
 * Phase 11 Google Calendar connect/list/disconnect endpoints.
 */

const { Integration, UserSetting } = require("../models");
const { BadRequestError, NotFoundError } = require("../middleware/errorHandler");
const { localizeApiPayload, withApiTimezone } = require("../utils/apiDateTime");
const {
  scheduleGoogleCalendarBackfill,
} = require("../services/googleCalendarBackfill.service");
const { exchangeServerAuthCode } = require("../utils/googleCalendarSync");

const buildApiData = (req, payload) => {
  const timezone = (req.user && req.user.timezone) || "UTC";
  return withApiTimezone(localizeApiPayload(payload, timezone), timezone);
};

const sanitizeIntegration = (integration, timezone) =>
  localizeApiPayload(
    {
      _id: integration._id,
      user_id: integration.user_id,
      provider: integration.provider,
      calendar_id: integration.calendar_id,
      token_expires: integration.token_expires,
      scope: integration.scope,
      is_active: integration.is_active,
      last_synced_at: integration.last_synced_at,
      created_at: integration.created_at,
      updated_at: integration.updated_at,
    },
    timezone,
  );

const enableGoogleCalendarSyncSetting = async (userId) => {
  await UserSetting.findOneAndUpdate(
    { user_id: userId },
    {
      $set: {
        google_calendar_sync_enabled: true,
        updated_at: new Date(),
      },
    },
  );
};

const disableGoogleCalendarSyncSetting = async (userId) => {
  await UserSetting.findOneAndUpdate(
    { user_id: userId },
    {
      $set: {
        google_calendar_sync_enabled: false,
        updated_at: new Date(),
      },
    },
  );
};

/**
 * POST /api/integrations/google/connect
 * Store or update user's Google Calendar integration tokens.
 */
const connectGoogleCalendar = async (req, res, next) => {
  try {
    const {
      access_token,
      refresh_token,
      server_auth_code,
      token_expires,
      calendar_id,
      scope,
    } = req.body;

    let resolvedAccessToken = null;
    let resolvedRefreshToken =
      typeof refresh_token === "string" && refresh_token.trim()
        ? refresh_token.trim()
        : null;
    let tokenExpiryValue = null;
    let resolvedScope =
      typeof scope === "string" && scope.trim() ? scope.trim() : null;

    if (typeof server_auth_code === "string" && server_auth_code.trim()) {
      const exchanged = await exchangeServerAuthCode(server_auth_code);
      if (!exchanged?.access_token) {
        throw new BadRequestError("Failed to exchange Google authorization code");
      }
      resolvedAccessToken = exchanged.access_token;
      resolvedRefreshToken = exchanged.refresh_token || resolvedRefreshToken;
      tokenExpiryValue = exchanged.token_expires || null;
      resolvedScope = exchanged.scope || resolvedScope;
    } else if (typeof access_token === "string" && access_token.trim()) {
      resolvedAccessToken = access_token.trim();
      if (token_expires) {
        const parsed = new Date(token_expires);
        if (Number.isNaN(parsed.getTime())) {
          throw new BadRequestError("token_expires must be a valid date/time");
        }
        tokenExpiryValue = parsed;
      }
    } else {
      throw new BadRequestError("access_token or server_auth_code is required");
    }

    const updatePayload = {
      access_token: resolvedAccessToken,
      refresh_token: resolvedRefreshToken,
      token_expires: tokenExpiryValue,
      calendar_id:
        typeof calendar_id === "string" && calendar_id.trim()
          ? calendar_id.trim()
          : "primary",
      scope: resolvedScope,
      is_active: true,
      updated_at: new Date(),
    };

    const integration = await Integration.findOneAndUpdate(
      {
        user_id: req.userId,
        provider: "google_calendar",
      },
      {
        $set: updatePayload,
        $setOnInsert: {
          user_id: req.userId,
          provider: "google_calendar",
          created_at: new Date(),
        },
      },
      {
        upsert: true,
        new: true,
      },
    ).lean();

    await enableGoogleCalendarSyncSetting(req.userId);
    scheduleGoogleCalendarBackfill(req.userId);

    res.status(200).json({
      status: "success",
      message: "Google Calendar connected",
      data: buildApiData(req, {
        integration: sanitizeIntegration(integration, (req.user && req.user.timezone) || "UTC"),
        google_calendar_sync_enabled: true,
      }),
    });
  } catch (error) {
    next(error);
  }
};

/**
 * DELETE /api/integrations/google
 * Disconnect Google Calendar and turn sync toggle off.
 */
const disconnectGoogleCalendar = async (req, res, next) => {
  try {
    const integration = await Integration.findOne({
      user_id: req.userId,
      provider: "google_calendar",
      is_active: true,
    }).lean();

    if (!integration) {
      throw new NotFoundError("Google Calendar is not connected");
    }

    await Integration.updateOne(
      { _id: integration._id },
      {
        $set: {
          is_active: false,
          updated_at: new Date(),
        },
      },
    );

    await disableGoogleCalendarSyncSetting(req.userId);

    res.status(200).json({
      status: "success",
      message: "Google Calendar disconnected",
      data: buildApiData(req, {
        provider: "google_calendar",
        is_active: false,
        google_calendar_sync_enabled: false,
      }),
    });
  } catch (error) {
    next(error);
  }
};

/**
 * GET /api/integrations
 * Return active integrations for authenticated user.
 */
const getIntegrations = async (req, res, next) => {
  try {
    const integrations = await Integration.find({
      user_id: req.userId,
      is_active: true,
    })
      .select(
        "provider calendar_id token_expires scope is_active last_synced_at created_at updated_at",
      )
      .sort({ updated_at: -1 })
      .lean();

    const timezone = (req.user && req.user.timezone) || "UTC";
    res.status(200).json({
      status: "success",
      data: buildApiData(req, {
        integrations: integrations.map((row) => sanitizeIntegration(row, timezone)),
      }),
    });
  } catch (error) {
    next(error);
  }
};

module.exports = {
  connectGoogleCalendar,
  disconnectGoogleCalendar,
  getIntegrations,
};

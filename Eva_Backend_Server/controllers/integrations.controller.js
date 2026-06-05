/**
 * Integrations Controller
 * Phase 11 Google Calendar connect/list endpoints.
 */

const { Integration } = require("../models");
const { BadRequestError } = require("../middleware/errorHandler");
const { localizeApiPayload, withApiTimezone } = require("../utils/apiDateTime");

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

/**
 * POST /api/integrations/google/connect
 * Store or update user's Google Calendar integration tokens.
 */
const connectGoogleCalendar = async (req, res, next) => {
  try {
    const { access_token, refresh_token, token_expires, calendar_id, scope } =
      req.body;

    if (!access_token || typeof access_token !== "string") {
      throw new BadRequestError("access_token is required");
    }

    let tokenExpiryValue = null;
    if (token_expires) {
      const parsed = new Date(token_expires);
      if (Number.isNaN(parsed.getTime())) {
        throw new BadRequestError("token_expires must be a valid date/time");
      }
      tokenExpiryValue = parsed;
    }

    const updatePayload = {
      access_token: access_token.trim(),
      refresh_token:
        typeof refresh_token === "string" && refresh_token.trim()
          ? refresh_token.trim()
          : null,
      token_expires: tokenExpiryValue,
      calendar_id:
        typeof calendar_id === "string" && calendar_id.trim()
          ? calendar_id.trim()
          : "primary",
      scope: typeof scope === "string" && scope.trim() ? scope.trim() : null,
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

    res.status(200).json({
      status: "success",
      message: "Google Calendar connected",
      data: buildApiData(req, {
        integration: sanitizeIntegration(integration, (req.user && req.user.timezone) || "UTC"),
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
  getIntegrations,
};

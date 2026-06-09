/**
 * Google Calendar sync toggle helpers.
 */

const isGoogleCalendarSyncEnabled = (userSettings) =>
  userSettings?.google_calendar_sync_enabled === true;

module.exports = {
  isGoogleCalendarSyncEnabled,
};

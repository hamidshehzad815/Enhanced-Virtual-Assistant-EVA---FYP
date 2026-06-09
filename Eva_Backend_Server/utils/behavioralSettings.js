/** User-facing behavioral analytics toggle helpers. */

const isBehavioralAnalyticsEnabled = (settings) => {
  if (!settings) {
    return true;
  }
  if (settings.behavioral_analytics_enabled === undefined) {
    return true;
  }
  return Boolean(settings.behavioral_analytics_enabled);
};

module.exports = {
  isBehavioralAnalyticsEnabled,
};

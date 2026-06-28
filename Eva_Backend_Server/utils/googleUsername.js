const { User } = require("../models");

const sanitizeUsernameBase = (value) => {
  const cleaned = String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9_]/g, "")
    .slice(0, 24);

  if (cleaned.length >= 3) {
    return cleaned;
  }

  return "eva_user";
};

/**
 * Build a unique username for a new Google sign-up.
 */
const generateUniqueUsername = async (email, name) => {
  const emailLocal = String(email || "").split("@")[0];
  const base = sanitizeUsernameBase(emailLocal || name || "eva_user");

  let candidate = base;
  let suffix = 0;

  while (await User.findOne({ username: candidate })) {
    suffix += 1;
    candidate = `${base.slice(0, Math.max(3, 24 - String(suffix).length - 1))}_${suffix}`;
  }

  return candidate;
};

module.exports = {
  generateUniqueUsername,
};

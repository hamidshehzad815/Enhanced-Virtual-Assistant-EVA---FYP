const { User } = require("../models");

const USERNAME_MAX = 30;

// Keep only lowercase letters (usernames are letters-only); fall back if too short.
const sanitizeUsernameBase = (value) => {
  const cleaned = String(value || "")
    .toLowerCase()
    .replace(/[^a-z]/g, "")
    .slice(0, 24);

  if (cleaned.length >= 3) {
    return cleaned;
  }

  return "evauser";
};

// Convert a positive integer to a lowercase-letter suffix: 1->a, 26->z, 27->aa.
const numberToAlphaSuffix = (n) => {
  let result = "";
  let value = n;
  while (value > 0) {
    value -= 1;
    result = String.fromCharCode(97 + (value % 26)) + result;
    value = Math.floor(value / 26);
  }
  return result;
};

/**
 * Build a unique, lowercase-letters-only username for a new Google sign-up.
 * Uniqueness collisions get an alphabetic suffix (a, b, …, z, aa, …) so the
 * result still matches the username rule ^[a-z]{3,30}$.
 */
const generateUniqueUsername = async (email, name) => {
  const emailLocal = String(email || "").split("@")[0];
  const base = sanitizeUsernameBase(emailLocal || name || "evauser");

  let candidate = base;
  let suffix = 0;

  while (await User.findOne({ username: candidate })) {
    suffix += 1;
    const alpha = numberToAlphaSuffix(suffix);
    const keep = Math.max(3, USERNAME_MAX - alpha.length);
    candidate = `${base.slice(0, keep)}${alpha}`;
  }

  return candidate;
};

module.exports = {
  generateUniqueUsername,
};

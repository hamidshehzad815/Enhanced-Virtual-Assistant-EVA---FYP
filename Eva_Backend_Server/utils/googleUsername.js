const { User } = require("../models");

const USERNAME_MIN = 3;
const USERNAME_MAX = 30;

// Lowercase and keep only letters (usernames are letters-only).
const onlyLetters = (value) =>
  String(value || "").toLowerCase().replace(/[^a-z]/g, "");

/**
 * Build the username base from a full name:
 *   - use the FIRST word if it's long enough (>= 3 letters);
 *   - if the first word is too short, append the SECOND word;
 *   - fall back to "evauser" if there is nothing usable.
 * (Email is intentionally NOT used — roll-number emails like
 *  f2022266297@umt.edu.pk have no useful letters.)
 */
const buildBaseFromName = (name) => {
  const words = String(name || "")
    .split(/\s+/)
    .map(onlyLetters)
    .filter(Boolean);

  const first = words[0] || "";
  let base = first;
  if (first.length < USERNAME_MIN && words[1]) {
    base = first + words[1];
  }

  base = base.slice(0, 24);
  return base.length >= USERNAME_MIN ? base : "evauser";
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
 * Build a unique, lowercase-letters-only username for a new Google sign-up,
 * derived from the user's full name. Uniqueness collisions get an alphabetic
 * suffix (a, b, …, z, aa) so the result still matches the rule ^[a-z]{3,30}$.
 */
const generateUniqueUsername = async (email, name) => {
  const base = buildBaseFromName(name);

  let candidate = base;
  let suffix = 0;

  while (await User.findOne({ username: candidate })) {
    suffix += 1;
    const alpha = numberToAlphaSuffix(suffix);
    const keep = Math.max(USERNAME_MIN, USERNAME_MAX - alpha.length);
    candidate = `${base.slice(0, keep)}${alpha}`;
  }

  return candidate;
};

module.exports = {
  generateUniqueUsername,
};

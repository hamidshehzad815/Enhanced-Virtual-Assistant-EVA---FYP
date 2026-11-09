/**
 * Auth input validation (single source of truth for register / login /
 * forgot-password / reset-password).
 *
 * The rules deliberately mirror what mainstream sites do, so that passwords
 * produced by browser / OS / password-manager generators (which are usually
 * letters + digits, sometimes with `-`) are accepted:
 *
 *   name     : 2–100 chars, letters / spaces / . ' - only, at least 2 letters
 *   username : 3–30 chars, starts with a letter, then a-z 0-9 . _ ; no "..",
 *              "__", ".", "_" at the end; not a reserved word
 *   email    : practical RFC-5322 subset, max 254 chars, TLD of 2+ letters
 *   password : 8–64 chars, at least one letter AND at least one number or
 *              symbol, not a commonly used password, not a trivial pattern
 *              (aaaaaaaa, 12345678, abcdefgh), must not contain the user's
 *              email name / username, and must not equal the old password
 *              (checked by the controller)
 *
 * The backend is authoritative; the web and Flutter clients mirror these rules
 * for instant feedback (Web_Frontend/src/utils/authValidation.js and
 * Frontend/lib/core/utils/auth_validators.dart). Keep the three in sync.
 */

const { BadRequestError } = require("../middleware/errorHandler");

const NAME_MIN = 2;
const NAME_MAX = 100;
const USERNAME_MIN = 3;
const USERNAME_MAX = 30;
const EMAIL_MAX = 254;
const PASSWORD_MIN = 8;
const PASSWORD_MAX = 64;
// bcrypt only uses the first 72 bytes; refuse anything longer rather than
// silently truncating it.
const PASSWORD_MAX_BYTES = 72;

const NAME_ALLOWED_RE = /^[\p{L}\p{M}][\p{L}\p{M} .'’-]*$/u;
const USERNAME_RE = /^[a-z][a-z0-9._]*$/;
const EMAIL_RE =
  /^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*\.[A-Za-z]{2,}$/;

const RESERVED_USERNAMES = new Set([
  "admin",
  "administrator",
  "root",
  "support",
  "help",
  "system",
  "moderator",
  "staff",
  "official",
  "security",
  "api",
  "null",
  "undefined",
  "eva",
  "evaapp",
  "evasupport",
  "evaadmin",
]);

// Small deny-list of the most frequently breached passwords. Compared on a
// lowercased copy. (Everything shorter than 8 chars is rejected by length.)
const COMMON_PASSWORDS = new Set([
  "password",
  "password1",
  "password12",
  "password123",
  "password1234",
  "passw0rd",
  "p@ssw0rd",
  "p@ssword",
  "pa$$w0rd",
  "123456789",
  "1234567890",
  "12345678",
  "123123123",
  "11111111",
  "00000000",
  "1q2w3e4r",
  "1q2w3e4r5t",
  "1qaz2wsx",
  "qwerty123",
  "qwertyui",
  "qwertyuiop",
  "qwerty12345",
  "asdfghjk",
  "asdfghjkl",
  "zxcvbnm1",
  "iloveyou",
  "iloveyou1",
  "letmein1",
  "welcome1",
  "welcome123",
  "admin123",
  "admin1234",
  "administrator",
  "abc12345",
  "abcd1234",
  "abcd12345",
  "monkey123",
  "dragon123",
  "football1",
  "baseball1",
  "superman1",
  "trustno1",
  "sunshine1",
  "princess1",
  "changeme",
  "changeme1",
  "master123",
  "login123",
  "pakistan1",
  "pakistan123",
  "eva12345",
  "eva123456",
  "evaapp123",
  "student123",
  "university1",
]);

const trimString = (value) => (typeof value === "string" ? value.trim() : "");

// ── Field validators ────────────────────────────────────────────────────────

const validateName = (value) => {
  const name = trimString(value).replace(/\s+/g, " ");
  if (!name) return "Full name is required";
  if (name.length < NAME_MIN) return `Name must be at least ${NAME_MIN} characters`;
  if (name.length > NAME_MAX) return `Name cannot exceed ${NAME_MAX} characters`;
  if (!NAME_ALLOWED_RE.test(name) || (name.match(/\p{L}/gu) || []).length < 2) {
    return "Name can only contain letters, spaces, apostrophes, hyphens and periods";
  }
  return null;
};

const validateUsername = (value) => {
  const username = trimString(value).toLowerCase();
  if (!username) return "Username is required";
  if (username.length < USERNAME_MIN) {
    return `Username must be at least ${USERNAME_MIN} characters`;
  }
  if (username.length > USERNAME_MAX) {
    return `Username cannot exceed ${USERNAME_MAX} characters`;
  }
  if (!/^[a-z]/.test(username)) return "Username must start with a letter";
  if (!USERNAME_RE.test(username)) {
    return "Username can only contain letters, numbers, periods and underscores";
  }
  if (/[._]{2}/.test(username)) {
    return "Username cannot have two periods or underscores in a row";
  }
  if (/[._]$/.test(username)) {
    return "Username cannot end with a period or underscore";
  }
  if (RESERVED_USERNAMES.has(username)) {
    return "This username is not available. Please choose another one";
  }
  return null;
};

const validateEmail = (value) => {
  const email = trimString(value);
  if (!email) return "Email is required";
  if (email.length > EMAIL_MAX) return "Email address is too long";
  const [local = ""] = email.split("@");
  if (
    !EMAIL_RE.test(email) ||
    local.length > 64 ||
    local.startsWith(".") ||
    local.endsWith(".") ||
    email.includes("..")
  ) {
    return "Please enter a valid email address";
  }
  return null;
};

/** Is it just one or two distinct chars (aaaaaaaa) or a straight run (12345678 / abcdefgh)? */
const isTrivialPattern = (password) => {
  if (new Set(password).size <= 2) return true; // aaaaaaaa, aaaaaaa1, abababab
  const lower = password.toLowerCase();
  if (lower.length < 6) return false;
  let ascending = true;
  let descending = true;
  for (let i = 1; i < lower.length; i += 1) {
    const diff = lower.charCodeAt(i) - lower.charCodeAt(i - 1);
    if (diff !== 1) ascending = false;
    if (diff !== -1) descending = false;
  }
  return ascending || descending;
};

/**
 * Validate a NEW password (register / reset). Returns an error string or null.
 *
 * @param {string} value
 * @param {{ email?: string, username?: string }} [context] - personal data the
 *   password must not contain.
 */
const validatePassword = (value, context = {}) => {
  const password = typeof value === "string" ? value : "";
  if (!password) return "Password is required";
  if (password.length < PASSWORD_MIN) {
    return `Password must be at least ${PASSWORD_MIN} characters`;
  }
  if (password.length > PASSWORD_MAX || Buffer.byteLength(password) > PASSWORD_MAX_BYTES) {
    return `Password cannot be longer than ${PASSWORD_MAX} characters`;
  }
  if (!password.trim()) return "Password cannot be only spaces";
  if (!/\p{L}/u.test(password)) return "Password must include at least one letter";
  if (!/[\p{N}\p{S}\p{P}]/u.test(password)) {
    return "Password must include at least one number or symbol";
  }

  const lower = password.toLowerCase();
  if (COMMON_PASSWORDS.has(lower) || isTrivialPattern(password)) {
    return "This password is too common. Please choose a stronger one";
  }

  const emailName = trimString(context.email).split("@")[0].toLowerCase();
  if (emailName.length >= 4 && lower.includes(emailName)) {
    return "Password cannot contain your email address";
  }
  const username = trimString(context.username).toLowerCase();
  if (username.length >= 4 && lower.includes(username)) {
    return "Password cannot contain your username";
  }
  return null;
};

// ── Form-level validators ───────────────────────────────────────────────────

/** Build a { field: message } map of registration errors (empty if all valid). */
const validateRegistration = ({ name, username, email, password }) => {
  const errors = {};
  const nameError = validateName(name);
  if (nameError) errors.name = nameError;
  const usernameError = validateUsername(username);
  if (usernameError) errors.username = usernameError;
  const emailError = validateEmail(email);
  if (emailError) errors.email = emailError;
  const passwordError = validatePassword(password, { email, username });
  if (passwordError) errors.password = passwordError;
  return errors;
};

/** Login only checks presence/type — never password strength. */
const validateLogin = ({ email, password }) => {
  const errors = {};
  const emailError = validateEmail(email);
  if (emailError) errors.email = emailError;
  if (typeof password !== "string" || !password) {
    errors.password = "Password is required";
  } else if (password.length > 1024) {
    // Guard against bcrypt/CPU abuse with absurd payloads.
    errors.password = "Password is too long";
  }
  return errors;
};

/** Reset-password form (token comes from the emailed link). */
const validateResetPassword = ({ token, new_password: newPassword, confirm_password: confirmPassword }) => {
  const errors = {};
  if (typeof token !== "string" || !token.trim()) {
    errors.token = "This reset link is invalid. Please request a new one";
  }
  const passwordError = validatePassword(newPassword);
  if (passwordError) errors.new_password = passwordError;
  if (typeof confirmPassword !== "string" || !confirmPassword) {
    errors.confirm_password = "Please confirm your new password";
  } else if (!passwordError && newPassword !== confirmPassword) {
    errors.confirm_password = "Passwords do not match";
  }
  return errors;
};

/**
 * Throw a 400 with a per-field `errors` object if any field failed.
 *
 * Response shape:
 *   { status: "fail", message: "<first error>", field: "<first field>",
 *     errors: { field: message } }
 *
 * `message` is the first specific problem (not a generic "Validation failed")
 * so even clients that only display `message` show something useful; `errors`
 * lets form clients put each message under the right input.
 */
const throwIfErrors = (errors) => {
  const fields = errors ? Object.keys(errors) : [];
  if (fields.length > 0) {
    const err = new BadRequestError(errors[fields[0]]);
    err.errors = errors;
    err.field = fields[0];
    throw err;
  }
};

module.exports = {
  PASSWORD_MIN,
  PASSWORD_MAX,
  validateName,
  validateUsername,
  validateEmail,
  validatePassword,
  validateRegistration,
  validateLogin,
  validateResetPassword,
  throwIfErrors,
};

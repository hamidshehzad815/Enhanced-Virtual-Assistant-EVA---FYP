/**
 * Auth input validation (single source of truth for register + reset-password).
 *
 * These rules must match the app-side validation so a value the app accepts is
 * also accepted by the backend, and vice versa. The backend is authoritative.
 *
 * Canonical rules:
 *   name     : 2–100 characters
 *   username : ^[a-z]{3,30}$  (lowercase letters only — no numbers/underscore/symbols)
 *   email    : basic valid email format
 *   password : min 8, with lowercase + uppercase + number + symbol
 */

const { BadRequestError } = require("../middleware/errorHandler");

const NAME_MIN = 2;
const NAME_MAX = 100;
const USERNAME_RE = /^[a-z]{3,30}$/;
const EMAIL_RE = /^\S+@\S+\.\S+$/;
const PASSWORD_MIN = 8;

const validateName = (value) => {
  const name = typeof value === "string" ? value.trim() : "";
  if (!name) return "Name is required";
  if (name.length < NAME_MIN) return `Name must be at least ${NAME_MIN} characters`;
  if (name.length > NAME_MAX) return `Name cannot exceed ${NAME_MAX} characters`;
  return null;
};

const validateUsername = (value) => {
  const username = typeof value === "string" ? value.trim() : "";
  if (!username) return "Username is required";
  if (!USERNAME_RE.test(username)) {
    return "Username must be 3-30 lowercase letters (a-z) only — no numbers, spaces, or symbols";
  }
  return null;
};

const validateEmail = (value) => {
  const email = typeof value === "string" ? value.trim() : "";
  if (!email) return "Email is required";
  if (!EMAIL_RE.test(email)) return "Please provide a valid email address";
  return null;
};

const validatePassword = (value) => {
  const password = typeof value === "string" ? value : "";
  if (!password) return "Password is required";
  if (password.length < PASSWORD_MIN) {
    return `Password must be at least ${PASSWORD_MIN} characters`;
  }
  if (!/[a-z]/.test(password)) return "Password must include a lowercase letter";
  if (!/[A-Z]/.test(password)) return "Password must include an uppercase letter";
  if (!/[0-9]/.test(password)) return "Password must include a number";
  if (!/[^A-Za-z0-9]/.test(password)) return "Password must include a symbol";
  return null;
};

/** Build a { field: message } map of registration errors (empty if all valid). */
const validateRegistration = ({ name, username, email, password }) => {
  const errors = {};
  const nameError = validateName(name);
  if (nameError) errors.name = nameError;
  const usernameError = validateUsername(username);
  if (usernameError) errors.username = usernameError;
  const emailError = validateEmail(email);
  if (emailError) errors.email = emailError;
  const passwordError = validatePassword(password);
  if (passwordError) errors.password = passwordError;
  return errors;
};

/**
 * Throw a 400 with a per-field `errors` object if any field failed.
 * Response shape: { status: "fail", message: "Validation failed", errors: { field: msg } }
 * so the client can map each message to its field.
 */
const throwIfErrors = (errors) => {
  if (errors && Object.keys(errors).length > 0) {
    const err = new BadRequestError("Validation failed");
    err.errors = errors;
    throw err;
  }
};

module.exports = {
  validateName,
  validateUsername,
  validateEmail,
  validatePassword,
  validateRegistration,
  throwIfErrors,
};

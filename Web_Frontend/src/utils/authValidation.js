/**
 * Client-side auth validation. Mirrors Eva_Backend_Server/utils/authValidation.js
 * (the backend is authoritative) so users get instant feedback and anything
 * accepted here is accepted by the server. Keep both files in sync.
 *
 * Password rule (same as most real sites, and compatible with the passwords
 * Chrome / Google Password Manager / Safari / 1Password generate):
 *   8–64 characters, at least one letter, at least one number or symbol,
 *   not a commonly used password, not a trivial pattern.
 */

const NAME_ALLOWED_RE = /^[\p{L}\p{M}][\p{L}\p{M} .'’-]*$/u;
const USERNAME_RE = /^[a-z][a-z0-9._]*$/;
const EMAIL_RE =
  /^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*\.[A-Za-z]{2,}$/;

const RESERVED_USERNAMES = new Set([
  'admin', 'administrator', 'root', 'support', 'help', 'system', 'moderator',
  'staff', 'official', 'security', 'api', 'null', 'undefined', 'eva',
  'evaapp', 'evasupport', 'evaadmin',
]);

const COMMON_PASSWORDS = new Set([
  'password', 'password1', 'password12', 'password123', 'password1234',
  'passw0rd', 'p@ssw0rd', 'p@ssword', 'pa$$w0rd', '123456789', '1234567890',
  '12345678', '123123123', '11111111', '00000000', '1q2w3e4r', '1q2w3e4r5t',
  '1qaz2wsx', 'qwerty123', 'qwertyui', 'qwertyuiop', 'qwerty12345',
  'asdfghjk', 'asdfghjkl', 'zxcvbnm1', 'iloveyou', 'iloveyou1', 'letmein1',
  'welcome1', 'welcome123', 'admin123', 'admin1234', 'administrator',
  'abc12345', 'abcd1234', 'abcd12345', 'monkey123', 'dragon123', 'football1',
  'baseball1', 'superman1', 'trustno1', 'sunshine1', 'princess1', 'changeme',
  'changeme1', 'master123', 'login123', 'pakistan1', 'pakistan123',
  'eva12345', 'eva123456', 'evaapp123', 'student123', 'university1',
]);

export const PASSWORD_MIN = 8;
export const PASSWORD_MAX = 64;

const clean = (v) => (typeof v === 'string' ? v.trim() : '');

export const validateName = (value) => {
  const name = clean(value).replace(/\s+/g, ' ');
  if (!name) return 'Full name is required';
  if (name.length < 2) return 'Name must be at least 2 characters';
  if (name.length > 100) return 'Name cannot exceed 100 characters';
  if (!NAME_ALLOWED_RE.test(name) || (name.match(/\p{L}/gu) || []).length < 2) {
    return 'Name can only contain letters, spaces, apostrophes, hyphens and periods';
  }
  return null;
};

export const validateUsername = (value) => {
  const username = clean(value).toLowerCase();
  if (!username) return 'Username is required';
  if (username.length < 3) return 'Username must be at least 3 characters';
  if (username.length > 30) return 'Username cannot exceed 30 characters';
  if (!/^[a-z]/.test(username)) return 'Username must start with a letter';
  if (!USERNAME_RE.test(username)) {
    return 'Username can only contain letters, numbers, periods and underscores';
  }
  if (/[._]{2}/.test(username)) return 'Username cannot have two periods or underscores in a row';
  if (/[._]$/.test(username)) return 'Username cannot end with a period or underscore';
  if (RESERVED_USERNAMES.has(username)) return 'This username is not available. Please choose another one';
  return null;
};

export const validateEmail = (value) => {
  const email = clean(value);
  if (!email) return 'Email is required';
  if (email.length > 254) return 'Email address is too long';
  const local = email.split('@')[0] || '';
  if (!EMAIL_RE.test(email) || local.length > 64 || local.startsWith('.') || local.endsWith('.') || email.includes('..')) {
    return 'Please enter a valid email address';
  }
  return null;
};

const isTrivialPattern = (password) => {
  if (new Set(password).size <= 2) return true;
  const lower = password.toLowerCase();
  if (lower.length < 6) return false;
  let asc = true;
  let desc = true;
  for (let i = 1; i < lower.length; i += 1) {
    const d = lower.charCodeAt(i) - lower.charCodeAt(i - 1);
    if (d !== 1) asc = false;
    if (d !== -1) desc = false;
  }
  return asc || desc;
};

/** Individual requirement checks — drives the live checklist UI. */
export const passwordChecks = (password = '') => ({
  length: password.length >= PASSWORD_MIN && password.length <= PASSWORD_MAX,
  letter: /\p{L}/u.test(password),
  numberOrSymbol: /[\p{N}\p{S}\p{P}]/u.test(password),
});

/** Validate a NEW password. `context` = { email, username } the password must not contain. */
export const validatePassword = (value, context = {}) => {
  const password = typeof value === 'string' ? value : '';
  if (!password) return 'Password is required';
  if (password.length < PASSWORD_MIN) return `Password must be at least ${PASSWORD_MIN} characters`;
  if (password.length > PASSWORD_MAX) return `Password cannot be longer than ${PASSWORD_MAX} characters`;
  if (!password.trim()) return 'Password cannot be only spaces';
  if (!/\p{L}/u.test(password)) return 'Password must include at least one letter';
  if (!/[\p{N}\p{S}\p{P}]/u.test(password)) return 'Password must include at least one number or symbol';

  const lower = password.toLowerCase();
  if (COMMON_PASSWORDS.has(lower) || isTrivialPattern(password)) {
    return 'This password is too common. Please choose a stronger one';
  }
  const emailName = clean(context.email).split('@')[0].toLowerCase();
  if (emailName.length >= 4 && lower.includes(emailName)) return 'Password cannot contain your email address';
  const username = clean(context.username).toLowerCase();
  if (username.length >= 4 && lower.includes(username)) return 'Password cannot contain your username';
  return null;
};

export const validateConfirmPassword = (password, confirm) => {
  if (!confirm) return 'Please confirm your new password';
  if (password !== confirm) return 'Passwords do not match';
  return null;
};

/**
 * Strength for the meter: { level: 0-3, label, valid }.
 * 0 = empty, 1 = weak (fails a rule), 2 = good, 3 = strong.
 */
export const passwordStrength = (password = '', context = {}) => {
  if (!password) return { level: 0, label: '', valid: false };
  if (validatePassword(password, context)) return { level: 1, label: 'Weak', valid: false };
  let score = 0;
  if (password.length >= 12) score += 1;
  if (password.length >= 16) score += 1;
  if (/\p{Ll}/u.test(password) && /\p{Lu}/u.test(password)) score += 1;
  if (/\p{N}/u.test(password) && /[\p{S}\p{P}]/u.test(password)) score += 1;
  return score >= 3
    ? { level: 3, label: 'Strong', valid: true }
    : { level: 2, label: 'Good', valid: true };
};

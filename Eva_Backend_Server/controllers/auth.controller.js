/**
 * Authentication Controller
 * Handles register, login, refresh, logout, and user info
 */

const crypto = require("crypto");
const jwt = require("jsonwebtoken");
const { User, UserSetting } = require("../models");
const {
  BadRequestError,
  UnauthorizedError,
  ForbiddenError,
  ConflictError,
} = require("../middleware/errorHandler");
const logger = require("../config/logger");
const { normalizeTimezone } = require("../utils/timezone");
const {
  sendVerificationEmail,
  sendPasswordResetEmail,
} = require("../services/email.service");
const { renderEmailVerificationPage } = require("../utils/verificationPage");
const { allowFriendRequestsToBoolean } = require("../utils/friendSettings");
const { verifyGoogleIdToken } = require("../utils/googleIdToken");
const { generateUniqueUsername } = require("../utils/googleUsername");
const {
  validateRegistration,
  validateLogin,
  validateEmail,
  validatePassword,
  validateResetPassword,
  throwIfErrors,
} = require("../utils/authValidation");

/** Build an ApiError subclass instance carrying a machine-readable `code`. */
const withCode = (error, code, field) => {
  error.code = code;
  if (field) error.field = field;
  return error;
};

/** 409 that points at a specific form field. */
const fieldConflict = (field, message) => {
  const error = new ConflictError(message);
  error.field = field;
  error.errors = { [field]: message };
  return error;
};

const serializeAuthUser = (user) => ({
  _id: user._id,
  name: user.name,
  username: user.username,
  email: user.email,
  is_verified: Boolean(user.is_verified),
  profile_picture: user.profile_picture || null,
});

/**
 * Generate JWT access token
 * @param {string} userId - User ID
 * @returns {string} Access token
 */
const generateAccessToken = (userId) => {
  return jwt.sign({ userId }, process.env.JWT_ACCESS_SECRET, {
    expiresIn: process.env.JWT_ACCESS_EXPIRES || "15m",
  });
};

/**
 * Generate JWT refresh token
 * @param {string} userId - User ID
 * @returns {string} Refresh token
 */
const generateRefreshToken = (userId) => {
  return jwt.sign({ userId }, process.env.JWT_REFRESH_SECRET, {
    expiresIn: process.env.JWT_REFRESH_EXPIRES || "7d",
  });
};

/**
 * Generate email verification token
 * @returns {Object} { token, hashedToken, expires }
 */
const generateVerificationToken = () => {
  const token = crypto.randomBytes(32).toString("hex");
  const hashedToken = crypto.createHash("sha256").update(token).digest("hex");
  const expires = new Date(Date.now() + 24 * 60 * 60 * 1000); // 24 hours
  return { token, hashedToken, expires };
};

/**
 * Generate password reset token
 * @returns {Object} { token, hashedToken, expires }
 */
const generatePasswordResetToken = () => {
  const token = crypto.randomBytes(32).toString("hex");
  const hashedToken = crypto.createHash("sha256").update(token).digest("hex");
  const expires = new Date(Date.now() + 60 * 60 * 1000); // 1 hour
  return { token, hashedToken, expires };
};

const issueAuthTokensResponse = async (
  user,
  res,
  { message, statusCode = 200, isNewUser = false } = {},
) => {
  const accessToken = generateAccessToken(user._id);
  const refreshToken = generateRefreshToken(user._id);

  await user.setRefreshToken(refreshToken);
  await user.updateLastLogin();

  res.status(statusCode).json({
    status: "success",
    message,
    data: {
      user: serializeAuthUser(user),
      tokens: {
        access_token: accessToken,
        refresh_token: refreshToken,
      },
      is_new_user: isNewUser,
    },
  });
};

/**
 * POST /api/auth/register
 * Register a new user
 */
const register = async (req, res, next) => {
  try {
    const { name, username, email, password, timezone } = req.body || {};

    // Validate fields (required + format) with per-field error messages.
    throwIfErrors(validateRegistration({ name, username, email, password }));

    const normalizedName = name.trim().replace(/\s+/g, " ");
    const normalizedUsername = username.trim().toLowerCase();
    const normalizedEmail = email.trim().toLowerCase();

    // Check if email already exists
    const existingEmail = await User.findOne({ email: normalizedEmail });
    if (existingEmail) {
      throw fieldConflict("email", "An account with this email already exists");
    }

    // Check if username already exists
    const existingUsername = await User.findOne({ username: normalizedUsername });
    if (existingUsername) {
      throw fieldConflict("username", "This username is already taken");
    }

    // Generate verification token
    const { token, hashedToken, expires } = generateVerificationToken();

    // Create user
    const userTimezone = normalizeTimezone(timezone || "Asia/Karachi");

    const user = await User.create({
      name: normalizedName,
      username: normalizedUsername,
      email: normalizedEmail,
      password_hash: password,
      timezone: userTimezone,
      auth_provider: "local",
      is_verified: false,
      email_verification_token: hashedToken,
      email_verification_expires: expires,
    });

    // Create default settings for user
    await UserSetting.createDefaultSettings(user._id);

    // Send verification email
    const emailSent = await sendVerificationEmail(user.email, user.name, token);

    logger.info("User registered", {
      userId: user._id,
      email: user.email,
      emailSent,
    });

    const response = {
      status: "success",
      message: emailSent
        ? "Registration successful. Please check your email to verify your account."
        : "Registration successful. Please verify your email to login.",
      data: {
        user: serializeAuthUser(user),
        email_sent: emailSent,
      },
    };

    res.status(201).json(response);
  } catch (error) {
    next(error);
  }
};

/**
 * POST /api/auth/login
 * Login with email and password
 */
const login = async (req, res, next) => {
  try {
    const { email, password } = req.body || {};

    // Login checks presence/format only — never password strength, so users
    // with older/simpler passwords can still sign in.
    throwIfErrors(validateLogin({ email, password }));

    // Find user by email (include password_hash)
    const user = await User.findOne({
      email: email.trim().toLowerCase(),
    }).select("+password_hash");

    // Same message for "no such user" and "wrong password" (no enumeration).
    const invalidCredentials = () =>
      withCode(
        new UnauthorizedError("Incorrect email or password"),
        "INVALID_CREDENTIALS",
      );

    if (!user) {
      throw invalidCredentials();
    }

    // Google-only accounts have no password to check.
    if (!user.password_hash) {
      throw withCode(
        new UnauthorizedError(
          "This account uses Google sign-in. Please continue with Google",
        ),
        "USE_GOOGLE_SIGNIN",
      );
    }

    // Verify password
    const isPasswordValid = await user.comparePassword(password);
    if (!isPasswordValid) {
      throw invalidCredentials();
    }

    // Only reveal account state once the password is proven correct.
    if (!user.is_active) {
      throw withCode(
        new UnauthorizedError("This account has been deactivated"),
        "ACCOUNT_DEACTIVATED",
      );
    }

    if (!user.is_verified) {
      throw withCode(
        new ForbiddenError(
          "Please verify your email before signing in. Check your inbox for the verification link",
        ),
        "EMAIL_NOT_VERIFIED",
      );
    }

    // Generate tokens
    await issueAuthTokensResponse(user, res, {
      message: "Login successful",
    });

    logger.info("User logged in", { userId: user._id, email: user.email });
  } catch (error) {
    next(error);
  }
};

/**
 * POST /api/auth/google
 * Sign in or register using a Google ID token from the client.
 */
const googleAuth = async (req, res, next) => {
  try {
    const { id_token: idToken, timezone } = req.body;

    if (!idToken || typeof idToken !== "string") {
      throw new BadRequestError("id_token is required");
    }

    let profile;
    try {
      profile = await verifyGoogleIdToken(idToken);
    } catch (error) {
      logger.warn("Google token verification failed", { message: error.message });
      throw new UnauthorizedError("Invalid Google sign-in token");
    }

    if (!profile.email) {
      throw new UnauthorizedError("Google account email is unavailable");
    }

    if (!profile.emailVerified) {
      throw new UnauthorizedError("Google email is not verified");
    }

    let user = await User.findOne({ email: profile.email }).select("+password_hash");
    let isNewUser = false;

    if (user) {
      if (!user.is_active) {
        throw new UnauthorizedError("Account is deactivated");
      }

      if (user.auth_provider === "local" && user.password_hash) {
        throw new ConflictError(
          "This email is registered with a password. Please sign in with email and password.",
        );
      }

      if (user.auth_provider !== "google") {
        user.auth_provider = "google";
      }

      if (profile.picture && !user.profile_picture) {
        user.profile_picture = profile.picture;
      }

      user.is_verified = true;
      await user.save();
    } else {
      isNewUser = true;
      const username = await generateUniqueUsername(profile.email, profile.name);
      const userTimezone = normalizeTimezone(timezone || "Asia/Karachi");

      user = await User.create({
        name: profile.name || username,
        username,
        email: profile.email,
        auth_provider: "google",
        is_verified: true,
        profile_picture: profile.picture || null,
        timezone: userTimezone,
      });

      await UserSetting.createDefaultSettings(user._id);
    }

    logger.info(isNewUser ? "User registered via Google" : "User logged in via Google", {
      userId: user._id,
      email: user.email,
    });

    await issueAuthTokensResponse(user, res, {
      message: isNewUser ? "Google sign-up successful" : "Google login successful",
      statusCode: isNewUser ? 201 : 200,
      isNewUser,
    });
  } catch (error) {
    next(error);
  }
};

/**
 * POST /api/auth/refresh
 * Refresh access token using refresh token
 */
const refresh = async (req, res, next) => {
  try {
    const { refresh_token } = req.body;

    if (!refresh_token) {
      throw new BadRequestError("Refresh token is required");
    }

    // Verify refresh token
    let decoded;
    try {
      decoded = jwt.verify(refresh_token, process.env.JWT_REFRESH_SECRET);
    } catch (err) {
      if (err.name === "TokenExpiredError") {
        throw new UnauthorizedError(
          "Refresh token expired. Please login again",
        );
      }
      throw new UnauthorizedError("Invalid refresh token");
    }

    // Find user with refresh token hash
    const user = await User.findById(decoded.userId).select(
      "+refresh_token_hash",
    );

    if (!user) {
      throw new UnauthorizedError("User not found");
    }

    if (!user.is_active) {
      throw new UnauthorizedError("Account is deactivated");
    }

    // Verify refresh token matches stored hash
    if (!user.refresh_token_hash) {
      throw new UnauthorizedError(
        "Refresh token invalidated. Please login again",
      );
    }

    const isRefreshTokenValid = await user.compareRefreshToken(refresh_token);
    if (!isRefreshTokenValid) {
      throw new UnauthorizedError("Invalid refresh token. Please login again");
    }

    // Generate new access token
    const newAccessToken = generateAccessToken(user._id);

    // Optionally rotate refresh token for better security
    const newRefreshToken = generateRefreshToken(user._id);
    await user.setRefreshToken(newRefreshToken);

    logger.debug("Token refreshed", { userId: user._id });

    res.json({
      status: "success",
      message: "Token refreshed",
      data: {
        tokens: {
          access_token: newAccessToken,
          refresh_token: newRefreshToken,
        },
      },
    });
  } catch (error) {
    next(error);
  }
};

/**
 * POST /api/auth/logout
 * Logout user and invalidate refresh token
 */
const logout = async (req, res, next) => {
  try {
    // Clear refresh token
    await req.user.clearRefreshToken();

    logger.info("User logged out", { userId: req.user._id });

    res.json({
      status: "success",
      message: "Logged out successfully",
    });
  } catch (error) {
    next(error);
  }
};

/**
 * GET /api/auth/me
 * Get current authenticated user
 */
const getMe = async (req, res, next) => {
  try {
    const settingsDoc = await UserSetting.findOne({ user_id: req.user._id })
      .select([
        "theme",
        "notifications_enabled",
        "push_notifications_enabled",
        "email_notifications_enabled",
        "quiet_hours_enabled",
        "quiet_hours",
        "allow_friend_requests",
      ].join(" "))
      .lean();

    const settings = settingsDoc
      ? {
          ...settingsDoc,
          allow_friend_requests: allowFriendRequestsToBoolean(
            settingsDoc.allow_friend_requests,
          ),
        }
      : null;

    res.json({
      status: "success",
      data: {
        user: serializeAuthUser(req.user),
        settings,
      },
    });
  } catch (error) {
    next(error);
  }
};

/**
 * GET /api/auth/verify-email
 * Verify email with token
 */
const sendVerificationHtml = (res, statusCode, payload) =>
  res.status(statusCode).type("html").send(renderEmailVerificationPage(payload));

const verifyEmail = async (req, res) => {
  try {
    const { token } = req.query;

    if (!token) {
      return sendVerificationHtml(res, 400, {
        success: false,
        title: "Verification failed",
        message:
          "This link is missing a verification code. Open the full link from your email, or request a new verification email from the app.",
      });
    }

    const hashedToken = crypto.createHash("sha256").update(token).digest("hex");

    const user = await User.findOne({
      email_verification_token: hashedToken,
      email_verification_expires: { $gt: new Date() },
    }).select("+email_verification_token +email_verification_expires");

    if (!user) {
      return sendVerificationHtml(res, 400, {
        success: false,
        title: "Link expired or invalid",
        message:
          "This verification link is no longer valid. It may have expired or already been used. Request a new verification email and try again.",
      });
    }

    user.is_verified = true;
    user.email_verification_token = undefined;
    user.email_verification_expires = undefined;
    await user.save();

    logger.info("Email verified", { userId: user._id, email: user.email });

    return sendVerificationHtml(res, 200, {
      success: true,
      title: "Email verified",
      message:
        "Your email is confirmed. You can close this page and sign in to EVA.",
    });
  } catch (error) {
    logger.error("Email verification error", {
      message: error.message,
      stack: error.stack,
    });
    return sendVerificationHtml(res, 500, {
      success: false,
      title: "Something went wrong",
      message:
        "We could not complete verification right now. Please try again in a few minutes.",
    });
  }
};

/**
 * POST /api/auth/resend-verification
 * Resend verification email
 */
const resendVerification = async (req, res, next) => {
  try {
    const { email } = req.body;

    if (!email) {
      throw new BadRequestError("Email is required");
    }

    const user = await User.findOne({ email: email.toLowerCase() });

    if (!user) {
      // Don't reveal if email exists
      return res.json({
        status: "success",
        message:
          "If an account exists with this email, a verification link has been sent.",
      });
    }

    if (user.is_verified) {
      throw new BadRequestError("Email is already verified");
    }

    // Generate new verification token
    const { token, hashedToken, expires } = generateVerificationToken();

    user.email_verification_token = hashedToken;
    user.email_verification_expires = expires;
    await user.save();

    const emailSent = await sendVerificationEmail(user.email, user.name, token);

    logger.info("Verification email resent", {
      userId: user._id,
      email: user.email,
      emailSent,
    });

    res.json({
      status: "success",
      message:
        "If an account exists with this email, a verification link has been sent.",
    });
  } catch (error) {
    next(error);
  }
};

/**
 * POST /api/auth/forgot-password
 * Sends a password reset email if account exists.
 */
const forgotPassword = async (req, res, next) => {
  try {
    const { email } = req.body || {};
    const emailError = validateEmail(email);
    if (emailError) {
      throwIfErrors({ email: emailError });
    }

    const normalizedEmail = email.trim().toLowerCase();
    const user = await User.findOne({ email: normalizedEmail }).select("+password_hash");

    // Generic response to avoid account enumeration.
    const genericMessage =
      "If an account exists with this email, a password reset link has been sent.";

    if (!user || !user.is_active || !user.password_hash) {
      return res.json({
        status: "success",
        message: genericMessage,
      });
    }

    const { token, hashedToken, expires } = generatePasswordResetToken();
    user.password_reset_token = hashedToken;
    user.password_reset_expires = expires;
    await user.save();

    const emailSent = await sendPasswordResetEmail(user.email, user.name, token);
    logger.info("Password reset requested", {
      userId: user._id,
      email: user.email,
      emailSent,
    });

    return res.json({
      status: "success",
      message: genericMessage,
    });
  } catch (error) {
    return next(error);
  }
};

/**
 * POST /api/auth/reset-password
 * Reset password using reset token from email.
 */
const resetPassword = async (req, res, next) => {
  try {
    const { token, new_password, confirm_password } = req.body || {};

    throwIfErrors(
      validateResetPassword({ token, new_password, confirm_password }),
    );

    const hashedToken = crypto.createHash("sha256").update(token.trim()).digest("hex");
    const user = await User.findOne({
      password_reset_token: hashedToken,
      password_reset_expires: { $gt: new Date() },
      is_active: true,
    }).select("+password_reset_token +password_reset_expires +password_hash +refresh_token_hash");

    if (!user) {
      throw withCode(
        new BadRequestError(
          "This reset link is invalid or has expired. Please request a new one",
        ),
        "INVALID_RESET_TOKEN",
        "token",
      );
    }

    // Rules that depend on who the user is.
    const personalError = validatePassword(new_password, {
      email: user.email,
      username: user.username,
    });
    if (personalError) {
      throwIfErrors({ new_password: personalError });
    }

    // Real sites refuse to "reset" to the password you already have.
    if (user.password_hash && (await user.comparePassword(new_password))) {
      throwIfErrors({
        new_password: "New password cannot be the same as your current password",
      });
    }

    user.password_hash = new_password;
    user.password_reset_token = undefined;
    user.password_reset_expires = undefined;
    user.refresh_token_hash = undefined; // force fresh login on all devices
    await user.save();

    logger.info("Password reset successful", { userId: user._id, email: user.email });

    return res.json({
      status: "success",
      message: "Password reset successful. Please login with your new password.",
    });
  } catch (error) {
    return next(error);
  }
};

/**
 * GET /api/auth/reset-password
 * Serves a self-contained HTML page with a password-reset form so the emailed
 * reset link works without a separate frontend. The form POSTs to
 * POST /api/auth/reset-password and shows the result inline. A per-request CSP
 * nonce is set so the inline script runs under Helmet's default CSP.
 */
const renderResetPasswordPage = (req, res) => {
  const token = typeof req.query.token === "string" ? req.query.token : "";
  const tokenJson = JSON.stringify(token);
  const nonce = crypto.randomBytes(16).toString("base64");

  const html = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Reset your EVA password</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: Arial, Helvetica, sans-serif; background:#f5f7fb; margin:0; padding:24px; color:#111827; }
    .card { max-width:440px; margin:40px auto; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 8px 28px rgba(0,0,0,0.08); }
    .header { background:linear-gradient(135deg,#2563eb 0%,#0f766e 100%); padding:28px; text-align:center; color:#fff; }
    .header h1 { margin:0; font-size:26px; letter-spacing:1px; }
    .header p { margin:6px 0 0; opacity:.9; font-size:14px; }
    .body { padding:28px; }
    label { display:block; font-size:13px; font-weight:600; margin:14px 0 6px; }
    input { width:100%; padding:12px 14px; border:1px solid #d1d5db; border-radius:8px; font-size:15px; }
    input:focus { outline:none; border-color:#2563eb; }
    button { width:100%; margin-top:22px; padding:13px; border:none; border-radius:8px; background:linear-gradient(135deg,#2563eb 0%,#0f766e 100%); color:#fff; font-size:15px; font-weight:700; cursor:pointer; }
    button:disabled { opacity:.6; cursor:not-allowed; }
    .msg { margin-top:16px; padding:12px 14px; border-radius:8px; font-size:14px; display:none; }
    .msg.error { display:block; background:#fef2f2; color:#b91c1c; }
    .msg.success { display:block; background:#ecfdf5; color:#047857; }
    .field-error { display:none; margin-top:6px; font-size:12.5px; color:#b91c1c; }
    .field-error.show { display:block; }
    input.invalid { border-color:#dc2626; }
    .pw-wrap { position:relative; }
    .pw-wrap input { padding-right:64px; }
    .toggle { position:absolute; right:6px; top:50%; transform:translateY(-50%); width:auto; margin:0; padding:6px 10px; background:none; color:#2563eb; font-size:13px; font-weight:600; }
    .meter { height:5px; border-radius:9px; background:#e5e7eb; margin-top:10px; overflow:hidden; }
    .meter > div { height:100%; width:0; border-radius:9px; transition:width .25s, background .25s; }
    .meter-label { font-size:12px; margin-top:4px; color:#6b7280; min-height:16px; }
    .rules { list-style:none; margin:10px 0 0; padding:0; font-size:12.5px; color:#6b7280; }
    .rules li { padding-left:20px; position:relative; margin:3px 0; }
    .rules li::before { content:'\\25CB'; position:absolute; left:0; }
    .rules li.ok { color:#047857; }
    .rules li.ok::before { content:'\\2713'; }
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>EVA</h1>
      <p>Reset your password</p>
    </div>
    <div class="body">
      <form id="form" novalidate>
        <label for="pw">New password</label>
        <div class="pw-wrap">
          <input id="pw" type="password" autocomplete="new-password" placeholder="At least 8 characters" maxlength="64" />
          <button type="button" class="toggle" id="toggle" aria-label="Show or hide password">Show</button>
        </div>
        <div class="field-error" id="pw-err"></div>
        <div class="meter"><div id="meter-bar"></div></div>
        <div class="meter-label" id="meter-label"></div>
        <ul class="rules">
          <li id="r-len">8–64 characters</li>
          <li id="r-letter">At least one letter</li>
          <li id="r-num">At least one number or symbol</li>
        </ul>
        <label for="cpw">Confirm new password</label>
        <input id="cpw" type="password" autocomplete="new-password" placeholder="Re-enter password" maxlength="64" />
        <div class="field-error" id="cpw-err"></div>
        <button id="submit" type="submit">Reset password</button>
      </form>
      <div id="msg" class="msg"></div>
    </div>
  </div>
  <script nonce="${nonce}">
    var TOKEN = ${tokenJson};
    var form = document.getElementById('form');
    var msg = document.getElementById('msg');
    var btn = document.getElementById('submit');
    var pwEl = document.getElementById('pw');
    var cpwEl = document.getElementById('cpw');
    var pwErr = document.getElementById('pw-err');
    var cpwErr = document.getElementById('cpw-err');
    var bar = document.getElementById('meter-bar');
    var barLabel = document.getElementById('meter-label');
    function show(kind, text){ msg.className = kind ? ('msg ' + kind) : 'msg'; msg.textContent = text; }
    function fieldError(el, errEl, text){
      errEl.textContent = text || '';
      errEl.className = text ? 'field-error show' : 'field-error';
      if (text) el.classList.add('invalid'); else el.classList.remove('invalid');
    }
    var COMMON = ['password','password1','password12','password123','passw0rd','12345678','123456789','1234567890','qwerty123','qwertyui','iloveyou','welcome1','welcome123','admin123','abc12345','abcd1234','1q2w3e4r','changeme','11111111','00000000'];
    // Same rules as the server (utils/authValidation.js). The server stays authoritative.
    function checks(p){
      return {
        len: p.length >= 8 && p.length <= 64,
        letter: /[A-Za-z\\u00C0-\\u024F]/.test(p),
        num: /[0-9]|[^A-Za-z0-9\\s]/.test(p)
      };
    }
    function isTrivial(p){
      if (new Set(p.split("")).size <= 2) return true;
      var l = p.toLowerCase(), asc = true, desc = true;
      for (var i = 1; i < l.length; i++) { var d = l.charCodeAt(i) - l.charCodeAt(i-1); if (d !== 1) asc = false; if (d !== -1) desc = false; }
      return l.length >= 6 && (asc || desc);
    }
    function validatePw(p){
      if (!p) return 'Password is required';
      if (p.length < 8) return 'Password must be at least 8 characters';
      if (p.length > 64) return 'Password cannot be longer than 64 characters';
      if (!/[A-Za-z\\u00C0-\\u024F]/.test(p)) return 'Password must include at least one letter';
      if (!/[0-9]|[^A-Za-z0-9\\s]/.test(p)) return 'Password must include at least one number or symbol';
      if (COMMON.indexOf(p.toLowerCase()) !== -1 || isTrivial(p)) return 'This password is too common. Please choose a stronger one';
      return null;
    }
    function strength(p){
      var c = checks(p);
      if (!p) return { pct: 0, color: '#e5e7eb', label: '' };
      if (!(c.len && c.letter && c.num) || validatePw(p)) return { pct: 25, color: '#ef4444', label: 'Weak' };
      var score = 0;
      if (p.length >= 12) score++;
      if (p.length >= 16) score++;
      if (/[a-z]/.test(p) && /[A-Z]/.test(p)) score++;
      if (/[0-9]/.test(p) && /[^A-Za-z0-9]/.test(p)) score++;
      if (score >= 3) return { pct: 100, color: '#16a34a', label: 'Strong' };
      if (score >= 1) return { pct: 66, color: '#f59e0b', label: 'Good' };
      return { pct: 45, color: '#f59e0b', label: 'Fair' };
    }
    function refresh(){
      var p = pwEl.value, c = checks(p);
      document.getElementById('r-len').className = c.len ? 'ok' : '';
      document.getElementById('r-letter').className = c.letter ? 'ok' : '';
      document.getElementById('r-num').className = c.num ? 'ok' : '';
      var s = strength(p);
      bar.style.width = s.pct + '%'; bar.style.background = s.color;
      barLabel.textContent = s.label;
    }
    pwEl.addEventListener('input', function(){ refresh(); fieldError(pwEl, pwErr, ''); });
    cpwEl.addEventListener('input', function(){ fieldError(cpwEl, cpwErr, ''); });
    pwEl.addEventListener('blur', function(){ if (pwEl.value) fieldError(pwEl, pwErr, validatePw(pwEl.value)); });
    cpwEl.addEventListener('blur', function(){ if (cpwEl.value && cpwEl.value !== pwEl.value) fieldError(cpwEl, cpwErr, 'Passwords do not match'); });
    document.getElementById('toggle').addEventListener('click', function(){
      var hidden = pwEl.type === 'password';
      pwEl.type = hidden ? 'text' : 'password';
      cpwEl.type = pwEl.type;
      this.textContent = hidden ? 'Hide' : 'Show';
    });
    if (!TOKEN) { show('error', 'Invalid or missing reset link. Please request a new password reset from the app.'); btn.disabled = true; }
    form.addEventListener('submit', function(e){
      e.preventDefault();
      show('', '');
      var pw = pwEl.value, cpw = cpwEl.value;
      var pwProblem = validatePw(pw);
      var cpwProblem = !cpw ? 'Please confirm your new password' : (pw !== cpw ? 'Passwords do not match' : null);
      fieldError(pwEl, pwErr, pwProblem);
      fieldError(cpwEl, cpwErr, pwProblem ? null : cpwProblem);
      if (pwProblem || cpwProblem) return;
      btn.disabled = true; btn.textContent = 'Resetting…';
      fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: TOKEN, new_password: pw, confirm_password: cpw })
      })
      .then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){ return { ok: r.ok, d: d }; }); })
      .then(function(res){
        if (res.ok) { form.style.display = 'none'; show('success', 'Password reset successful. Open the EVA app and log in with your new password.'); return; }
        var errs = (res.d && res.d.errors) || {};
        if (errs.new_password) fieldError(pwEl, pwErr, errs.new_password);
        if (errs.confirm_password) fieldError(cpwEl, cpwErr, errs.confirm_password);
        if (!errs.new_password && !errs.confirm_password) show('error', (res.d && res.d.message) ? res.d.message : 'Reset failed. The link may have expired.');
        btn.disabled = false; btn.textContent = 'Reset password';
      })
      .catch(function(){ show('error', 'Network error. Please check your connection and try again.'); btn.disabled = false; btn.textContent = 'Reset password'; });
    });
  </script>
</body>
</html>`;

  res.setHeader(
    "Content-Security-Policy",
    `default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'nonce-${nonce}'; connect-src 'self'`,
  );
  res.set("Content-Type", "text/html; charset=utf-8");
  return res.send(html);
};

module.exports = {
  register,
  login,
  googleAuth,
  refresh,
  logout,
  getMe,
  verifyEmail,
  resendVerification,
  forgotPassword,
  resetPassword,
  renderResetPasswordPage,
};

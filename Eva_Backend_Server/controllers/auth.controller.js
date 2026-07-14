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
  validatePassword,
  throwIfErrors,
} = require("../utils/authValidation");

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
    const { name, username, email, password, timezone } = req.body;

    // Validate fields (required + format) with per-field error messages.
    throwIfErrors(validateRegistration({ name, username, email, password }));

    // Check if email already exists
    const existingEmail = await User.findOne({ email: email.toLowerCase() });
    if (existingEmail) {
      throw new ConflictError("Email already registered");
    }

    // Check if username already exists
    const existingUsername = await User.findOne({
      username: username.toLowerCase(),
    });
    if (existingUsername) {
      throw new ConflictError("Username already taken");
    }

    // Generate verification token
    const { token, hashedToken, expires } = generateVerificationToken();

    // Create user
    const userTimezone = normalizeTimezone(timezone || "Asia/Karachi");

    const user = await User.create({
      name,
      username: username.toLowerCase(),
      email: email.toLowerCase(),
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
    const { email, password } = req.body;

    // Validate required fields
    if (!email || !password) {
      throw new BadRequestError("Email and password are required");
    }

    // Find user by email (include password_hash)
    const user = await User.findOne({ email: email.toLowerCase() }).select(
      "+password_hash",
    );

    if (!user) {
      throw new UnauthorizedError("Invalid email or password");
    }

    // Check if user is active
    if (!user.is_active) {
      throw new UnauthorizedError("Account is deactivated");
    }

    // Check if user has a password (local auth)
    if (!user.password_hash) {
      throw new UnauthorizedError("Please login with Google");
    }

    // Verify password
    const isPasswordValid = await user.comparePassword(password);
    if (!isPasswordValid) {
      throw new UnauthorizedError("Invalid email or password");
    }

    // Check if email is verified
    if (!user.is_verified) {
      throw new UnauthorizedError("Please verify your email before logging in");
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
    const { email } = req.body;
    if (!email) {
      throw new BadRequestError("Email is required");
    }

    const normalizedEmail = String(email).toLowerCase().trim();
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
    const { token, new_password, confirm_password } = req.body;

    if (!token || !new_password || !confirm_password) {
      throw new BadRequestError(
        "token, new_password, and confirm_password are required",
      );
    }

    // Enforce the same password policy as registration.
    const passwordError = validatePassword(new_password);
    if (passwordError) {
      throwIfErrors({ password: passwordError });
    }

    if (new_password !== confirm_password) {
      throwIfErrors({
        confirm_password: "New password and confirm password do not match",
      });
    }

    const hashedToken = crypto.createHash("sha256").update(token).digest("hex");
    const user = await User.findOne({
      password_reset_token: hashedToken,
      password_reset_expires: { $gt: new Date() },
      is_active: true,
    }).select("+password_reset_token +password_reset_expires +password_hash +refresh_token_hash");

    if (!user) {
      throw new BadRequestError("Invalid or expired reset token");
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
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>EVA</h1>
      <p>Reset your password</p>
    </div>
    <div class="body">
      <form id="form">
        <label for="pw">New password</label>
        <input id="pw" type="password" autocomplete="new-password" placeholder="At least 6 characters" />
        <label for="cpw">Confirm new password</label>
        <input id="cpw" type="password" autocomplete="new-password" placeholder="Re-enter password" />
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
    function show(kind, text){ msg.className = kind ? ('msg ' + kind) : 'msg'; msg.textContent = text; }
    if (!TOKEN) { show('error', 'Invalid or missing reset link. Please request a new password reset from the app.'); btn.disabled = true; }
    form.addEventListener('submit', function(e){
      e.preventDefault();
      var pw = document.getElementById('pw').value;
      var cpw = document.getElementById('cpw').value;
      if (pw.length < 6) { show('error', 'Password must be at least 6 characters.'); return; }
      if (pw !== cpw) { show('error', 'Passwords do not match.'); return; }
      btn.disabled = true; show('', 'Resetting…');
      fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: TOKEN, new_password: pw, confirm_password: cpw })
      })
      .then(function(r){ return r.json().then(function(d){ return { ok: r.ok, d: d }; }); })
      .then(function(res){
        if (res.ok) { form.style.display = 'none'; show('success', 'Password reset successful. Open the EVA app and log in with your new password.'); }
        else { show('error', (res.d && res.d.message) ? res.d.message : 'Reset failed. The link may have expired.'); btn.disabled = false; }
      })
      .catch(function(){ show('error', 'Network error. Please try again.'); btn.disabled = false; });
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

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

    // Validate required fields
    if (!name || !username || !email || !password) {
      throw new BadRequestError(
        "Name, username, email, and password are required",
      );
    }

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

    if (String(new_password).length < 6) {
      throw new BadRequestError("Password must be at least 6 characters");
    }

    if (new_password !== confirm_password) {
      throw new BadRequestError("new_password and confirm_password do not match");
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
};

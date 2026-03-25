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
const { sendVerificationEmail } = require("../services/email.service");

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
    const user = await User.create({
      name,
      username: username.toLowerCase(),
      email: email.toLowerCase(),
      password_hash: password,
      timezone: timezone || "UTC",
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
        user: user.toPublicProfile(),
        email_sent: emailSent,
      },
    };

    // Include verification token in development mode for testing (backup if email fails)
    if (process.env.NODE_ENV === "development") {
      response.data.verification_token = token;
      response.data.verify_url = `/api/auth/verify-email?token=${token}`;
    }

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
    const accessToken = generateAccessToken(user._id);
    const refreshToken = generateRefreshToken(user._id);

    // Store refresh token hash
    await user.setRefreshToken(refreshToken);

    // Update last login
    await user.updateLastLogin();

    logger.info("User logged in", { userId: user._id, email: user.email });

    res.json({
      status: "success",
      message: "Login successful",
      data: {
        user: user.toPublicProfile(),
        tokens: {
          access_token: accessToken,
          refresh_token: refreshToken,
          token_type: "Bearer",
          expires_in: process.env.JWT_ACCESS_EXPIRES || "15m",
        },
      },
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
          token_type: "Bearer",
          expires_in: process.env.JWT_ACCESS_EXPIRES || "15m",
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
    // Fetch user settings
    const settings = await UserSetting.findOne({ user_id: req.user._id });

    res.json({
      status: "success",
      data: {
        user: req.user.toPublicProfile(),
        settings: settings || null,
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
const verifyEmail = async (req, res, next) => {
  try {
    const { token } = req.query;

    if (!token) {
      throw new BadRequestError("Verification token is required");
    }

    // Hash the token to compare with stored hash
    const hashedToken = crypto.createHash("sha256").update(token).digest("hex");

    // Find user with valid verification token
    const user = await User.findOne({
      email_verification_token: hashedToken,
      email_verification_expires: { $gt: new Date() },
    }).select("+email_verification_token +email_verification_expires");

    if (!user) {
      throw new BadRequestError("Invalid or expired verification token");
    }

    // Mark user as verified
    user.is_verified = true;
    user.email_verification_token = undefined;
    user.email_verification_expires = undefined;
    await user.save();

    logger.info("Email verified", { userId: user._id, email: user.email });

    res.json({
      status: "success",
      message: "Email verified successfully. You can now login.",
    });
  } catch (error) {
    next(error);
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

    const response = {
      status: "success",
      message:
        "If an account exists with this email, a verification link has been sent.",
    };

    // Include verification token in development mode for testing
    if (process.env.NODE_ENV === "development") {
      response.data = {
        verification_token: token,
        verify_url: `/api/auth/verify-email?token=${token}`,
      };
    }

    res.json(response);
  } catch (error) {
    next(error);
  }
};

module.exports = {
  register,
  login,
  refresh,
  logout,
  getMe,
  verifyEmail,
  resendVerification,
};

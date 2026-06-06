/**
 * Authentication Middleware
 * JWT validation and user authentication
 */

const jwt = require("jsonwebtoken");
const { User } = require("../models");
const { UnauthorizedError } = require("./errorHandler");
const logger = require("../config/logger");

/**
 * Protect routes - require valid access token
 */
const protect = async (req, res, next) => {
  try {
    let token;

    // Check for token in Authorization header
    if (
      req.headers.authorization &&
      req.headers.authorization.startsWith("Bearer")
    ) {
      token = req.headers.authorization.split(" ")[1];
    }

    if (!token) {
      throw new UnauthorizedError("Access token required");
    }

    // Verify token
    let decoded;
    try {
      decoded = jwt.verify(token, process.env.JWT_ACCESS_SECRET);
    } catch (err) {
      if (err.name === "TokenExpiredError") {
        throw new UnauthorizedError("Access token expired");
      }
      throw new UnauthorizedError("Invalid access token");
    }

    // Check if user still exists and is active
    const user = await User.findById(decoded.userId);

    if (!user) {
      throw new UnauthorizedError("User no longer exists");
    }

    if (!user.is_active) {
      throw new UnauthorizedError("User account is deactivated");
    }

    // Attach user to request
    req.user = user;
    req.userId = user._id;

    next();
  } catch (error) {
    next(error);
  }
};

/**
 * Optional auth - attach user if token present, but don't require it
 */
const optionalAuth = async (req, res, next) => {
  try {
    let token;

    if (
      req.headers.authorization &&
      req.headers.authorization.startsWith("Bearer")
    ) {
      token = req.headers.authorization.split(" ")[1];
    }

    if (token) {
      try {
        const decoded = jwt.verify(token, process.env.JWT_ACCESS_SECRET);
        const user = await User.findById(decoded.userId);

        if (user && user.is_active) {
          req.user = user;
          req.userId = user._id;
        }
      } catch (err) {
        // Token invalid or expired - continue without user
        logger.debug("Optional auth: invalid token, continuing without user");
      }
    }

    next();
  } catch (error) {
    next(error);
  }
};

/**
 * Require email verification
 */
const requireVerified = (req, res, next) => {
  if (!req.user.is_verified) {
    return next(new UnauthorizedError("Email verification required"));
  }
  next();
};

module.exports = {
  protect,
  optionalAuth,
  requireVerified,
};

/**
 * Custom Error Classes and Error Handler Middleware
 */

const logger = require("../config/logger");

/**
 * Custom API Error class
 */
class ApiError extends Error {
  constructor(statusCode, message, isOperational = true, stack = "") {
    super(message);
    this.statusCode = statusCode;
    this.isOperational = isOperational;
    this.status = `${statusCode}`.startsWith("4") ? "fail" : "error";

    if (stack) {
      this.stack = stack;
    } else {
      Error.captureStackTrace(this, this.constructor);
    }
  }
}

/**
 * Not Found Error (404)
 */
class NotFoundError extends ApiError {
  constructor(message = "Resource not found") {
    super(404, message);
  }
}

/**
 * Bad Request Error (400)
 */
class BadRequestError extends ApiError {
  constructor(message = "Bad request") {
    super(400, message);
  }
}

/**
 * Unauthorized Error (401)
 */
class UnauthorizedError extends ApiError {
  constructor(message = "Unauthorized") {
    super(401, message);
  }
}

/**
 * Forbidden Error (403)
 */
class ForbiddenError extends ApiError {
  constructor(message = "Forbidden") {
    super(403, message);
  }
}

/**
 * Conflict Error (409)
 */
class ConflictError extends ApiError {
  constructor(message = "Conflict") {
    super(409, message);
  }
}

/**
 * Validation Error (422)
 */
class ValidationError extends ApiError {
  constructor(message = "Validation failed", errors = []) {
    super(422, message);
    this.errors = errors;
  }
}

/**
 * Internal Server Error (500)
 */
class InternalError extends ApiError {
  constructor(message = "Internal server error") {
    super(500, message, false);
  }
}

/**
 * Convert non-API errors to ApiError
 */
const normalizeError = (err) => {
  // Mongoose validation error
  if (err.name === "ValidationError") {
    const errors = Object.values(err.errors).map((e) => e.message);
    return new ValidationError("Validation failed", errors);
  }

  // Mongoose cast error (invalid ObjectId)
  if (err.name === "CastError") {
    return new BadRequestError(`Invalid ${err.path}: ${err.value}`);
  }

  // Mongoose duplicate key error
  if (err.code === 11000) {
    const field = Object.keys(err.keyValue)[0];
    return new ConflictError(`${field} already exists`);
  }

  // JWT errors
  if (err.name === "JsonWebTokenError") {
    return new UnauthorizedError("Invalid token");
  }

  if (err.name === "TokenExpiredError") {
    return new UnauthorizedError("Token expired");
  }

  // Return original if already ApiError
  if (err instanceof ApiError) {
    return err;
  }

  // Default to internal error
  return new InternalError(err.message);
};

/**
 * 404 Not Found handler for undefined routes
 */
const notFoundHandler = (req, res, next) => {
  next(new NotFoundError(`Route ${req.originalUrl} not found`));
};

/**
 * Global error handler middleware
 */
const errorHandler = (err, req, res, next) => {
  const error = normalizeError(err);

  // Log error
  if (error.statusCode >= 500) {
    logger.error("Server error", {
      message: error.message,
      stack: error.stack,
      url: req.originalUrl,
      method: req.method,
      ip: req.ip,
    });
  } else {
    logger.warn("Client error", {
      message: error.message,
      statusCode: error.statusCode,
      url: req.originalUrl,
      method: req.method,
    });
  }

  // Build response
  const response = {
    status: error.status,
    message: error.message,
  };

  // Add validation errors if present
  if (error.errors) {
    response.errors = error.errors;
  }

  // Add stack trace in development
  if (process.env.NODE_ENV === "development") {
    response.stack = error.stack;
  }

  res.status(error.statusCode).json(response);
};

module.exports = {
  ApiError,
  NotFoundError,
  BadRequestError,
  UnauthorizedError,
  ForbiddenError,
  ConflictError,
  ValidationError,
  InternalError,
  notFoundHandler,
  errorHandler,
};

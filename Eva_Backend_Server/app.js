/**
 * EVA Backend Server - Express Entry Point
 */

// Load environment variables first (always from this folder)
const path = require("path");
require("dotenv").config({ path: path.join(__dirname, ".env") });

const express = require("express");
const cors = require("cors");
const helmet = require("helmet");
const morgan = require("morgan");
const rateLimit = require("express-rate-limit");

// Import configurations
const logger = require("./config/logger");
const { connectDB } = require("./config/db");
const { startReminderJob, stopReminderJob } = require("./jobs/reminder.job");
const {
  startLearningAutoCompleteJob,
  stopLearningAutoCompleteJob,
} = require("./jobs/learning_auto_complete.job");

// Import middleware
const { notFoundHandler, errorHandler } = require("./middleware/errorHandler");
const { getBackendPort, buildBackendPublicUrl } = require("./utils/publicUrl");

// Import routes
const routes = require("./routes");

// Create Express app
const app = express();

// ===========================================
// Security Middleware
// ===========================================

// Set security HTTP headers
app.use(helmet());

// Enable CORS
app.use(
  cors({
    origin: true, // Reflects the request origin (no wildcard)
    credentials: true,
    methods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allowedHeaders: ["Content-Type", "Authorization"],
  }),
);

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: {
    status: "fail",
    message: "Too many requests, please try again later",
  },
  standardHeaders: true,
  legacyHeaders: false,
});
app.use("/api", limiter);

// ===========================================
// Body Parsing Middleware
// ===========================================

app.use(express.json({ limit: "10mb" }));
app.use(express.urlencoded({ extended: true, limit: "10mb" }));

// ===========================================
// Logging Middleware
// ===========================================

// HTTP request logging with Morgan -> Winston
const morganFormat = process.env.NODE_ENV === "production" ? "combined" : "dev";
app.use(morgan(morganFormat, { stream: logger.stream }));

// ===========================================
// Request ID Middleware
// ===========================================

app.use((req, res, next) => {
  req.requestId = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  res.setHeader("X-Request-ID", req.requestId);
  next();
});

// ===========================================
// Routes
// ===========================================

app.use(routes);

// ===========================================
// Error Handling
// ===========================================

// 404 handler for undefined routes
app.use(notFoundHandler);

// Global error handler
app.use(errorHandler);

// ===========================================
// Server Startup
// ===========================================

const PORT = getBackendPort();
let reminderJobHandle = null;
let learningAutoCompleteJobHandle = null;

const startServer = async () => {
  logger.info("=".repeat(50));
  logger.info("EVA Backend Server Starting...");
  logger.info("=".repeat(50));

  // Connect to MongoDB
  const dbConnected = await connectDB();

  if (!dbConnected) {
    logger.error("Failed to connect to MongoDB. Exiting...");
    process.exit(1);
  }

  // Start phase 12 reminder scheduler.
  reminderJobHandle = startReminderJob();

  // Start phase 6 learning auto-complete scheduler.
  learningAutoCompleteJobHandle = startLearningAutoCompleteJob();

  // Start HTTP server
  app.listen(PORT, () => {
    logger.info("=".repeat(50));
    logger.info(`Server running on port ${PORT}`);
    logger.info(`Environment: ${process.env.NODE_ENV || "development"}`);
    logger.info(`Health check: http://localhost:${PORT}/health`);
    logger.info(`Email links base: ${buildBackendPublicUrl()}`);
    logger.info("=".repeat(50));
  });
};

// Handle uncaught exceptions
process.on("uncaughtException", (err) => {
  logger.error("Uncaught Exception", { error: err.message, stack: err.stack });
  process.exit(1);
});

// Handle unhandled promise rejections
process.on("unhandledRejection", (reason, promise) => {
  logger.error("Unhandled Rejection", { reason: reason.message || reason });
});

// Handle SIGTERM
process.on("SIGTERM", () => {
  logger.info("SIGTERM received. Shutting down gracefully...");
  if (reminderJobHandle) {
    stopReminderJob();
  }
  if (learningAutoCompleteJobHandle) {
    stopLearningAutoCompleteJob();
  }
  process.exit(0);
});

// Start the server only when app.js is run directly.
if (require.main === module) {
  startServer();
}

module.exports = app;
module.exports.startServer = startServer;

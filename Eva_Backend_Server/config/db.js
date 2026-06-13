/**
 * MongoDB Connection Configuration
 * Uses Mongoose for MongoDB connection with event handling
 */

const mongoose = require("mongoose");
const logger = require("./logger");

// Connection state tracking
let isConnected = false;

/**
 * Resolve MongoDB database name from URI or env.
 * Mongoose defaults to "test" when the URI has no database segment — match AI server instead.
 */
const getDatabaseName = (uri) => {
  const explicit = (process.env.MONGODB_DB_NAME || "").trim();
  if (explicit) {
    return explicit;
  }

  if (!uri) {
    return "EVA";
  }

  const tail = uri.split("/").pop()?.split("?")[0]?.trim() || "";
  if (tail && !tail.includes("@") && !tail.includes(".")) {
    return tail;
  }

  return "EVA";
};

/**
 * Connect to MongoDB
 * @returns {Promise<boolean>} Connection success status
 */
const connectDB = async () => {
  if (isConnected) {
    logger.info("MongoDB already connected");
    return true;
  }

  try {
    const dbName = getDatabaseName(process.env.MONGODB_URI);
    const conn = await mongoose.connect(process.env.MONGODB_URI, {
      dbName,
    });

    isConnected = true;
    logger.info(`MongoDB connected: ${conn.connection.host} (database: ${conn.connection.name})`);
    return true;
  } catch (error) {
    logger.error("MongoDB connection failed", { error: error.message });
    return false;
  }
};

/**
 * Disconnect from MongoDB
 */
const disconnectDB = async () => {
  if (!isConnected) {
    return;
  }

  try {
    await mongoose.disconnect();
    isConnected = false;
    logger.info("MongoDB disconnected");
  } catch (error) {
    logger.error("MongoDB disconnect error", { error: error.message });
  }
};

/**
 * Check MongoDB connection health
 * @returns {boolean} Connection health status
 */
const healthCheck = () => {
  return mongoose.connection.readyState === 1;
};

// Mongoose connection event handlers
mongoose.connection.on("connected", () => {
  logger.info("Mongoose connected to MongoDB");
});

mongoose.connection.on("error", (err) => {
  logger.error("Mongoose connection error", { error: err.message });
});

mongoose.connection.on("disconnected", () => {
  isConnected = false;
  logger.warn("Mongoose disconnected from MongoDB");
});

// Handle process termination
process.on("SIGINT", async () => {
  await disconnectDB();
  process.exit(0);
});

module.exports = {
  connectDB,
  disconnectDB,
  healthCheck,
};

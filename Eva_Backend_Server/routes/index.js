/**
 * Routes Index
 * Centralized route registration
 */

const express = require("express");
const router = express.Router();

// Import route modules
const healthRoutes = require("./health.routes");
const authRoutes = require("./auth.routes");
const chatRoutes = require("./chat.routes");
const taskRoutes = require("./tasks.routes");
const integrationRoutes = require("./integrations.routes");
const settingsRoutes = require("./settings.routes");
const analyticsRoutes = require("./analytics.routes");
const friendsRoutes = require("./friends.routes");
const learningRoutes = require("./learning.routes");
const profileRoutes = require("./profile.routes");

// Register routes
router.use("/", healthRoutes);
router.use("/api/auth", authRoutes);
router.use("/api/chat", chatRoutes);
router.use("/api/tasks", taskRoutes);
router.use("/api/integrations", integrationRoutes);
router.use("/api/settings", settingsRoutes);
router.use("/api/analytics", analyticsRoutes);
router.use("/api/friends", friendsRoutes);
router.use("/api/learning", learningRoutes);
router.use("/api/profile", profileRoutes);

// Future routes will be added here:
// router.use('/api/notifications', notificationRoutes);
// router.use('/api/learning', learningRoutes);

module.exports = router;

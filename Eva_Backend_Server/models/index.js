/**
 * Models Index
 * Export all Mongoose models
 */

const User = require("./User");
const UserSetting = require("./UserSetting");
const ChatSession = require("./ChatSession");
const ConversationHistory = require("./ConversationHistory");
const Notification = require("./Notification");
const Task = require("./Task");
const ActivityLog = require("./ActivityLog");
const Integration = require("./Integration");
const Friend = require("./Friend");
const LearningGoal = require("./LearningGoal");
const RoadmapTopic = require("./RoadmapTopic");

module.exports = {
  User,
  UserSetting,
  ChatSession,
  ConversationHistory,
  Notification,
  Task,
  ActivityLog,
  Integration,
  Friend,
  LearningGoal,
  RoadmapTopic,
};

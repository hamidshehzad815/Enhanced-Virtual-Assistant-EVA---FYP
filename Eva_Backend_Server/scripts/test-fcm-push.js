/**
 * Send a test push to the most recently updated user with a push token.
 *
 * Usage (from Eva_Backend_Server):
 *   node scripts/test-fcm-push.js
 *
 * Requires MONGODB_URI and FIREBASE_CREDENTIALS in .env.
 * Restart the backend after changing the service account file.
 */

const path = require("path");
require("dotenv").config({ path: path.join(__dirname, "..", ".env") });

const mongoose = require("mongoose");
const { User } = require("../models");
const { dispatch_push } = require("../services/notification.service");

const main = async () => {
  if (!process.env.MONGODB_URI) {
    console.error("MONGODB_URI is not set in .env");
    process.exit(1);
  }

  await mongoose.connect(process.env.MONGODB_URI);

  const user = await User.findOne({ "push_tokens.0": { $exists: true } })
    .sort({ updated_at: -1 })
    .select("email push_tokens")
    .lean();

  if (!user) {
    console.error("No user with push_tokens found. Log in on the phone first.");
    process.exit(1);
  }

  const fakeNotification = {
    _id: new mongoose.Types.ObjectId(),
    title: "EVA test push",
    message: "If you see this, FCM delivery is working.",
    type: "task_reminder",
    reference_type: "task",
    reference_id: null,
  };

  console.log(`Sending test push to: ${user.email}`);
  console.log(`Registered tokens: ${user.push_tokens.length}`);

  const result = await dispatch_push(user._id, fakeNotification, user, {
    test: "true",
  });

  console.log("\nResult:", JSON.stringify(result, null, 2));
  console.log(
    "\nCheck backend logs for 'Push token rejected by FCM' (error_code) if dispatched is false.",
  );
  console.log("On phone: app in background, notification permission enabled.");

  await mongoose.disconnect();
};

main().catch((error) => {
  console.error("Failed:", error.message);
  process.exit(1);
});

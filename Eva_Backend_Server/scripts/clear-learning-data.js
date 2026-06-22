/**
 * Delete all documents from tasks, roadmap_topics, and learning_goals.
 *
 * Usage (from Eva_Backend_Server):
 *   node scripts/clear-learning-data.js --confirm
 *
 * Optional:
 *   node scripts/clear-learning-data.js --confirm --uri mongodb://localhost:27017/EVA
 *
 * Requires --confirm (avoids accidental wipes).
 */

const path = require("path");
require("dotenv").config({ path: path.join(__dirname, "..", ".env") });

const mongoose = require("mongoose");

const COLLECTIONS = ["tasks", "roadmap_topics", "learning_goals"];

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

const parseArgs = () => {
  const args = process.argv.slice(2);
  const confirm = args.includes("--confirm");
  const uriIndex = args.indexOf("--uri");
  const uri =
    uriIndex >= 0 && args[uriIndex + 1]
      ? args[uriIndex + 1]
      : process.env.MONGODB_URI || "mongodb://localhost:27017/EVA";
  return { confirm, uri };
};

const main = async () => {
  const { confirm, uri } = parseArgs();

  if (!confirm) {
    console.error("Refusing to run without --confirm.");
    console.error("Example: node scripts/clear-learning-data.js --confirm");
    process.exit(1);
  }

  const dbName = getDatabaseName(uri);
  console.log(`Connecting to ${uri.replace(/\/\/([^@/]+@)?/, "//***@")} (db: ${dbName})`);

  await mongoose.connect(uri, { dbName });
  const db = mongoose.connection.db;

  const summary = [];

  for (const name of COLLECTIONS) {
    const before = await db.collection(name).countDocuments();
    const result = await db.collection(name).deleteMany({});
    summary.push({ collection: name, before, deleted: result.deletedCount });
  }

  console.log("\nCleared collections:");
  for (const row of summary) {
    console.log(`  ${row.collection}: ${row.deleted} deleted (was ${row.before})`);
  }

  await mongoose.disconnect();
  console.log("\nDone.");
};

main().catch((error) => {
  console.error("Failed:", error.message);
  process.exit(1);
});

/**
 * Delete all documents from every collection in the EVA database,
 * except `roadmap_resources` (curated learning resources are preserved).
 *
 * Usage (from Eva_Backend_Server):
 *   node scripts/clear-database-except-roadmap-resources.js --confirm
 *
 * Preview only (no deletes):
 *   node scripts/clear-database-except-roadmap-resources.js --dry-run
 *
 * Optional custom URI:
 *   node scripts/clear-database-except-roadmap-resources.js --confirm --uri mongodb://localhost:27017/EVA
 *
 * Requires --confirm to perform deletes (avoids accidental wipes).
 */

const path = require("path");
require("dotenv").config({ path: path.join(__dirname, "..", ".env") });

const mongoose = require("mongoose");

const PRESERVED_COLLECTION = "roadmap_resources";

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

const maskUri = (uri) => uri.replace(/\/\/([^@/]+@)?/, "//***@");

const parseArgs = () => {
  const args = process.argv.slice(2);
  const confirm = args.includes("--confirm");
  const dryRun = args.includes("--dry-run");
  const uriIndex = args.indexOf("--uri");
  const uri =
    uriIndex >= 0 && args[uriIndex + 1]
      ? args[uriIndex + 1]
      : process.env.MONGODB_URI || "mongodb://localhost:27017/EVA";

  return { confirm, dryRun, uri };
};

const listTargetCollections = async (db) => {
  const entries = await db.listCollections({}, { nameOnly: true }).toArray();
  return entries
    .map((entry) => entry.name)
    .filter((name) => name !== PRESERVED_COLLECTION)
    .sort();
};

const main = async () => {
  const { confirm, dryRun, uri } = parseArgs();

  if (!confirm && !dryRun) {
    console.error("Refusing to run without --confirm or --dry-run.");
    console.error(
      "Example: node scripts/clear-database-except-roadmap-resources.js --confirm",
    );
    process.exit(1);
  }

  const dbName = getDatabaseName(uri);
  console.log(`Connecting to ${maskUri(uri)} (db: ${dbName})`);

  await mongoose.connect(uri, { dbName });
  const db = mongoose.connection.db;

  const preservedCount = await db
    .collection(PRESERVED_COLLECTION)
    .countDocuments()
    .catch(() => 0);

  const collections = await listTargetCollections(db);

  if (!collections.length) {
    console.log("\nNo collections to clear (only preserved collection may exist).");
    console.log(
      `Preserved: ${PRESERVED_COLLECTION} (${preservedCount} document(s))`,
    );
    await mongoose.disconnect();
    return;
  }

  console.log(`\nPreserved: ${PRESERVED_COLLECTION} (${preservedCount} document(s))`);
  console.log(`${dryRun ? "Would clear" : "Clearing"} ${collections.length} collection(s):\n`);

  const summary = [];

  for (const name of collections) {
    const before = await db.collection(name).countDocuments();
    summary.push({ collection: name, before, deleted: 0 });

    if (dryRun) {
      continue;
    }

    const result = await db.collection(name).deleteMany({});
    summary[summary.length - 1].deleted = result.deletedCount;
  }

  for (const row of summary) {
    if (dryRun) {
      console.log(`  ${row.collection}: ${row.before} document(s)`);
    } else {
      console.log(
        `  ${row.collection}: ${row.deleted} deleted (was ${row.before})`,
      );
    }
  }

  await mongoose.disconnect();

  if (dryRun) {
    console.log("\nDry run complete. Re-run with --confirm to delete.");
  } else {
    console.log("\nDone.");
  }
};

main().catch((error) => {
  console.error("Failed:", error.message);
  process.exit(1);
});

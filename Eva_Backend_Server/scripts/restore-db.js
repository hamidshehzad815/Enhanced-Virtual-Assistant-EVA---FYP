/**
 * Restore collections from a backup folder created by scripts/backup-db.js.
 * For each <collection>.json file found, replaces that collection's contents
 * entirely (deleteMany({}) then insertMany from the file).
 *
 * Usage (from Eva_Backend_Server):
 *   node scripts/restore-db.js --in ./backups/2026-07-19T12-00-00-000Z --confirm
 *
 * Preview only (no writes):
 *   node scripts/restore-db.js --in ./backups/2026-07-19T12-00-00-000Z --dry-run
 */

const fs = require("fs");
const path = require("path");
require("dotenv").config({ path: path.join(__dirname, "..", ".env") });

const mongoose = require("mongoose");
const { EJSON } = require("bson");

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
  const inIndex = args.indexOf("--in");
  const inDir = inIndex >= 0 && args[inIndex + 1] ? args[inIndex + 1] : null;

  return { confirm, dryRun, uri, inDir };
};

const main = async () => {
  const { confirm, dryRun, uri, inDir } = parseArgs();

  if (!inDir) {
    console.error("Missing --in <backup-folder>.");
    process.exit(1);
  }
  if (!fs.existsSync(inDir)) {
    console.error(`Backup folder not found: ${inDir}`);
    process.exit(1);
  }
  if (!confirm && !dryRun) {
    console.error("Refusing to run without --confirm or --dry-run.");
    console.error(
      `Example: node scripts/restore-db.js --in "${inDir}" --confirm`,
    );
    process.exit(1);
  }

  const files = fs.readdirSync(inDir).filter((f) => f.endsWith(".json"));
  if (!files.length) {
    console.error(`No .json files found in ${inDir}`);
    process.exit(1);
  }

  const dbName = getDatabaseName(uri);
  console.log(`Connecting to ${maskUri(uri)} (db: ${dbName})`);
  await mongoose.connect(uri, { dbName });
  const db = mongoose.connection.db;

  console.log(`\n${dryRun ? "Would restore" : "Restoring"} ${files.length} collection(s) from ${inDir}\n`);

  for (const file of files) {
    const name = file.replace(/\.json$/, "");
    const docs = EJSON.parse(fs.readFileSync(path.join(inDir, file), "utf8"));

    if (dryRun) {
      console.log(`  ${name}: ${docs.length} document(s) would replace current contents`);
      continue;
    }

    await db.collection(name).deleteMany({});
    if (docs.length) {
      await db.collection(name).insertMany(docs);
    }
    console.log(`  ${name}: restored ${docs.length} document(s)`);
  }

  await mongoose.disconnect();
  console.log(dryRun ? "\nDry run complete. Re-run with --confirm to restore." : "\nDone.");
};

main().catch((error) => {
  console.error("Failed:", error.message);
  process.exit(1);
});

/**
 * Dump every collection in the EVA database to local JSON files (one file per
 * collection, using MongoDB Extended JSON so ObjectId/Date/etc. round-trip
 * correctly through restore-db.js).
 *
 * Usage (from Eva_Backend_Server):
 *   node scripts/backup-db.js
 *
 * Optional custom URI / output dir:
 *   node scripts/backup-db.js --uri mongodb://localhost:27017/EVA --out ./my-backup
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
  const uriIndex = args.indexOf("--uri");
  const uri =
    uriIndex >= 0 && args[uriIndex + 1]
      ? args[uriIndex + 1]
      : process.env.MONGODB_URI || "mongodb://localhost:27017/EVA";

  const outIndex = args.indexOf("--out");
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const out =
    outIndex >= 0 && args[outIndex + 1]
      ? args[outIndex + 1]
      : path.join(__dirname, "..", "backups", timestamp);

  return { uri, out };
};

const main = async () => {
  const { uri, out } = parseArgs();
  const dbName = getDatabaseName(uri);

  console.log(`Connecting to ${maskUri(uri)} (db: ${dbName})`);
  await mongoose.connect(uri, { dbName });
  const db = mongoose.connection.db;

  fs.mkdirSync(out, { recursive: true });

  const entries = await db.listCollections({}, { nameOnly: true }).toArray();
  const names = entries.map((entry) => entry.name).sort();

  console.log(`\nBacking up ${names.length} collection(s) to ${out}\n`);

  let totalDocs = 0;
  for (const name of names) {
    const docs = await db.collection(name).find({}).toArray();
    const filePath = path.join(out, `${name}.json`);
    fs.writeFileSync(filePath, EJSON.stringify(docs, undefined, 2));
    console.log(`  ${name}: ${docs.length} document(s)`);
    totalDocs += docs.length;
  }

  await mongoose.disconnect();
  console.log(`\nDone. ${totalDocs} document(s) backed up to ${out}`);
  console.log(`Restore with: node scripts/restore-db.js --in "${out}" --confirm`);
};

main().catch((error) => {
  console.error("Failed:", error.message);
  process.exit(1);
});

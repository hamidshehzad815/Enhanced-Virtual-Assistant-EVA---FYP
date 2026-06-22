/**
 * Seed roadmap_resources from roadmaps.json (idempotent).
 *
 * Usage (from Eva_Backend_Server):
 *   node scripts/seed-roadmaps.js
 *   node scripts/seed-roadmaps.js --json ../Eva_AI_Server/data/roadmaps.json
 *
 * Path resolution (same as AI server):
 *   1. --json flag
 *   2. ROADMAPS_JSON_PATH env
 *   3. <repo>/Roadmaps/roadmaps.json
 *   4. Eva_AI_Server/data/roadmaps.json
 */

const fs = require("fs");
const path = require("path");
require("dotenv").config({ path: path.join(__dirname, "..", ".env") });

const mongoose = require("mongoose");
const { connectDB, disconnectDB } = require("../config/db");

const WORKSPACE_ROOT = path.resolve(__dirname, "..", "..");
const DEFAULT_JSON = path.join(
  WORKSPACE_ROOT,
  "Eva_AI_Server",
  "data",
  "roadmaps.json",
);

const resolveRoadmapsJsonPath = (cliPath) => {
  if (cliPath) {
    const p = path.isAbsolute(cliPath)
      ? cliPath
      : path.resolve(process.cwd(), cliPath);
    if (!fs.existsSync(p)) {
      throw new Error(`File not found: ${p}`);
    }
    return p;
  }

  const fromEnv = (process.env.ROADMAPS_JSON_PATH || "").trim();
  if (fromEnv) {
    const p = path.isAbsolute(fromEnv)
      ? fromEnv
      : path.resolve(WORKSPACE_ROOT, fromEnv);
    if (!fs.existsSync(p)) {
      throw new Error(`ROADMAPS_JSON_PATH not found: ${p}`);
    }
    return p;
  }

  const preferred = path.join(WORKSPACE_ROOT, "Roadmaps", "roadmaps.json");
  if (fs.existsSync(preferred)) {
    return preferred;
  }

  if (!fs.existsSync(DEFAULT_JSON)) {
    throw new Error(
      `roadmaps.json not found. Tried:\n  ${preferred}\n  ${DEFAULT_JSON}`,
    );
  }
  return DEFAULT_JSON;
};

const parseArgs = () => {
  const jsonFlagIndex = process.argv.indexOf("--json");
  if (jsonFlagIndex === -1) {
    return { jsonPath: null };
  }
  const jsonPath = process.argv[jsonFlagIndex + 1];
  if (!jsonPath) {
    throw new Error("Usage: node scripts/seed-roadmaps.js [--json <path>]");
  }
  return { jsonPath };
};

const loadRoadmapsJson = (filePath) => {
  const raw = fs.readFileSync(filePath, "utf8");
  const data = JSON.parse(raw);
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new Error("roadmaps.json must be a JSON object");
  }
  return data;
};

const seedFromRoadmapsJson = async (data) => {
  const collection = mongoose.connection.collection("roadmap_resources");
  const topicNames = Array.isArray(data.topics) ? data.topics : [];
  const now = new Date();

  let inserted = 0;
  let skipped = 0;
  let expected = 0;

  for (const language of topicNames) {
    const block = data[language];
    if (!block || typeof block !== "object") {
      continue;
    }

    const levelKeys = block.topics;
    if (!Array.isArray(levelKeys)) {
      continue;
    }

    for (const level of levelKeys) {
      if (typeof level !== "string") {
        continue;
      }

      const levelData = block[level];
      if (!levelData || typeof levelData !== "object") {
        continue;
      }

      const titles = levelData.topics;
      if (!Array.isArray(titles)) {
        continue;
      }

      let levelCalendarDays = null;
      if (levelData.days != null) {
        const parsed = Number(levelData.days);
        levelCalendarDays = Number.isFinite(parsed) ? parsed : null;
      }

      for (let idx = 0; idx < titles.length; idx += 1) {
        expected += 1;
        const order = idx + 1;
        const title = String(titles[idx] || "").trim();

        const exists = await collection.findOne(
          { language, level, order },
          { projection: { _id: 1 } },
        );

        if (exists) {
          skipped += 1;
          continue;
        }

        await collection.insertOne({
          language,
          level,
          order,
          title,
          level_calendar_days: levelCalendarDays,
          resources: [],
          fetched_at: null,
          created_at: now,
          updated_at: now,
        });
        inserted += 1;
      }
    }
  }

  return { inserted, skipped, expected };
};

const main = async () => {
  const { jsonPath } = parseArgs();
  const resolvedPath = resolveRoadmapsJsonPath(jsonPath);
  const data = loadRoadmapsJson(resolvedPath);

  console.log(`Using roadmaps file: ${resolvedPath}`);

  const connected = await connectDB();
  if (!connected) {
    throw new Error("MongoDB connection failed");
  }

  try {
    const { inserted, skipped, expected } = await seedFromRoadmapsJson(data);
    console.log("Seeding roadmap_resources...");
    console.log(`  Expected session rows (from JSON): ${expected}`);
    console.log(`  Inserted: ${inserted}`);
    console.log(`  Skipped (already present): ${skipped}`);
    console.log("Done.");
  } finally {
    await disconnectDB();
  }
};

if (require.main === module) {
  main().catch((error) => {
    console.error("Seed failed:", error.message);
    process.exit(1);
  });
}

module.exports = {
  resolveRoadmapsJsonPath,
  loadRoadmapsJson,
  seedFromRoadmapsJson,
};

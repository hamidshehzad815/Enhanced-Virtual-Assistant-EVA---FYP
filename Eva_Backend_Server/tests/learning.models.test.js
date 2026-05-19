/**
 * Learning models — schema shape (no MongoDB connection required).
 */

process.env.NODE_ENV = "test";

const LearningGoal = require("../models/LearningGoal");
const RoadmapTopic = require("../models/RoadmapTopic");

describe("Learning models (Phase 1 schema)", () => {
  test("LearningGoal exposes roadmap and tracking fields", () => {
    const paths = LearningGoal.schema.paths;
    expect(paths.roadmap_key).toBeDefined();
    expect(paths.started_at).toBeDefined();
    expect(paths.completed_at).toBeDefined();
    expect(paths.time_taken_days).toBeDefined();
    expect(paths.duration_days).toBeDefined();
    expect(paths.subject).toBeDefined();
  });

  test("RoadmapTopic exposes goal linkage and resources", () => {
    const paths = RoadmapTopic.schema.paths;
    expect(paths.goal_id).toBeDefined();
    expect(paths.task_id).toBeDefined();
    expect(paths.resources).toBeDefined();
    expect(paths.order).toBeDefined();
  });
});

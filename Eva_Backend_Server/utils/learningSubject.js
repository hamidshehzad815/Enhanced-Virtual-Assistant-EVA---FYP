/**
 * Subject / language normalization for learning goals (DB stores lowercase subject).
 */

const TOPIC_ALIAS_MAP = {
  py: "python",
  python3: "python",
  js: "javascript",
  ts: "typescript",
  golang: "go",
  "go lang": "go",
  cpp: "c++",
  "c plus plus": "c++",
  "c sharp": "c#",
  csharp: "c#",
  mongo: "mongodb",
  "mongo db": "mongodb",
  postgre: "postgresql",
  mssql: "microsoft sql server",
  "sql server": "microsoft sql server",
  "my sql": "mysql",
};

const DISPLAY_BY_SUBJECT = {
  python: "Python",
  javascript: "JavaScript",
  typescript: "TypeScript",
  java: "Java",
  "c#": "C#",
  "c++": "C++",
  go: "Go",
  rust: "Rust",
  php: "PHP",
  kotlin: "Kotlin",
  swift: "Swift",
  ruby: "Ruby",
  dart: "Dart",
  c: "C",
  oracle: "Oracle",
  mysql: "MySQL",
  "microsoft sql server": "Microsoft SQL Server",
  postgresql: "PostgreSQL",
  mongodb: "MongoDB",
  sql: "SQL",
};

const normalizeSubjectFilter = (input) => {
  const trimmed = String(input || "").trim();
  if (!trimmed) {
    return null;
  }

  const lower = trimmed.toLowerCase();
  if (DISPLAY_BY_SUBJECT[lower]) {
    return lower;
  }

  const alias = TOPIC_ALIAS_MAP[lower];
  if (alias) {
    return alias;
  }

  return lower;
};

const subjectToDisplay = (subject) => {
  const key = String(subject || "").trim().toLowerCase();
  if (!key) {
    return "";
  }
  if (DISPLAY_BY_SUBJECT[key]) {
    return DISPLAY_BY_SUBJECT[key];
  }
  return key.replace(/\b\w/g, (ch) => ch.toUpperCase());
};

const formatTrackLabel = (roadmapKey) => {
  const key = String(roadmapKey || "").trim();
  if (!key || key === "general") {
    return "General";
  }
  return key.replace(/_/g, " ").replace(/\b\w/g, (ch) => ch.toUpperCase());
};

module.exports = {
  normalizeSubjectFilter,
  subjectToDisplay,
  formatTrackLabel,
};

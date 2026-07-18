/**
 * Collaborator detail population.
 *
 * Task and LearningGoal documents store collaborators as a lean array of
 * `{ user_id, status }`. The API must expose *who* each collaborator is —
 * their public profile — without leaking private fields (email, tokens, …).
 *
 * These helpers batch-load the referenced users once and shape them into the
 * public collaborator object the frontend consumes:
 *
 *   { user: { _id, name, username, profile_picture }, status }
 */

const { User } = require("../models");

/** Only public profile fields — never email, password, tokens, etc. */
const COLLABORATOR_PUBLIC_FIELDS = "name username profile_picture";

const VALID_STATUSES = new Set(["pending", "accepted", "rejected"]);

const normalizeStatus = (status) => {
  const value = String(status || "pending").trim().toLowerCase();
  return VALID_STATUSES.has(value) ? value : "pending";
};

/**
 * Collect the unique collaborator user ids across many docs, each carrying a
 * `collaborators: [{ user_id, status }]` array.
 * @param {Array<{collaborators?: Array}>} docs
 * @returns {string[]} unique user id strings
 */
const collectCollaboratorUserIds = (docs) => {
  const ids = new Set();
  for (const doc of docs || []) {
    const rows = Array.isArray(doc?.collaborators) ? doc.collaborators : [];
    for (const row of rows) {
      if (row?.user_id) {
        ids.add(String(row.user_id));
      }
    }
  }
  return [...ids];
};

/**
 * Batch-load public profiles for a set of user ids.
 * @param {Array<string|import("mongoose").Types.ObjectId>} userIds
 * @returns {Promise<Map<string, {_id, name, username, profile_picture}>>}
 */
const loadCollaboratorProfiles = async (userIds) => {
  const map = new Map();
  const unique = [...new Set((userIds || []).map((id) => String(id)))].filter(
    Boolean,
  );
  if (!unique.length) {
    return map;
  }

  const users = await User.find({ _id: { $in: unique } })
    .select(COLLABORATOR_PUBLIC_FIELDS)
    .lean();

  for (const user of users) {
    map.set(String(user._id), {
      _id: String(user._id),
      name: user.name || null,
      username: user.username || null,
      profile_picture: user.profile_picture || null,
    });
  }
  return map;
};

/**
 * Shape one `collaborators[]` array using a preloaded profile map.
 * Collaborators whose user record is missing (e.g. deleted account) are
 * skipped so the API never returns a half-populated row.
 *
 * @param {Array<{user_id, status}>} collaborators
 * @param {Map} profileMap
 * @param {(row, user) => object} [extra] extra fields to merge per collaborator
 * @returns {Array<{user, status}>}
 */
const serializeCollaborators = (collaborators, profileMap, extra) => {
  const rows = Array.isArray(collaborators) ? collaborators : [];
  const out = [];
  for (const row of rows) {
    if (!row?.user_id) {
      continue;
    }
    const user = profileMap.get(String(row.user_id));
    if (!user) {
      continue;
    }
    out.push({
      user,
      status: normalizeStatus(row.status),
      ...(typeof extra === "function" ? extra(row, user) : {}),
    });
  }
  return out;
};

/**
 * Convenience for a single document: load profiles and serialize in one call.
 * @param {Array<{user_id, status}>} collaborators
 * @returns {Promise<Array<{user, status}>>}
 */
const buildCollaboratorsForDoc = async (collaborators) => {
  const ids = collectCollaboratorUserIds([{ collaborators }]);
  const profileMap = await loadCollaboratorProfiles(ids);
  return serializeCollaborators(collaborators, profileMap);
};

module.exports = {
  COLLABORATOR_PUBLIC_FIELDS,
  collectCollaboratorUserIds,
  loadCollaboratorProfiles,
  serializeCollaborators,
  buildCollaboratorsForDoc,
};

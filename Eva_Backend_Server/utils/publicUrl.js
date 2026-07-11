/**
 * Backend public URL helpers (env loaded via dotenv in app.js).
 *
 * BACKEND_PORT — port Express listens on (default 3000)
 * BACKEND_PUBLIC_URL — optional host/base for email links (port comes from BACKEND_PORT)
 *   unset  → http://localhost:{BACKEND_PORT}
 *   set    → http://192.168.1.10:{BACKEND_PORT}  (mobile testing on same Wi-Fi)
 *   https  → https://api.example.com  (production, no port appended)
 */

const getBackendPort = () => {
  // Prefer PORT (injected by hosts like Render/Heroku), then BACKEND_PORT, then default.
  const parsed = parseInt(process.env.PORT || process.env.BACKEND_PORT, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 3000;
};

const stripTrailingSlashes = (value) =>
  String(value || "").trim().replace(/\/+$/, "");

const buildBackendPublicUrl = () => {
  const raw = stripTrailingSlashes(process.env.BACKEND_PUBLIC_URL);
  if (!raw) {
    return `http://localhost:${getBackendPort()}`;
  }

  const withScheme = /^https?:\/\//i.test(raw) ? raw : `http://${raw}`;

  try {
    const url = new URL(withScheme);
    if (!url.port && url.protocol !== "https:") {
      url.port = String(getBackendPort());
    }
    return url.origin;
  } catch {
    return `http://localhost:${getBackendPort()}`;
  }
};

/** Build `{base}{path}?token=...` or use an optional full-URL template override. */
const buildTokenLink = (template, path, token) => {
  const custom = stripTrailingSlashes(template);
  const encoded = encodeURIComponent(token);

  if (custom) {
    if (custom.includes("{token}")) {
      return custom.replace("{token}", encoded);
    }
    const separator = custom.includes("?") ? "&" : "?";
    return `${custom}${separator}token=${encoded}`;
  }

  const apiPath = String(path || "").startsWith("/") ? path : `/${path || ""}`;
  return `${buildBackendPublicUrl()}${apiPath}?token=${encoded}`;
};

module.exports = {
  getBackendPort,
  buildBackendPublicUrl,
  buildTokenLink,
};

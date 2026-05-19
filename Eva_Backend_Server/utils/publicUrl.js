/**
 * Public URL helper
 * Builds a single backend public base URL from env values.
 */

const buildBackendPublicUrl = () => {
  const explicit = String(process.env.BACKEND_PUBLIC_URL || "").trim();
  if (explicit) {
    return explicit.replace(/\/+$/, "");
  }

  const scheme = String(process.env.BACKEND_SCHEME || "http").trim() || "http";
  const host = String(process.env.BACKEND_HOST || "localhost").trim() || "localhost";
  const port = String(process.env.BACKEND_PORT || process.env.PORT || "3000").trim() || "3000";

  return `${scheme}://${host}:${port}`.replace(/\/+$/, "");
};

module.exports = {
  buildBackendPublicUrl,
};


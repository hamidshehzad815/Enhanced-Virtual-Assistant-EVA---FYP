/**
 * Minimal HTML page for email verification (browser link from email).
 */

const escapeHtml = (value) =>
  String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");

/**
 * @param {{ success: boolean, title: string, message: string }} opts
 * @returns {string}
 */
const renderEmailVerificationPage = ({ success, title, message }) => {
  const safeTitle = escapeHtml(title);
  const safeMessage = escapeHtml(message);
  const accent = success ? "#059669" : "#dc2626";
  const accentSoft = success ? "#d1fae5" : "#fee2e2";
  const icon = success ? "✓" : "!";

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${safeTitle} · EVA</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1.25rem;
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      background: linear-gradient(145deg, #f0f4ff 0%, #e8eef8 50%, #f5f7fa 100%);
      color: #1e293b;
    }
    .card {
      width: 100%;
      max-width: 22rem;
      padding: 1.75rem 1.5rem;
      text-align: center;
      background: #fff;
      border-radius: 1rem;
      box-shadow: 0 4px 24px rgba(15, 23, 42, 0.08), 0 1px 3px rgba(15, 23, 42, 0.06);
    }
    .icon {
      width: 3rem;
      height: 3rem;
      margin: 0 auto 1rem;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 50%;
      background: ${accentSoft};
      color: ${accent};
      font-size: 1.35rem;
      font-weight: 700;
      line-height: 1;
    }
    .brand {
      font-size: 0.7rem;
      font-weight: 600;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #64748b;
      margin-bottom: 0.35rem;
    }
    h1 {
      font-size: 1.15rem;
      font-weight: 600;
      margin-bottom: 0.5rem;
      color: #0f172a;
    }
    p {
      font-size: 0.9rem;
      line-height: 1.5;
      color: #475569;
    }
  </style>
</head>
<body>
  <div class="card" role="status">
    <div class="icon" aria-hidden="true">${icon}</div>
    <p class="brand">EVA</p>
    <h1>${safeTitle}</h1>
    <p>${safeMessage}</p>
  </div>
</body>
</html>`;
};

module.exports = { renderEmailVerificationPage, escapeHtml };

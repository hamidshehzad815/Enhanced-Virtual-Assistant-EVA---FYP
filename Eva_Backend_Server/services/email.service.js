/**
 * Email Service
 * Sends transactional email via the Brevo HTTP API.
 */

const axios = require("axios");
const logger = require("../config/logger");
const { buildTokenLink } = require("../utils/publicUrl");

const BREVO_ENDPOINT = "https://api.brevo.com/v3/smtp/email";

/**
 * Resolve the sender identity from EMAIL_FROM into Brevo's { name, email } shape.
 * The email must be a sender verified in Brevo (single-sender or a verified domain).
 * Accepts either a bare address ("me@gmail.com") or a formatted one
 * ("EVA Assistant <me@gmail.com>"); a bare address gets a default display name.
 */
const getSender = () => {
  const raw = (process.env.EMAIL_FROM || "").trim();
  if (!raw) return null;

  const match = raw.match(/^\s*(.*?)\s*<\s*([^>]+?)\s*>\s*$/);
  if (match) {
    return { name: match[1] || "EVA Assistant", email: match[2].trim() };
  }
  return { name: "EVA Assistant", email: raw };
};

/** Whether email sending is configured (API key + sender address both present). */
const isEmailConfigured = () =>
  Boolean(process.env.BREVO_API_KEY && getSender());

/**
 * Send email
 * @param {Object} options - Email options
 * @param {string} options.to - Recipient email
 * @param {string} options.subject - Email subject
 * @param {string} options.text - Plain text body
 * @param {string} options.html - HTML body
 * @returns {Promise<boolean>}
 */
const sendEmail = async ({ to, subject, text, html }) => {
  const apiKey = process.env.BREVO_API_KEY;
  const sender = getSender();

  if (!apiKey || !sender) {
    logger.warn("Email not sent: Brevo not configured", {
      to,
      subject,
      hasApiKey: Boolean(apiKey),
      hasFrom: Boolean(sender),
    });
    return false;
  }

  const recipients = Array.isArray(to)
    ? to.map((email) => ({ email }))
    : [{ email: to }];

  try {
    const response = await axios.post(
      BREVO_ENDPOINT,
      {
        sender,
        to: recipients,
        subject,
        htmlContent: html,
        textContent: text,
      },
      {
        headers: {
          "api-key": apiKey,
          "Content-Type": "application/json",
          accept: "application/json",
        },
        timeout: 15000,
      },
    );

    logger.info("Email sent", {
      to,
      subject,
      messageId: response.data?.messageId,
    });
    return true;
  } catch (error) {
    const detail = error.response?.data || error.message;
    logger.error("Email sending failed", {
      to,
      subject,
      error: typeof detail === "string" ? detail : JSON.stringify(detail),
    });
    return false;
  }
};

/**
 * Send verification email
 * @param {string} to - Recipient email
 * @param {string} name - User's name
 * @param {string} token - Verification token
 * @returns {Promise<boolean>}
 */
const sendVerificationEmail = async (to, name, token) => {
  const verifyUrl = buildTokenLink(
    process.env.VERIFY_EMAIL_URL,
    "/api/auth/verify-email",
    token,
  );

  const subject = "Verify your EVA account";

  const text = `
Hello ${name},

Welcome to EVA - Your Enhanced Virtual Assistant!

Please verify your email address by clicking the link below:

${verifyUrl}

This link will expire in 24 hours.

If you didn't create an account, please ignore this email.

Best regards,
EVA Team
  `;

  const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Verify your email</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
    <h1 style="color: white; margin: 0; font-size: 28px;">EVA</h1>
    <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">Enhanced Virtual Assistant</p>
  </div>

  <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
    <h2 style="color: #333; margin-top: 0;">Hello ${name}! 👋</h2>

    <p>Welcome to EVA! We're excited to have you on board.</p>

    <p>Please verify your email address by clicking the button below:</p>

    <div style="text-align: center; margin: 30px 0;">
      <a href="${verifyUrl}"
         style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 15px 40px;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
                display: inline-block;">
        Verify Email
      </a>
    </div>

    <p style="color: #666; font-size: 14px;">Or copy and paste this link in your browser:</p>
    <p style="background: #e9e9e9; padding: 10px; border-radius: 5px; word-break: break-all; font-size: 12px;">
      ${verifyUrl}
    </p>

    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">

    <p style="color: #999; font-size: 12px;">
      This link will expire in 24 hours.<br>
      If you didn't create an account, please ignore this email.
    </p>
  </div>

  <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
    <p>&copy; 2024 EVA - Enhanced Virtual Assistant</p>
  </div>
</body>
</html>
  `;

  return sendEmail({ to, subject, text, html });
};

/**
 * Send password reset email
 * @param {string} to - Recipient email
 * @param {string} name - User's name
 * @param {string} token - Password reset token
 * @returns {Promise<boolean>}
 */
const sendPasswordResetEmail = async (to, name, token) => {
  if (!process.env.RESET_PASSWORD_URL) {
    logger.warn(
      "RESET_PASSWORD_URL is not set. The reset link will fall back to the backend "
        + "API endpoint (/api/auth/reset-password) instead of the web reset form, so "
        + "the emailed link will not open a usable page. Set RESET_PASSWORD_URL to your "
        + "reset-password web page, e.g. https://<web-frontend>/reset-password",
    );
  }

  const resetUrl = buildTokenLink(
    process.env.RESET_PASSWORD_URL,
    "/api/auth/reset-password",
    token,
  );

  const subject = "Reset your EVA password";

  const text = `
Hello ${name},

We received a request to reset your EVA account password.

Use the link below to reset your password:
${resetUrl}

This link will expire in 1 hour.

If you did not request this, please ignore this email.

Best regards,
EVA Team
  `;

  const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Reset your password</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <div style="background: linear-gradient(135deg, #2563eb 0%, #0f766e 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
    <h1 style="color: white; margin: 0; font-size: 28px;">EVA</h1>
    <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">Password Reset</p>
  </div>

  <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
    <h2 style="color: #333; margin-top: 0;">Hello ${name},</h2>

    <p>We received a request to reset your EVA account password.</p>

    <div style="text-align: center; margin: 30px 0;">
      <a href="${resetUrl}"
         style="background: linear-gradient(135deg, #2563eb 0%, #0f766e 100%);
                color: white;
                padding: 15px 40px;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
                display: inline-block;">
        Reset Password
      </a>
    </div>

    <p style="color: #666; font-size: 14px;">Or copy and paste this link in your browser:</p>
    <p style="background: #e9e9e9; padding: 10px; border-radius: 5px; word-break: break-all; font-size: 12px;">
      ${resetUrl}
    </p>

    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">

    <p style="color: #999; font-size: 12px;">
      This link will expire in 1 hour.<br>
      If you did not request this, please ignore this email.
    </p>
  </div>
</body>
</html>
  `;

  return sendEmail({ to, subject, text, html });
};

/**
 * Report whether the email service is ready to send.
 * Brevo is a stateless HTTP API, so there is no connection to open — this
 * just confirms the API key and sender address are configured.
 * @returns {Promise<boolean>}
 */
const verifyConnection = async () => {
  if (isEmailConfigured()) {
    logger.info("Email service ready (Brevo)");
    return true;
  }
  logger.warn(
    "Email service not configured (missing BREVO_API_KEY or EMAIL_FROM)",
  );
  return false;
};

module.exports = {
  sendEmail,
  sendVerificationEmail,
  sendPasswordResetEmail,
  verifyConnection,
  isEmailConfigured,
};

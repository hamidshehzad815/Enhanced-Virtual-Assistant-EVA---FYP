/**
 * Email Service
 * Handles sending emails using Nodemailer
 */

const nodemailer = require("nodemailer");
const logger = require("../config/logger");
const { buildTokenLink } = require("../utils/publicUrl");

// Create reusable transporter
let transporter = null;

/**
 * Initialize email transporter
 */
const initializeTransporter = () => {
  if (transporter) return transporter;

  transporter = nodemailer.createTransport({
    host: process.env.EMAIL_HOST,
    port: parseInt(process.env.EMAIL_PORT, 10),
    secure: false, // true for 465, false for other ports
    auth: {
      user: process.env.EMAIL_USER,
      pass: process.env.EMAIL_PASS,
    },
  });

  return transporter;
};

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
  try {
    const transport = initializeTransporter();

    const mailOptions = {
      from: `"EVA Assistant" <${process.env.EMAIL_USER}>`,
      to,
      subject,
      text,
      html,
    };

    const info = await transport.sendMail(mailOptions);
    logger.info("Email sent", { to, subject, messageId: info.messageId });
    return true;
  } catch (error) {
    logger.error("Email sending failed", { to, subject, error: error.message });
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
 * Verify transporter connection
 * @returns {Promise<boolean>}
 */
const verifyConnection = async () => {
  try {
    const transport = initializeTransporter();
    await transport.verify();
    logger.info("Email service connected");
    return true;
  } catch (error) {
    logger.error("Email service connection failed", { error: error.message });
    return false;
  }
};

module.exports = {
  sendEmail,
  sendVerificationEmail,
  sendPasswordResetEmail,
  verifyConnection,
};

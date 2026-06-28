const { OAuth2Client } = require("google-auth-library");

const getGoogleAudiences = () => {
  const audiences = [
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_ANDROID_CLIENT_ID,
  ]
    .map((value) => String(value || "").trim())
    .filter(Boolean);

  if (!audiences.length) {
    throw new Error("GOOGLE_CLIENT_ID is not configured");
  }

  return audiences;
};

/**
 * Verify a Google ID token and return normalized profile fields.
 */
const verifyGoogleIdToken = async (idToken) => {
  const client = new OAuth2Client();
  const ticket = await client.verifyIdToken({
    idToken: String(idToken).trim(),
    audience: getGoogleAudiences(),
  });

  const payload = ticket.getPayload();
  if (!payload) {
    throw new Error("Invalid Google token payload");
  }

  return {
    googleId: payload.sub,
    email: payload.email ? String(payload.email).toLowerCase().trim() : "",
    emailVerified: payload.email_verified === true,
    name: payload.name ? String(payload.name).trim() : "",
    picture: payload.picture ? String(payload.picture).trim() : null,
  };
};

module.exports = {
  verifyGoogleIdToken,
  getGoogleAudiences,
};

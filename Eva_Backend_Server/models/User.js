/**
 * User Model
 * Handles user authentication and profile data
 */

const mongoose = require("mongoose");
const bcrypt = require("bcryptjs");

const userSchema = new mongoose.Schema(
  {
    name: {
      type: String,
      required: [true, "Name is required"],
      trim: true,
      maxlength: [100, "Name cannot exceed 100 characters"],
    },
    username: {
      type: String,
      required: [true, "Username is required"],
      unique: true,
      trim: true,
      lowercase: true,
      minlength: [3, "Username must be at least 3 characters"],
      maxlength: [30, "Username cannot exceed 30 characters"],
      match: [
        /^[a-z0-9_]+$/,
        "Username can only contain lowercase letters, numbers, and underscores",
      ],
    },
    email: {
      type: String,
      required: [true, "Email is required"],
      unique: true,
      trim: true,
      lowercase: true,
      match: [/^\S+@\S+\.\S+$/, "Please provide a valid email"],
    },
    password_hash: {
      type: String,
      select: false,
      minlength: [6, "Password must be at least 6 characters"],
    },
    profile_picture: {
      type: String,
      default: null,
    },
    profile_picture_public_id: {
      type: String,
      default: null,
      select: false,
    },
    bio: {
      type: String,
      maxlength: [300, "Bio cannot exceed 300 characters"],
      default: null,
    },
    university: {
      type: String,
      trim: true,
      default: null,
    },
    department: {
      type: String,
      trim: true,
      default: null,
    },
    semester: {
      type: Number,
      min: [1, "Semester must be at least 1"],
      max: [12, "Semester cannot exceed 12"],
      default: null,
    },
    timezone: {
      type: String,
      required: true,
      default: "Asia/Karachi",
    },
    push_tokens: {
      type: [String],
      default: [],
    },
    auth_provider: {
      type: String,
      enum: ["local", "google"],
      default: "local",
    },
    is_verified: {
      type: Boolean,
      default: false,
    },
    is_active: {
      type: Boolean,
      default: true,
    },
    email_verification_token: {
      type: String,
      select: false,
    },
    email_verification_expires: {
      type: Date,
      select: false,
    },
    password_reset_token: {
      type: String,
      select: false,
    },
    password_reset_expires: {
      type: Date,
      select: false,
    },
    refresh_token_hash: {
      type: String,
      select: false,
    },
    last_login: {
      type: Date,
      default: null,
    },
    last_active: {
      type: Date,
      default: null,
    },
  },
  {
    timestamps: {
      createdAt: "created_at",
      updatedAt: "updated_at",
    },
  },
);

// Index for faster queries
// Note: email and username already have indexes from unique: true
userSchema.index({ is_active: 1 });

/**
 * Hash password before saving
 */
userSchema.pre("save", async function (next) {
  // Only hash if password is modified
  if (!this.isModified("password_hash")) {
    return next();
  }

  // Hash password with salt rounds of 12
  if (this.password_hash) {
    this.password_hash = await bcrypt.hash(this.password_hash, 12);
  }
  next();
});

/**
 * Compare password with hash
 * @param {string} candidatePassword - Plain text password
 * @returns {Promise<boolean>}
 */
userSchema.methods.comparePassword = async function (candidatePassword) {
  return await bcrypt.compare(candidatePassword, this.password_hash);
};

/**
 * Hash refresh token before saving
 * @param {string} refreshToken - Plain refresh token
 */
userSchema.methods.setRefreshToken = async function (refreshToken) {
  this.refresh_token_hash = await bcrypt.hash(refreshToken, 10);
  await this.save();
};

/**
 * Compare refresh token with hash
 * @param {string} refreshToken - Plain refresh token
 * @returns {Promise<boolean>}
 */
userSchema.methods.compareRefreshToken = async function (refreshToken) {
  return await bcrypt.compare(refreshToken, this.refresh_token_hash);
};

/**
 * Clear refresh token (logout)
 */
userSchema.methods.clearRefreshToken = async function () {
  this.refresh_token_hash = null;
  await this.save();
};

/**
 * Update last login timestamp
 */
userSchema.methods.updateLastLogin = async function () {
  this.last_login = new Date();
  this.last_active = new Date();
  await this.save();
};

/**
 * Get public profile (safe to send to client)
 * @returns {Object}
 */
userSchema.methods.toPublicProfile = function () {
  return {
    _id: this._id,
    name: this.name,
    username: this.username,
    email: this.email,
    profile_picture: this.profile_picture,
    bio: this.bio,
    university: this.university,
    department: this.department,
    semester: this.semester,
    timezone: this.timezone,
    auth_provider: this.auth_provider,
    is_verified: this.is_verified,
    last_login: this.last_login,
    created_at: this.created_at,
  };
};

const User = mongoose.model("User", userSchema);

module.exports = User;

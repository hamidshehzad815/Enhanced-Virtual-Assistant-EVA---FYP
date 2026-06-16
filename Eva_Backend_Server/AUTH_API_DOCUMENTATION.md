# EVA Backend Auth API Documentation

This document covers authentication and profile APIs in `Eva_Backend_Server`.

Base URL (local):
- `http://localhost:3000`

Auth header (protected endpoints):
- `Authorization: Bearer <access_token>`

---

## 1) Register

Endpoint:
- `POST /api/auth/register`

Request body:
```json
{
  "name": "Hamid Shehzad",
  "username": "hamidlilla",
  "email": "hamid@example.com",
  "password": "secret123",
  "timezone": "Asia/Karachi"
}
```

Success response (`201`):
```json
{
  "status": "success",
  "message": "Registration successful. Please check your email to verify your account.",
  "data": {
    "user": {
      "_id": "507f1f77bcf86cd799439011",
      "name": "Hamid Shehzad",
      "username": "hamidlilla",
      "email": "hamid@example.com",
      "is_verified": false
    },
    "email_sent": true
  }
}
```

Common errors:
- `400` missing required fields
- `409` email/username already exists

---

## 2) Verify Email

Endpoint:
- `GET /api/auth/verify-email?token=<token>`

Success response (`200`):
```json
{
  "status": "success",
  "message": "Email verified successfully. You can now login."
}
```

Common errors:
- `400` token missing
- `400` invalid/expired token

---

## 3) Resend Verification Email

Endpoint:
- `POST /api/auth/resend-verification`

Request body:
```json
{
  "email": "hamid@example.com"
}
```

Success response (`200`):
```json
{
  "status": "success",
  "message": "If an account exists with this email, a verification link has been sent."
}
```

Common errors:
- `400` email missing
- `400` email already verified

---

## 4) Login

Endpoint:
- `POST /api/auth/login`

Request body:
```json
{
  "email": "hamid@example.com",
  "password": "secret123"
}
```

Success response (`200`):
```json
{
  "status": "success",
  "message": "Login successful",
  "data": {
    "user": {
      "_id": "507f1f77bcf86cd799439011",
      "name": "Hamid Shehzad",
      "username": "hamidlilla",
      "email": "hamid@example.com",
      "is_verified": true
    },
    "tokens": {
      "access_token": "<jwt>",
      "refresh_token": "<jwt>"
    }
  }
}
```

Common errors:
- `400` email/password missing
- `401` invalid credentials
- `401` account deactivated
- `401` email not verified

---

## 5) Refresh Token

Endpoint:
- `POST /api/auth/refresh`

Request body:
```json
{
  "refresh_token": "<jwt>"
}
```

Success response (`200`):
```json
{
  "status": "success",
  "message": "Token refreshed",
  "data": {
    "tokens": {
      "access_token": "<new_jwt>",
      "refresh_token": "<new_jwt>"
    }
  }
}
```

Common errors:
- `400` refresh token missing
- `401` invalid/expired refresh token

---

## 6) Forgot Password

Endpoint:
- `POST /api/auth/forgot-password`

Request body:
```json
{
  "email": "hamid@example.com"
}
```

Success response (`200`) (always generic to prevent account enumeration):
```json
{
  "status": "success",
  "message": "If an account exists with this email, a password reset link has been sent."
}
```

Common errors:
- `400` email missing

---

## 7) Reset Password

Endpoint:
- `POST /api/auth/reset-password`

Request body:
```json
{
  "token": "<reset_token_from_email>",
  "new_password": "newSecret123",
  "confirm_password": "newSecret123"
}
```

Success response (`200`):
```json
{
  "status": "success",
  "message": "Password reset successful. Please login with your new password."
}
```

Common errors:
- `400` token/new_password/confirm_password missing
- `400` password too short (minimum 6)
- `400` passwords do not match
- `400` invalid/expired token

---

## 8) Logout (Protected)

Endpoint:
- `POST /api/auth/logout`

Headers:
- `Authorization: Bearer <access_token>`

Success response (`200`):
```json
{
  "status": "success",
  "message": "Logged out successfully"
}
```

Common errors:
- `401` missing/invalid access token

---

## 9) Get Current User (Protected)

Endpoint:
- `GET /api/auth/me`

Headers:
- `Authorization: Bearer <access_token>`

Success response (`200`):
```json
{
  "status": "success",
  "data": {
    "user": {
      "_id": "507f1f77bcf86cd799439011",
      "name": "Hamid Shehzad",
      "username": "hamidlilla",
      "email": "hamid@example.com",
      "is_verified": true
    },
    "settings": {
      "theme": "system"
    }
  }
}
```

Common errors:
- `401` missing/invalid access token

---

## 10) Profile APIs (Protected)

### 10.1 Get Profile
Endpoint:
- `GET /api/profile`

Headers:
- `Authorization: Bearer <access_token>`

Success response (`200`):
```json
{
  "status": "success",
  "data": {
    "user": {
      "_id": "507f1f77bcf86cd799439011",
      "name": "Hamid Shehzad",
      "username": "hamidlilla",
      "email": "hamid@example.com",
      "profile_picture": null,
      "bio": null,
      "university": null,
      "department": null,
      "semester": null,
      "timezone": "Asia/Karachi",
      "auth_provider": "local",
      "is_verified": true,
      "last_login": "2026-04-30T10:00:00.000Z",
      "created_at": "2026-04-30T09:00:00.000Z"
    }
  }
}
```

### 10.2 Update Profile
Endpoint:
- `PATCH /api/profile`

Headers:
- `Authorization: Bearer <access_token>`

Allowed fields:
- `name`
- `username`
- `bio`
- `university`
- `department`
- `semester`
- `timezone`

Profile pictures are updated via `POST /api/profile/avatar` (multipart field `avatar`), not PATCH.

### 10.3 Upload Profile Picture
Endpoint:
- `POST /api/profile/avatar`

Headers:
- `Authorization: Bearer <access_token>`
- `Content-Type: multipart/form-data`

Form field:
- `avatar` (JPEG, PNG, or WebP; max 2 MB)

Success response (`200`):
```json
{
  "status": "success",
  "message": "Profile picture updated",
  "data": {
    "user": {
      "profile_picture": "https://res.cloudinary.com/..."
    }
  }
}
```

### 10.4 Update Profile (example)
Example request body:
```json
{
  "name": "Hamid S.",
  "bio": "FYP student",
  "timezone": "Asia/Karachi"
}
```

Success response (`200`):
```json
{
  "status": "success",
  "message": "Profile updated",
  "data": {
    "user": {
      "_id": "507f1f77bcf86cd799439011",
      "name": "Hamid S.",
      "username": "hamidlilla",
      "email": "hamid@example.com"
    }
  }
}
```

Common errors:
- `400` invalid field(s) or invalid input
- `409` username already taken
- `401` missing/invalid access token

---

## Notes on Email Links

Verification and reset links are generated from:
- `VERIFY_EMAIL_URL` (optional)
- `RESET_PASSWORD_URL` (optional)
- fallback backend URL: `BACKEND_PUBLIC_URL` or `http://localhost:<PORT>`

Template support:
- if URL contains `{token}`, token is injected there.
- otherwise, `?token=<...>` is appended.


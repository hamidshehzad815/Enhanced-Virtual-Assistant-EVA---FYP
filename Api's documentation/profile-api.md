# Profile API

Authenticated user's identity: name, username, email, profile picture, timezone, email verification status.

**Base path:** `/api/profile`  
See [README.md](./README.md) for auth headers and error envelopes.

---

## User object (`data.user`)

Returned by all three profile endpoints inside `data.user`.  
Every success response also includes top-level `data.timezone` (same IANA string as `user.timezone`).

| Field | Type | Editable? | Notes |
|-------|------|-----------|-------|
| `_id` | `string` | No | MongoDB user id |
| `name` | `string` | Yes | Display name; max 100 chars |
| `username` | `string` | Yes | Lowercase; 3–30 chars; `[a-z0-9_]` only; unique |
| `email` | `string` | **No** | Read-only on profile API |
| `profile_picture` | `string \| null` | Via avatar upload only | Cloudinary HTTPS URL or `null` |
| `timezone` | `string` | Yes | IANA timezone, e.g. `"Asia/Karachi"` |
| `is_verified` | `boolean` | No | `true` when email is verified |

### Fields NOT returned (removed from API)

Do not expect these on profile responses — they are not exposed:

| Field | Reason |
|-------|--------|
| `bio` | Removed from profile API |
| `university` | Removed from profile API |
| `department` | Removed from profile API |
| `semester` | Removed from profile API |
| `auth_provider` | Internal login method (`local` / `google`) |
| `last_login` | Not needed for profile UI |
| `created_at` | Not needed for profile UI |
| `password`, tokens, `push_tokens` | Never exposed |

---

## Profile vs `GET /api/auth/me`

Use the right endpoint for each screen:

| | `GET /api/profile` | `GET /api/auth/me` |
|--|-------------------|-------------------|
| **Purpose** | Full profile screen | App bootstrap after login |
| **User fields** | Name, username, email, picture, timezone, `is_verified` | Slim: `_id`, name, username, email, picture, `is_verified` |
| **Settings** | No | Yes — theme, notification toggles, quiet hours, `allow_friend_requests` |
| **When to call** | Profile / Edit Profile screen | Splash, home init, session restore |

For **Profile screen** → always use **`GET /api/profile`**.

---

## `GET /api/profile`

Load the logged-in user's profile.

| | |
|---|---|
| **Auth** | Required |
| **Method** | `GET` |
| **Path** | `/api/profile` |
| **Query params** | None |
| **Request body** | None |

### Success `200`

```json
{
  "status": "success",
  "data": {
    "timezone": "Asia/Karachi",
    "user": {
      "_id": "674a1b2c3d4e5f6789012301",
      "name": "Hamid",
      "username": "hamid",
      "email": "hamid@example.com",
      "profile_picture": null,
      "timezone": "Asia/Karachi",
      "is_verified": true
    }
  }
}
```

### Errors

| Status | When |
|--------|------|
| `401` | Missing or invalid token |
| `500` | Server error |

---

## `PATCH /api/profile`

Partial update — send **only fields you change**.

| | |
|---|---|
| **Auth** | Required |
| **Method** | `PATCH` |
| **Path** | `/api/profile` |
| **Content-Type** | `application/json` |

### Accepted body fields

| Field | Type | Validation |
|-------|------|------------|
| `name` | `string` | Required if sent; cannot be empty after trim; max 100 chars |
| `username` | `string` | Required if sent; auto-lowercased; 3–30 chars; letters, numbers, underscore only; unique per user |
| `timezone` | `string` | Required if sent; non-empty IANA string |

### Rejected body fields (`400`)

Any key not in the table above is rejected, including:

| Field | Result |
|-------|--------|
| `email` | `Invalid profile fields: email` |
| `profile_picture` | `Invalid profile fields: profile_picture` |
| `bio`, `university`, `department`, `semester` | Removed — rejected if sent |
| `is_verified`, `auth_provider`, `_id` | Rejected |

Other validation errors:

| Condition | Message (example) |
|-----------|-------------------|
| Empty body / no allowed fields | `No valid profile fields provided` |
| Empty `name` when sent | `name is required` |
| Empty `username` when sent | `username is required` |
| Empty `timezone` when sent | `timezone is required` |

### Username rules

- Minimum 3 characters, maximum 30
- Only lowercase letters, numbers, and underscore: `^[a-z0-9_]+$`
- Server lowercases before save
- If another user already has that username → **`409`** `Username already taken`

### Example requests

**Change display name:**
```json
{
  "name": "Hamid Ali"
}
```

**Change username:**
```json
{
  "username": "hamid_ali"
}
```

**Change timezone:**
```json
{
  "timezone": "Europe/London"
}
```

**Multiple fields at once:**
```json
{
  "name": "Hamid Ali",
  "username": "hamid_ali",
  "timezone": "Asia/Karachi"
}
```

### Success `200`

```json
{
  "status": "success",
  "message": "Profile updated",
  "data": {
    "timezone": "Asia/Karachi",
    "user": {
      "_id": "674a1b2c3d4e5f6789012301",
      "name": "Hamid Ali",
      "username": "hamid_ali",
      "email": "hamid@example.com",
      "profile_picture": null,
      "timezone": "Asia/Karachi",
      "is_verified": true
    }
  }
}
```

Use `data.user` from the response to refresh the UI (no need to call GET again unless you prefer).

### Errors

| Status | When |
|--------|------|
| `400` | Invalid/unknown field, empty body, validation error |
| `401` | Auth failure |
| `409` | Username already taken |
| `422` | Mongoose validation (e.g. username format fails DB rules) |
| `500` | Server error |

---

## `POST /api/profile/avatar`

Upload or replace the profile picture. **Only way** to set `profile_picture`.

| | |
|---|---|
| **Auth** | Required |
| **Method** | `POST` |
| **Path** | `/api/profile/avatar` |
| **Content-Type** | `multipart/form-data` |
| **JSON body** | Not used |

### Request (multipart)

| Part | Name | Type | Required |
|------|------|------|----------|
| File field | `avatar` | Image file | Yes |

**File rules:**

| Rule | Value |
|------|--------|
| Allowed MIME types | `image/jpeg`, `image/png`, `image/webp` |
| Max file size | **2 MB** default (`AVATAR_MAX_SIZE_MB` on server) |
| Rate limit | **10 uploads per hour** per user |

**Do not** send `profile_picture` as a URL on `PATCH /api/profile` — it will be rejected.

### What the server does

1. Validates file type and size
2. Uploads to **Cloudinary** (cropped to 400×400)
3. Deletes previous Cloudinary image if one existed
4. Saves new `profile_picture` URL on the user
5. Returns updated `data.user`

### Success `200`

```json
{
  "status": "success",
  "message": "Profile picture updated",
  "data": {
    "timezone": "Asia/Karachi",
    "user": {
      "_id": "674a1b2c3d4e5f6789012301",
      "name": "Hamid",
      "username": "hamid",
      "email": "hamid@example.com",
      "profile_picture": "https://res.cloudinary.com/demo/image/upload/v123/eva/profile-pictures/674a1b2c_1717584000000.jpg",
      "timezone": "Asia/Karachi",
      "is_verified": true
    }
  }
}
```

### Errors

| Status | When |
|--------|------|
| `400` | Missing file, wrong MIME type, empty file, file too large |
| `401` | Auth failure |
| `429` | Too many uploads in one hour |
| `502` | Cloudinary upload failed |
| `500` | Server error |

**429 response example:**
```json
{
  "status": "fail",
  "message": "Too many profile picture uploads, please try again later"
}
```

---

## `DELETE /api/profile/avatar`

Remove the profile picture. Clears `profile_picture` on the user and deletes the image from Cloudinary when a `profile_picture_public_id` is stored.

| | |
|---|---|
| **Auth** | Required |
| **Method** | `DELETE` |
| **Path** | `/api/profile/avatar` |
| **Body** | None |

### What the server does

1. Loads the user's stored Cloudinary `public_id` (if any)
2. Deletes the image from Cloudinary (best-effort; failures are logged, DB still cleared)
3. Sets `profile_picture` and `profile_picture_public_id` to `null`
4. Returns updated `data.user`

If the user already has no picture, returns `200` with message `"No profile picture to remove"` (idempotent).

### Success `200`

```json
{
  "status": "success",
  "message": "Profile picture removed",
  "data": {
    "timezone": "Asia/Karachi",
    "user": {
      "_id": "674a1b2c3d4e5f6789012301",
      "name": "Hamid",
      "username": "hamid",
      "email": "hamid@example.com",
      "profile_picture": null,
      "timezone": "Asia/Karachi",
      "is_verified": true
    }
  }
}
```

### Errors

| Status | When |
|--------|------|
| `401` | Auth failure |
| `500` | Server error |

---

## TypeScript reference (optional)

```typescript
type ProfileUser = {
  _id: string;
  name: string;
  username: string;
  email: string;
  profile_picture: string | null;
  timezone: string;
  is_verified: boolean;
};

type ProfileGetResponse = {
  status: "success";
  data: {
    timezone: string;
    user: ProfileUser;
  };
};

type ProfilePatchBody = Partial<{
  name: string;
  username: string;
  timezone: string;
}>;

type ProfilePatchResponse = {
  status: "success";
  message: "Profile updated";
  data: {
    timezone: string;
    user: ProfileUser;
  };
};

type ProfileAvatarResponse = {
  status: "success";
  message: "Profile picture updated";
  data: {
    timezone: string;
    user: ProfileUser;
  };
};
```

---

## Frontend screen mapping

| UI action | API |
|-----------|-----|
| Open Profile screen | `GET /api/profile` |
| Edit name | `PATCH /api/profile` → `{ "name": "..." }` |
| Edit username | `PATCH /api/profile` → `{ "username": "..." }` |
| Change timezone | `PATCH /api/profile` → `{ "timezone": "..." }` |
| Pick / change photo | `POST /api/profile/avatar` (multipart, field `avatar`) |
| Remove photo | `DELETE /api/profile/avatar` |
| Show "Verify email" banner | `user.is_verified === false` |
| Show avatar placeholder | `profile_picture === null` |

---

## Flutter / HTTP client notes

### Read profile
```
GET /api/profile
Headers: Authorization: Bearer <token>
```

### Update text fields
```
PATCH /api/profile
Headers:
  Authorization: Bearer <token>
  Content-Type: application/json
Body: { "name": "...", "timezone": "Asia/Karachi" }
```

### Upload avatar (multipart)

- Use `multipart/form-data` with field name **`avatar`** (exact spelling).
- Do **not** set `Content-Type: application/json` on this request — let the HTTP client set the multipart boundary.
- On success, bind avatar widget to `response.data.user.profile_picture`.
- Handle `profile_picture: null` with a default placeholder image.
- On `429`, show "Try again later" — user hit hourly upload limit.

### Other users' profiles

There is **no** `GET /api/profile/:userId`.  
Friend lists and search return a **partial** user snippet only (`name`, `username`, `email`, `profile_picture`) via Friends APIs — not this profile endpoint.

---

## Quick cheat sheet

| Action | Method | URL | Body |
|--------|--------|-----|------|
| Load profile | `GET` | `/api/profile` | — |
| Update name / username / timezone | `PATCH` | `/api/profile` | JSON (partial) |
| Change photo | `POST` | `/api/profile/avatar` | `multipart`, field `avatar` |

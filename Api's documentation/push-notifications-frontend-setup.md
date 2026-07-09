# Push Notifications — Frontend Setup Guide

Guide for the **Flutter developer** integrating FCM (Firebase Cloud Messaging) with the EVA Node backend.

The **backend push pipeline is already implemented**. Your job is to configure Firebase in the app, obtain an FCM device token, and register it with the backend.

---

## 1. Backend status (already done)

| Component | Status |
|-----------|--------|
| `firebase-admin` SDK | Installed (`Eva_Backend_Server/package.json`) |
| FCM send logic | `services/notification.service.js` → `dispatch_push()` |
| Token storage | `User.push_tokens[]` (MongoDB) |
| Register / remove token | `PATCH /api/settings` with `push_token` / `remove_push_token` |
| User toggles | `notifications_enabled`, `push_notifications_enabled` on `UserSetting` |
| Invalid token cleanup | Backend removes dead tokens after FCM rejection |
| Triggers that send push | Task/topic reminders, overdue alerts, friend requests, collaboration invites, chat/AI actions (when `delivery_channel` includes `"push"`) |

### Backend `.env` (backend team only — not in Flutter)

Set **one** of:

```env
FIREBASE_CREDENTIALS=./evafirebase-c92ab-firebase-adminsdk-....json
```

or paste the full JSON inline:

```env
FIREBASE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
```

**Never commit** the service account JSON. It is gitignored.

Firebase project used in dev: **`evafirebase-c92ab`**

If credentials are missing, backend logs:

`Push dispatch skipped: Firebase not configured`

If the user has no device token yet:

`Push dispatch skipped: no registered device tokens`

---

## 2. What the frontend must do

1. Create/configure the Firebase **Android app** (and iOS later if needed) in [Firebase Console](https://console.firebase.google.com/).
2. Add Flutter packages: `firebase_core`, `firebase_messaging`.
3. Add `google-services.json` to `Frontend/android/app/` (download from Firebase Console).
4. Apply Google Services Gradle plugin (Android).
5. Request notification permission (Android 13+ / iOS).
6. After login, get FCM token and call **`PATCH /api/settings`**.
7. On logout, call **`PATCH /api/settings`** with `remove_push_token`.
8. (Recommended) Handle foreground messages — see section 7.

---

## 3. Firebase Console setup

1. Open project **`evafirebase-c92ab`** (or create a new one and align with backend team).
2. Add Android app:
   - **Package name:** `com.example.eva` (must match `applicationId` in `android/app/build.gradle.kts`).
3. Download **`google-services.json`** → place at:

   ```
   Frontend/android/app/google-services.json
   ```

4. Enable **Cloud Messaging** (enabled by default on new projects).

> The file `google-services.json` is a **client** config. It is safe to commit if API keys are restricted in Firebase Console (Android app + package name). The **admin** service account JSON stays on the backend only.

---

## 4. Flutter dependencies

**Team build:** use **FVM Flutter 3.35.1** (see `Frontend/.fvmrc`). Run `fvm flutter pub get` / `fvm flutter run` — not global `flutter`.

```yaml
environment:
  sdk: ^3.9.0

dependencies:
  firebase_core: ^4.11.0
  firebase_messaging: ^16.4.0
  flutter_local_notifications: ^20.1.0   # ^22.x needs Flutter 3.38+
```

```bash
cd Frontend
fvm install
fvm flutter pub get
```

In `pubspec.yaml`:

```yaml
dependencies:
  firebase_core: ^3.8.1
  firebase_messaging: ^15.1.5
```

Run:

```bash
flutter pub get
```

---

## 5. Android native setup

### `android/settings.gradle.kts`

Inside `plugins { ... }`:

```kotlin
id("com.google.gms.google-services") version "4.4.4" apply false
```

### `android/app/build.gradle.kts`

Inside `plugins { ... }` (after Flutter plugin):

```kotlin
id("com.google.gms.google-services")
```

### `android/app/src/main/AndroidManifest.xml`

```xml
<uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
```

### Emulator / device

- Use an emulator image **with Google Play**.
- FCM requires Google Play Services.

---

## 6. Backend API contract

Full settings reference: [settings-api.md](./settings-api.md)

### Register device token

**`PATCH /api/settings`**

Headers:

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

Body:

```json
{
  "push_token": "<fcm_device_token>"
}
```

Success: `200` — token is appended to `User.push_tokens[]` (`$addToSet`, no duplicates).

**When to call:**

| Event | Action |
|-------|--------|
| After successful login | Register token |
| App start + user already logged in (e.g. splash) | Register token |
| FCM `onTokenRefresh` | Re-register new token |

### Remove device token (logout)

```json
{
  "remove_push_token": "<fcm_device_token>"
}
```

### Push toggles (settings screen)

Read/write via same endpoint:

| Field | Default | Effect |
|-------|---------|--------|
| `notifications_enabled` | `true` | Master switch — if `false`, no push/email/in-app dispatch |
| `push_notifications_enabled` | `true` | If `false`, push skipped even if token exists |

These fields **are** returned on `GET /api/settings`.  
`push_tokens` are **not** returned (stored on `User`, not settings doc).

---

## 7. Recommended Flutter implementation

### Minimal flow (token registration only)

```dart
// main.dart
WidgetsFlutterBinding.ensureInitialized();
await Firebase.initializeApp();
// ... runApp

// After login / on splash if token exists:
final fcmToken = await FirebaseMessaging.instance.getToken();
await http.patch(
  Uri.parse('$baseUrl/settings'),
  headers: {
    'Authorization': 'Bearer $accessToken',
    'Content-Type': 'application/json',
  },
  body: jsonEncode({'push_token': fcmToken}),
);

FirebaseMessaging.instance.onTokenRefresh.listen((newToken) {
  // PATCH push_token again with newToken
});
```

### Android 13+ permission

`FirebaseMessaging.instance.requestPermission()` is mainly for iOS. On Android 13+, ensure notification permission is granted (via `firebase_messaging` or `permission_handler`).

### Foreground notifications (important)

If the app is **open in foreground**, Android often **does not show a system banner** unless you handle it.

Add:

```dart
FirebaseMessaging.onMessage.listen((RemoteMessage message) {
  // Show local notification or in-app snackbar using message.notification?.title / body
});
```

For background/killed app, FCM `notification` payload from backend is usually shown automatically.

### Optional: tap handling

```dart
FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
  // Navigate using message.data['type'], message.data['reference_id'], etc.
});

final initial = await FirebaseMessaging.instance.getInitialMessage();
// Handle cold start from notification tap
```

---

## 8. FCM payload shape (from backend)

Backend sends via Firebase Admin (`sendEachForMulticast`):

**Notification (system tray):**

| Field | Source |
|-------|--------|
| `title` | `notification.title` |
| `body` | `notification.message` |

**Data payload (all strings):**

| Key | Example | Notes |
|-----|---------|-------|
| `notification_id` | MongoDB notification `_id` | Mark read via `PATCH /api/notifications/:id/read` |
| `type` | `task_reminder`, `friend_request`, `topic_reminder`, … | See `Notification` model enum in backend |
| `reference_type` | `task`, `topic`, `learning_goal`, `friend` | May be empty |
| `reference_id` | ObjectId string | May be empty |
| Extra keys | e.g. `learning_goal_id`, `suggested_action` | Only on some learning notifications (`push_data`) |

Example data-only extras for learning topic reminders:

```json
{
  "learning_goal_id": "...",
  "learning_topic_id": "...",
  "suggested_action": "complete_learning_topic"
}
```

---

## 9. In-app notification inbox (separate from push)

Push is one channel. In-app list uses:

| Method | Path |
|--------|------|
| `GET` | `/api/notifications?limit=20&skip=0` |
| `GET` | `/api/notifications/unread-count` |
| `PATCH` | `/api/notifications/:id/read` |
| `PATCH` | `/api/notifications/read-all` |

Use these for the notifications screen inside the app.

---

## 10. Dev networking (`baseUrl`)

| Where app runs | Backend URL |
|----------------|-------------|
| Android emulator | `http://10.0.2.2:4500/api` |
| Physical phone (same Wi‑Fi) | `http://<your-pc-lan-ip>:4500/api` |

Backend must listen on `0.0.0.0` (or your LAN IP), not only `127.0.0.1`, for phone testing.

---

## 11. Testing checklist

1. Backend running with `FIREBASE_CREDENTIALS` set.
2. Log in on device/emulator.
3. Confirm `PATCH /api/settings` returns `200` after login.
4. In MongoDB, user doc has `push_tokens: ["..."]`.
5. Trigger a push event (e.g. schedule a task due in ~30 min, or send friend request).
6. **Put app in background** — reminder at due time should appear in notification shade.
7. Backend logs to watch:
   - Success: no error (push is silent on success)
   - Failure: `Push dispatch skipped: ...` or `Push dispatch failed`

### Quick manual backend test (backend dev)

If token is registered, backend team can call `dispatch_push` from Node REPL — ask backend lead.

---

## 12. Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| `Push dispatch skipped: Firebase not configured` | Backend `.env` missing admin credentials |
| `Push dispatch skipped: no registered device tokens` | Frontend never sent `push_token`, or wrong user logged in |
| `PATCH /api/settings 401` | Expired access token — re-login |
| Notification in DB but no phone banner | App was in **foreground** (add `onMessage` handler) or notification permission denied |
| `notification_inserted: 1` in logs but no push | Log does not show push count — check `push_tokens` in DB and user toggles |
| Emulator never gets token | Emulator without Google Play Services |
| FCM success but no UI | Android notification permission off for the app |

---

## 13. Security notes

| File | Commit to Git? |
|------|----------------|
| `google-services.json` (Flutter) | Usually yes (client config) |
| Firebase **admin** service account JSON | **Never** — backend `.env` only |
| FCM device tokens in API requests | OK over HTTPS in production |

---

## 14. Related docs

- [settings-api.md](./settings-api.md) — `push_token`, toggles, PATCH fields

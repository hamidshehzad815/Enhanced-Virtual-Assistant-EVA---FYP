import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../../core/constants/api_constants.dart';
import '../../data/services/storage_service.dart';

class PushNotificationService {
  static final FirebaseMessaging _fcm = FirebaseMessaging.instance;

  // Request permission (Android 13+ handles automatically, but good for iOS)
  static Future<void> requestPermission() async {
    await _fcm.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );
  }

  // Get the token and register with backend
  static Future<void> registerToken() async {
    final token = await _fcm.getToken();
    if (token == null) return;

    final accessToken = await StorageService.getAccessToken();
    if (accessToken == null) return;

    try {
      final response = await http.patch(
        Uri.parse('${AppConstants.baseUrl}/settings'),
        headers: {
          'Authorization': 'Bearer $accessToken',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({'push_token': token}),
      );
      if (response.statusCode == 200) {
        print('✅ Push token registered');
      } else {
        print('❌ Failed to register token: ${response.body}');
      }
    } catch (e) {
      print('❌ Error registering token: $e');
    }
  }

  // Remove token on logout
  static Future<void> removeToken() async {
    final token = await _fcm.getToken();
    if (token == null) return;

    final accessToken = await StorageService.getAccessToken();
    if (accessToken == null) return;

    try {
      await http.patch(
        Uri.parse('${AppConstants.baseUrl}/settings'),
        headers: {
          'Authorization': 'Bearer $accessToken',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({'remove_push_token': token}),
      );
    } catch (e) {
      print('❌ Error removing token: $e');
    }
  }

  // Listen to token refresh
  static void listenTokenRefresh() {
    _fcm.onTokenRefresh.listen((newToken) {
      registerToken();
    });
  }

  // Handle foreground messages (optional)
  static void handleForegroundMessages() {
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      // Show in-app notification (e.g., using a snackbar or a custom dialog)
      print('Foreground message: ${message.notification?.title}');
      // You can display a local notification here or show a snackbar
    });
  }

  // Handle background messages – must be top-level
  static Future<void> onBackgroundMessage(RemoteMessage message) async {
    print('Background message: ${message.notification?.title}');
  }
}
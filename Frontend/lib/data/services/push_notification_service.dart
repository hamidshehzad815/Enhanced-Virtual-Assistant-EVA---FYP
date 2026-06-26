import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../../core/constants/api_constants.dart';
import '../../data/services/storage_service.dart';

const String _androidChannelId = 'eva_high_importance';
const String _androidChannelName = 'EVA Notifications';
const String _androidChannelDescription = 'Task reminders and alerts';

final FlutterLocalNotificationsPlugin _localNotifications =
    FlutterLocalNotificationsPlugin();

bool _localNotificationsReady = false;

int _notificationId(RemoteMessage message) {
  final raw = message.messageId?.hashCode ?? message.hashCode;
  return raw.abs().remainder(0x7fffffff);
}

Future<void> _ensureLocalNotificationsReady() async {
  if (_localNotificationsReady) return;

  const androidInit = AndroidInitializationSettings('@mipmap/ic_launcher');
  const initSettings = InitializationSettings(android: androidInit);
  await _localNotifications.initialize(settings: initSettings);

  const channel = AndroidNotificationChannel(
    _androidChannelId,
    _androidChannelName,
    description: _androidChannelDescription,
    importance: Importance.max,
    playSound: true,
    enableVibration: true,
  );

  final androidPlugin = _localNotifications
      .resolvePlatformSpecificImplementation<
        AndroidFlutterLocalNotificationsPlugin
      >();
  await androidPlugin?.createNotificationChannel(channel);
  final granted = await androidPlugin?.requestNotificationsPermission();
  if (kDebugMode) {
    print('Android notification permission granted: $granted');
  }

  _localNotificationsReady = true;
}

Future<void> _showLocalNotification(RemoteMessage message) async {
  try {
    await _ensureLocalNotificationsReady();

    final notification = message.notification;
    final title = notification?.title?.trim();
    final body = notification?.body?.trim();

    if (title == null || title.isEmpty) {
      if (kDebugMode) {
        print('Push skipped: message has no notification title');
      }
      return;
    }

    await _localNotifications.show(
      id: _notificationId(message),
      title: title,
      body: body,
      notificationDetails: const NotificationDetails(
        android: AndroidNotificationDetails(
          _androidChannelId,
          _androidChannelName,
          channelDescription: _androidChannelDescription,
          importance: Importance.max,
          priority: Priority.high,
          icon: '@mipmap/ic_launcher',
          playSound: true,
          enableVibration: true,
          visibility: NotificationVisibility.public,
        ),
      ),
      payload: message.data.isNotEmpty ? jsonEncode(message.data) : null,
    );

    if (kDebugMode) {
      print('Local notification shown: $title');
    }
  } catch (e, st) {
    if (kDebugMode) {
      print('Failed to show local notification: $e');
      print(st);
    }
  }
}

@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  // Firebase already initialized in main.dart – no need to init again
  await _showLocalNotification(message);
}

class PushNotificationService {
  static final FirebaseMessaging _fcm = FirebaseMessaging.instance;
  static bool _listenersRegistered = false;

  /// Call once from main() before runApp.
  static Future<void> setup() async {
    await _ensureLocalNotificationsReady();
    await _fcm.setForegroundNotificationPresentationOptions(
      alert: true,
      badge: true,
      sound: true,
    );
  }

  static Future<void> init() async {
    await setup();
    await requestPermission();
    if (!_listenersRegistered) {
      listenTokenRefresh();
      handleForegroundMessages();
      _listenersRegistered = true;
    }
    await registerToken();
  }

  static Future<void> requestPermission() async {
    await _fcm.requestPermission(alert: true, badge: true, sound: true);
  }

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
      if (kDebugMode) {
        if (response.statusCode == 200) {
          print('Push token registered');
        } else {
          print('Failed to register token: ${response.body}');
        }
      }
    } catch (e) {
      if (kDebugMode) {
        print('Error registering token: $e');
      }
    }
  }

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
      if (kDebugMode) {
        print('Error removing token: $e');
      }
    }
  }

  static void listenTokenRefresh() {
    _fcm.onTokenRefresh.listen((_) {
      registerToken();
    });
  }

  static void handleForegroundMessages() {
    FirebaseMessaging.onMessage.listen((RemoteMessage message) async {
      await _showLocalNotification(message);
    });
  }
}

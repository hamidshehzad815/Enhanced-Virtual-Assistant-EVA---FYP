// lib/data/services/notification_service.dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../../core/constants/api_constants.dart';
import '../models/app_notification.dart';

class NotificationListResult {
  final List<AppNotification> notifications;
  final int unreadCount;
  NotificationListResult(this.notifications, this.unreadCount);
}

class NotificationService {
  Future<NotificationListResult> getNotifications(
    String token, {
    int limit = 20,
    int skip = 0,
  }) async {
    final response = await http.get(
      Uri.parse(
        '${AppConstants.baseUrl}/notifications?limit=$limit&skip=$skip',
      ),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode == 200) {
      final json = jsonDecode(response.body);
      final data = json['data'] ?? {};
      final list = (data['notifications'] as List? ?? [])
          .map((n) => AppNotification.fromJson(n as Map<String, dynamic>))
          .toList();
      final unread = (data['unread_count'] as num?)?.toInt() ?? 0;
      return NotificationListResult(list, unread);
    }
    throw Exception('Failed to load notifications: ${response.statusCode}');
  }

  Future<int> getUnreadCount(String token) async {
    final response = await http.get(
      Uri.parse('${AppConstants.baseUrl}/notifications/unread-count'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode == 200) {
      final json = jsonDecode(response.body);
      return (json['data']?['unread_count'] as num?)?.toInt() ?? 0;
    }
    throw Exception('Failed to load unread count: ${response.statusCode}');
  }

  Future<void> markRead(String token, String id) async {
    final response = await http.patch(
      Uri.parse('${AppConstants.baseUrl}/notifications/$id/read'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to mark notification read: ${response.statusCode}');
    }
  }

  Future<void> markAllRead(String token) async {
    final response = await http.patch(
      Uri.parse('${AppConstants.baseUrl}/notifications/read-all'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to mark all read: ${response.statusCode}');
    }
  }

  Future<void> deleteNotification(String token, String id) async {
    final response = await http.delete(
      Uri.parse('${AppConstants.baseUrl}/notifications/$id'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode != 200 && response.statusCode != 204) {
      throw Exception('Failed to delete notification: ${response.statusCode}');
    }
  }

  /// Accept/reject a task collaboration invite (Tasks endpoint).
  /// Returns whether the invite had already been responded to.
  Future<bool> respondCollaboration(
    String token,
    String taskId,
    String action, // 'accept' | 'reject'
  ) async {
    return _respondInvite(
      token,
      '${AppConstants.baseUrl}/tasks/$taskId/collaborators/respond',
      action,
    );
  }

  /// Accept/reject a learning-plan collaboration invite (Learning endpoint).
  /// Returns whether the invite had already been responded to.
  Future<bool> respondLearningCollaboration(
    String token,
    String goalId,
    String action, // 'accept' | 'reject'
  ) async {
    return _respondInvite(
      token,
      '${AppConstants.baseUrl}/learning/$goalId/collaborators/respond',
      action,
    );
  }

  Future<bool> _respondInvite(String token, String url, String action) async {
    final response = await http.post(
      Uri.parse(url),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({'action': action}),
    );
    if (response.statusCode == 200) {
      final json = jsonDecode(response.body);
      return json['data']?['already_responded'] == true;
    }
    final error = jsonDecode(response.body);
    throw Exception(error['message'] ?? 'Failed to respond to invite');
  }
}

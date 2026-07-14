// lib/data/repositories/notification_repository.dart
import '../services/notification_service.dart';
import '../services/storage_service.dart';

class NotificationRepository {
  final NotificationService _service;

  NotificationRepository(this._service);

  Future<String> _getToken() async {
    final token = await StorageService.getAccessToken();
    if (token == null) throw Exception('No access token');
    return token;
  }

  Future<NotificationListResult> getNotifications({
    int limit = 20,
    int skip = 0,
  }) async {
    final token = await _getToken();
    return _service.getNotifications(token, limit: limit, skip: skip);
  }

  Future<int> getUnreadCount() async {
    final token = await _getToken();
    return _service.getUnreadCount(token);
  }

  Future<void> markRead(String id) async {
    final token = await _getToken();
    return _service.markRead(token, id);
  }

  Future<void> markAllRead() async {
    final token = await _getToken();
    return _service.markAllRead(token);
  }

  Future<void> deleteNotification(String id) async {
    final token = await _getToken();
    return _service.deleteNotification(token, id);
  }

  Future<bool> respondCollaboration(String taskId, String action) async {
    final token = await _getToken();
    return _service.respondCollaboration(token, taskId, action);
  }
}

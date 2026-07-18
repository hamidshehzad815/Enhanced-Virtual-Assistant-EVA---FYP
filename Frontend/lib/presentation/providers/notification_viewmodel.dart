// lib/presentation/providers/notification_viewmodel.dart
import 'dart:async';
import 'package:flutter/material.dart';
import '../../data/models/app_notification.dart';
import '../../data/repositories/notification_repository.dart';

class NotificationViewModel extends ChangeNotifier with WidgetsBindingObserver {
  final NotificationRepository _repository;

  static const Duration _pollInterval = Duration(seconds: 45);

  List<AppNotification> _notifications = [];
  int _unreadCount = 0;
  bool _isLoading = false;
  String? _error;
  Timer? _pollTimer;

  NotificationViewModel(this._repository) {
    WidgetsBinding.instance.addObserver(this);
    startPolling();
  }

  List<AppNotification> get notifications => _notifications;
  int get unreadCount => _unreadCount;
  bool get isLoading => _isLoading;
  String? get error => _error;

  // ─── Polling (foreground only) ───────────────────────────────────────────
  void startPolling() {
    _pollTimer?.cancel();
    refreshUnreadCount();
    _pollTimer = Timer.periodic(_pollInterval, (_) => refreshUnreadCount());
  }

  void stopPolling() {
    _pollTimer?.cancel();
    _pollTimer = null;
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      startPolling();
    } else {
      stopPolling();
    }
  }

  Future<void> refreshUnreadCount() async {
    try {
      final count = await _repository.getUnreadCount();
      if (count != _unreadCount) {
        _unreadCount = count;
        notifyListeners();
      }
    } catch (_) {
      // Polling failures stay silent — no need to spam the UI.
    }
  }

  // ─── Full list (loaded when the panel opens) ─────────────────────────────
  Future<void> loadNotifications() async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      final result = await _repository.getNotifications();
      _notifications = result.notifications;
      _unreadCount = result.unreadCount;
    } catch (e) {
      _error = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> markRead(String id) async {
    final idx = _notifications.indexWhere((n) => n.id == id);
    if (idx == -1 || _notifications[idx].isRead) return;
    try {
      await _repository.markRead(id);
      _notifications[idx] = _notifications[idx].copyWith(isRead: true);
      if (_unreadCount > 0) _unreadCount--;
      notifyListeners();
    } catch (_) {
      // ignore — keep it unread if the call failed
    }
  }

  Future<void> deleteNotification(String id) async {
    final idx = _notifications.indexWhere((n) => n.id == id);
    if (idx == -1) return;

    final notification = _notifications[idx];
    final wasUnread = !notification.isRead;
    _notifications.removeAt(idx);
    if (wasUnread && _unreadCount > 0) {
      _unreadCount--;
    }
    notifyListeners();

    try {
      await _repository.deleteNotification(id);
      _error = null;
    } catch (e) {
      _notifications.insert(idx, notification);
      if (wasUnread) {
        _unreadCount++;
      }
      _error = e.toString();
      notifyListeners();
      throw Exception('Failed to delete notification');
    }
  }

  Future<void> markAllRead() async {
    try {
      await _repository.markAllRead();
      _notifications =
          _notifications.map((n) => n.copyWith(isRead: true)).toList();
      _unreadCount = 0;
      notifyListeners();
    } catch (e) {
      _error = e.toString();
      notifyListeners();
    }
  }

  /// Accept/reject a collaboration invite.
  /// Returns 'accepted' | 'rejected' | 'already'.
  Future<String> respondToInvite(AppNotification n, String action) async {
    final referenceId = n.referenceId;
    if (referenceId == null || referenceId.isEmpty) {
      throw Exception('This invite has no reference');
    }

    // Learning-plan invites and task invites use different endpoints.
    final isLearning = n.type == 'learning_collaboration_invite' ||
        n.referenceType == 'learning_goal';
    final already = isLearning
        ? await _repository.respondLearningCollaboration(referenceId, action)
        : await _repository.respondCollaboration(referenceId, action);

    final idx = _notifications.indexWhere((x) => x.id == n.id);
    if (idx != -1) {
      final wasUnread = !_notifications[idx].isRead;
      _notifications[idx] = _notifications[idx].copyWith(
        isRead: true,
        actionTaken: action == 'accept' ? 'accepted' : 'rejected',
      );
      if (wasUnread && _unreadCount > 0) _unreadCount--;
    }
    // Best-effort: also mark the invite notification read server-side.
    try {
      await _repository.markRead(n.id);
    } catch (_) {}

    notifyListeners();
    return already ? 'already' : (action == 'accept' ? 'accepted' : 'rejected');
  }

  @override
  void dispose() {
    stopPolling();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }
}

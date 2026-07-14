import 'package:flutter/foundation.dart';
import '../../data/models/setting_model.dart';
import '../../data/repositories/settings_repository.dart';
import '../../data/services/storage_service.dart';
import '../../data/services/auth_service.dart';
import '../../data/services/push_notification_service.dart';
import '../../data/repositories/integrations_repository.dart';

class SettingsViewModel extends ChangeNotifier {
  final SettingsRepository _repository;
  final IntegrationsRepository _integrationsRepository;

  SettingsModel _settings = SettingsModel();
  String _searchQuery = '';
  bool _isSaving = false;
  bool _isLoading = false;
  String? _error;
  bool _googleCalendarConnected = false;

  SettingsViewModel({
    SettingsRepository? repository,
    IntegrationsRepository? integrationsRepository,
  })  : _repository = repository ?? SettingsRepository(),
        _integrationsRepository = integrationsRepository ?? IntegrationsRepository();

  // Getters
  SettingsModel get settings => _settings;
  String get searchQuery => _searchQuery;
  bool get isSaving => _isSaving;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get googleCalendarConnected => _googleCalendarConnected;

  void updateSearchQuery(String query) {
    _searchQuery = query.toLowerCase();
    notifyListeners();
  }

  void clearSearch() {
    _searchQuery = '';
    notifyListeners();
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }

  // ----- Main settings -----
  Future<void> loadSettings() async {
    try {
      _isLoading = true;
      _error = null;
      notifyListeners();

      final token = await StorageService.getAccessToken();
      if (token == null) throw Exception('Not authenticated');

      final response = await _repository.getSettings(token);
      _settings = SettingsModel.fromJson(response);
      try {
        _googleCalendarConnected =
            await _integrationsRepository.isGoogleCalendarConnected(token);
      } catch (e) {
        debugPrint('Integrations load error: $e');
        _googleCalendarConnected = false;
      }
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _isLoading = false;
      _error = e.toString();
      notifyListeners();
      debugPrint('Settings Load Error: $e');
    }
  }

  // Core update method with rollback
  Future<void> _safeUpdate({
    required SettingsModel newSettings,
    required Map<String, dynamic> apiBody,
  }) async {
    final oldSettings = _settings;
    _settings = newSettings;
    notifyListeners();

    try {
      final token = await StorageService.getAccessToken();
      if (token == null) throw Exception('Not authenticated');

      await _repository.updateSettings(token, apiBody);
      // Success – already updated UI
    } catch (e) {
      // Rollback
      _settings = oldSettings;
      _error = e.toString();
      notifyListeners();
      rethrow;
    }
  }

  // Individual toggles (each with rollback)
  Future<void> updateNotificationsEnabled(bool value) async {
    await _safeUpdate(
      newSettings: _settings.copyWith(notificationsEnabled: value),
      apiBody: {'notifications_enabled': value},
    );
  }

  Future<void> updatePushNotificationsEnabled(bool value) async {
    await _safeUpdate(
      newSettings: _settings.copyWith(pushNotificationsEnabled: value),
      apiBody: {'push_notifications_enabled': value},
    );
  }

  Future<void> updateEmailNotificationsEnabled(bool value) async {
    await _safeUpdate(
      newSettings: _settings.copyWith(emailNotificationsEnabled: value),
      apiBody: {'email_notifications_enabled': value},
    );
  }

  Future<void> updateGoogleCalendarSync(bool value) async {
    final token = await StorageService.getAccessToken();
    if (token == null) throw Exception('Not authenticated');

    if (value) {
      final alreadyConnected =
          _googleCalendarConnected ||
          await _integrationsRepository.isGoogleCalendarConnected(token);

      if (!alreadyConnected) {
        final oldSettings = _settings;
        _settings = _settings.copyWith(googleCalendarSyncEnabled: true);
        _isSaving = true;
        notifyListeners();

        try {
          await _integrationsRepository.connectGoogleCalendar(token);
          _googleCalendarConnected = true;
          await loadSettings();
        } catch (e) {
          _settings = oldSettings;
          _error = e.toString();
          notifyListeners();
          rethrow;
        } finally {
          _isSaving = false;
          notifyListeners();
        }
        return;
      }
    }

    await _safeUpdate(
      newSettings: _settings.copyWith(googleCalendarSyncEnabled: value),
      apiBody: {'google_calendar_sync_enabled': value},
    );

    if (!value) {
      _googleCalendarConnected =
          await _integrationsRepository.isGoogleCalendarConnected(token);
      notifyListeners();
    }
  }

  Future<void> updateBehaviorAnalytics(bool value) async {
    await _safeUpdate(
      newSettings: _settings.copyWith(behavioralAnalyticsEnabled: value),
      apiBody: {'behavioral_analytics_enabled': value},
    );
  }

  Future<void> updateAllowFriendRequests(bool value) async {
    await _safeUpdate(
      newSettings: _settings.copyWith(allowFriendRequests: value),
      apiBody: {'allow_friend_requests': value},
    );
  }

  Future<void> updateQuietHoursEnabled(bool value) async {
    await _safeUpdate(
      newSettings: _settings.copyWith(quietHoursEnabled: value),
      apiBody: {'quiet_hours_enabled': value},
    );
  }

  // Update whole quiet hours list
  Future<void> updateQuietHours(List<QuietHourInterval> quietHours) async {
    await _safeUpdate(
      newSettings: _settings.copyWith(quietHours: quietHours),
      apiBody: {'quiet_hours': quietHours.map((e) => e.toJson()).toList()},
    );
  }

  // Update a single numeric value
  Future<void> updateDefaultReminderMinutes(int minutes) async {
    await _safeUpdate(
      newSettings: _settings.copyWith(defaultReminderMinutes: minutes),
      apiBody: {'default_reminder_minutes': minutes},
    );
  }

  Future<void> updateDefaultTaskDuration(int minutes) async {
    await _safeUpdate(
      newSettings: _settings.copyWith(defaultTaskDuration: minutes),
      apiBody: {'default_task_duration': minutes},
    );
  }

  Future<void> updateDefaultLearningReminderMinutes(int minutes) async {
    await _safeUpdate(
      newSettings: _settings.copyWith(defaultLearningReminderMinutes: minutes),
      apiBody: {'default_learning_reminder_minutes': minutes},
    );
  }

  // ----- Learning Schedules CRUD -----
  Future<void> createLearningSchedule(
    String label,
    List<ScheduleSlot> slots,
  ) async {
    try {
      _isSaving = true;
      _error = null;
      notifyListeners();

      final token = await StorageService.getAccessToken();
      if (token == null) throw Exception('Not authenticated');

      final slotsJson = slots.map((s) => s.toJson()).toList();
      final response = await _repository.createLearningSchedule(
        token,
        label,
        slotsJson,
      );

      // Update local schedules from response
      final updatedSchedules =
          (response['data']['preferred_learning_schedules'] as List)
              .map((e) => LearningSchedule.fromJson(e))
              .toList();
      _settings = _settings.copyWith(learningSchedules: updatedSchedules);

      _isSaving = false;
      notifyListeners();
    } catch (e) {
      _isSaving = false;
      _error = e.toString();
      notifyListeners();
      rethrow;
    }
  }

  Future<void> updateLearningSchedule(
    String id, {
    String? label,
    List<ScheduleSlot>? slots,
  }) async {
    try {
      _isSaving = true;
      _error = null;
      notifyListeners();

      final token = await StorageService.getAccessToken();
      if (token == null) throw Exception('Not authenticated');

      final body = <String, dynamic>{};
      if (label != null) body['label'] = label;
      if (slots != null) body['slots'] = slots.map((s) => s.toJson()).toList();

      final response = await _repository.updateLearningSchedule(
        token,
        id,
        body,
      );

      final updatedSchedules =
          (response['data']['preferred_learning_schedules'] as List)
              .map((e) => LearningSchedule.fromJson(e))
              .toList();
      _settings = _settings.copyWith(learningSchedules: updatedSchedules);

      _isSaving = false;
      notifyListeners();
    } catch (e) {
      _isSaving = false;
      _error = e.toString();
      notifyListeners();
      rethrow;
    }
  }

  Future<void> deleteLearningSchedule(String id) async {
    try {
      _isSaving = true;
      _error = null;
      notifyListeners();

      final token = await StorageService.getAccessToken();
      if (token == null) throw Exception('Not authenticated');

      final response = await _repository.deleteLearningSchedule(token, id);

      final updatedSchedules =
          (response['data']['preferred_learning_schedules'] as List)
              .map((e) => LearningSchedule.fromJson(e))
              .toList();
      _settings = _settings.copyWith(learningSchedules: updatedSchedules);

      _isSaving = false;
      notifyListeners();
    } catch (e) {
      _isSaving = false;
      _error = e.toString();
      notifyListeners();
      rethrow;
    }
  }

  // ----- Push token management -----
  Future<void> registerPushToken(String token) async {
    try {
      final authToken = await StorageService.getAccessToken();
      if (authToken == null) throw Exception('Not authenticated');
      await _repository.updateSettings(authToken, {'push_token': token});
    } catch (e) {
      debugPrint('Push token registration failed: $e');
    }
  }

  Future<void> removePushToken(String token) async {
    try {
      final authToken = await StorageService.getAccessToken();
      if (authToken == null) throw Exception('Not authenticated');
      await _repository.updateSettings(authToken, {'remove_push_token': token});
    } catch (e) {
      debugPrint('Push token removal failed: $e');
    }
  }

  Future<void> updateTheme(String theme) async {
    final oldSettings = _settings;
    _settings = _settings.copyWith(theme: theme);
    notifyListeners();
    try {
      final token = await StorageService.getAccessToken();
      if (token == null) throw Exception('Not authenticated');
      await _repository.updateSettings(token, {'theme': theme});
    } catch (e) {
      _settings = oldSettings;
      _error = e.toString();
      notifyListeners();
      rethrow;
    }
  }

  void Function()? onLoggedOut;

  // ----- Logout & Delete Account -----
  Future<void> logout() async {
    await PushNotificationService.removeToken();
    try {
      final token = await StorageService.getAccessToken();
      if (token != null) {
        await AuthService.logoutUser(token);
      }
    } catch (e) {
      debugPrint('Logout API error: $e');
    } finally {
      await StorageService.clearTokens();
      onLoggedOut?.call();
    }
  }

  Future<void> deleteAccount() async {
    try {
      // Call DELETE /api/user (adjust endpoint as needed)
      // await _userService.deleteAccount(token);
      await StorageService.clearTokens();
      onLoggedOut?.call();
      notifyListeners();
    } catch (e) {
      _error = e.toString();
      notifyListeners();
      rethrow;
    }
  }
}

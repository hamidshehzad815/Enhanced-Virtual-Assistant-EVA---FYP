import '../services/settings_service.dart';

abstract class ISettingsRepository {
  // Main settings
  Future<Map<String, dynamic>> getSettings(String token);
  Future<Map<String, dynamic>> updateSettings(String token, Map<String, dynamic> body);

  // Learning schedules
  Future<Map<String, dynamic>> getLearningSchedules(String token);
  Future<Map<String, dynamic>> createLearningSchedule(String token, String label, List<Map<String, dynamic>> slots);
  Future<Map<String, dynamic>> updateLearningSchedule(String token, String scheduleId, Map<String, dynamic> body);
  Future<Map<String, dynamic>> deleteLearningSchedule(String token, String scheduleId);
}

class SettingsRepository implements ISettingsRepository {
  final SettingsService _settingsService;

  SettingsRepository({SettingsService? settingsService})
      : _settingsService = settingsService ?? SettingsService();

  @override
  Future<Map<String, dynamic>> getSettings(String token) =>
      _settingsService.getSettings(token);

  @override
  Future<Map<String, dynamic>> updateSettings(String token, Map<String, dynamic> body) =>
      _settingsService.updateSettings(token, body);

  @override
  Future<Map<String, dynamic>> getLearningSchedules(String token) =>
      _settingsService.getLearningSchedules(token);

  @override
  Future<Map<String, dynamic>> createLearningSchedule(String token, String label, List<Map<String, dynamic>> slots) =>
      _settingsService.createLearningSchedule(token, label, slots);

  @override
  Future<Map<String, dynamic>> updateLearningSchedule(String token, String scheduleId, Map<String, dynamic> body) =>
      _settingsService.updateLearningSchedule(token, scheduleId, body);

  @override
  Future<Map<String, dynamic>> deleteLearningSchedule(String token, String scheduleId) =>
      _settingsService.deleteLearningSchedule(token, scheduleId);
}
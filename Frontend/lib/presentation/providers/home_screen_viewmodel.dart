import 'package:flutter/foundation.dart';
import '../../data/services/storage_service.dart';
import '../../data/models/user_profile.dart';
import '../../data/models/task_data.dart';
import '../../data/models/focus_data.dart';
import '../../data/models/schedule_item.dart';
import '../../data/repositories/home_screen_repository.dart';

class HomeScreenViewModel extends ChangeNotifier {
  final HomeScreenRepository _repository;

  UserProfile? _userProfile;
  TaskData? _upcomingTask;
  List<FocusData> _focusList = [];
  List<ScheduleItem> _schedule = [];

  bool _isLoading = false;
  String? _error;

  HomeScreenViewModel({HomeScreenRepository? repository})
    : _repository = repository ?? HomeScreenRepository();

  // Getters
  UserProfile? get userProfile => _userProfile;
  TaskData? get upcomingTask => _upcomingTask;
  List<FocusData> get focusList => List.unmodifiable(_focusList);
  List<ScheduleItem> get schedule => List.unmodifiable(_schedule);
  bool get isLoading => _isLoading;
  String? get error => _error;

  Future<void> loadHomeScreenData() async {
    _setLoading(true);
    _clearError();

    try {
      final token = await StorageService.getAccessToken();

      if (token == null) {
        throw Exception("Token not found");
      }

      final dashboard = await _repository.getDashboard(token);
      debugPrint(dashboard.toString());

      final data = dashboard['data'];

      final progress = data['daily_progress'];

      _userProfile = UserProfile(
        name: 'Areej',
        userInitial: 'A',
        dailyProgress: (progress['completion_percentage'] ?? 0) / 100,
      );

      _upcomingTask = data['up_next'] != null
          ? TaskData.fromJson(data['up_next'])
          : null;

      _focusList = (data['learning'] as List)
          .map((e) => FocusData.fromJson(e))
          .toList();

      _schedule = (data['today_schedule'] as List)
          .map((e) => ScheduleItem.fromJson(e))
          .toList();

      notifyListeners();
    } catch (e) {
      _setError('Failed to load dashboard: $e');
    } finally {
      _setLoading(false);
    }
  }

  void _setLoading(bool value) {
    _isLoading = value;
    notifyListeners();
  }

  void _setError(String? value) {
    _error = value;
    notifyListeners();
  }

  void _clearError() {
    _error = null;
  }
}

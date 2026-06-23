import 'package:flutter/foundation.dart';
import '../../data/services/storage_service.dart';
import '../../data/models/user_profile.dart';
import '../../data/models/up_next_data.dart';
import '../../data/models/focus_data.dart';
import '../../data/models/schedule_item.dart';
import '../../data/models/daily_progress.dart';
import '../../data/repositories/home_screen_repository.dart';

class HomeScreenViewModel extends ChangeNotifier {
  final HomeScreenRepository _repository;

  UserProfile? _userProfile;
  DailyProgress? _dailyProgress;
  UpNextData? _upcomingTask;
  List<FocusData> _focusList = [];
  List<ScheduleItem> _schedule = [];

  bool _isLoading = false;
  String? _error;

  HomeScreenViewModel({HomeScreenRepository? repository})
    : _repository = repository ?? HomeScreenRepository();

  // Getters
  UserProfile? get userProfile => _userProfile;
  DailyProgress? get dailyProgress => _dailyProgress;
  UpNextData? get upcomingTask => _upcomingTask;
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

      final profileData = await _repository.getProfile(token);

      final dashboardData = await _repository.getDashboard(token);

      _userProfile = UserProfile.fromJson(profileData['data']['user']);

      final dashboard = dashboardData['data'];
      _dailyProgress = DailyProgress.fromJson(dashboard['daily_progress']);

      _upcomingTask = dashboard['up_next'] != null
          ? UpNextData.fromJson(dashboard['up_next'])
          : null;

      _focusList = (dashboard['learning'] as List)
          .map((e) => FocusData.fromJson(e))
          .toList();

      _schedule = (dashboard['today_schedule'] as List)
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

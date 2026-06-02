import 'package:flutter/foundation.dart';
import '../../data/models/user_profile.dart';
import '../../data/models/task_data.dart';
import '../../data/models/focus_data.dart';
import '../../data/models/schedule_item.dart';
import '../../data/repositories/home_screen_repository.dart';

/// HomeScreen ViewModel - Business logic & state management
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

  /// Load all home screen data
  Future<void> loadHomeScreenData() async {
    _setLoading(true);
    _clearError();

    try {
      final results = await Future.wait([
        _repository.getUserProfile(),
        _repository.getUpcomingTask(),
        _repository.getCurrentFocusList(),   
        _repository.getSchedule(),
      ]);

      _userProfile = results[0] as UserProfile;
      _upcomingTask = results[1] as TaskData;
      _focusList = results[2] as List<FocusData>;
      _schedule = results[3] as List<ScheduleItem>;

      notifyListeners();
    } catch (e) {
      _setError('Failed to load home screen data: $e');
    } finally {
      _setLoading(false);
    }
  }

  /// Load user profile separately
  Future<void> loadUserProfile() async {
    try {
      _userProfile = await _repository.getUserProfile();
      notifyListeners();
    } catch (e) {
      _setError('Failed to load user profile: $e');
    }
  }

  /// Load upcoming task separately
  Future<void> loadUpcomingTask() async {
    try {
      _upcomingTask = await _repository.getUpcomingTask();
      notifyListeners();
    } catch (e) {
      _setError('Failed to load upcoming task: $e');
    }
  }

  /// Load focus list separately
  Future<void> loadFocusList() async {
    try {
      _focusList = await _repository.getCurrentFocusList();
      notifyListeners();
    } catch (e) {
      _setError('Failed to load focus list: $e');
    }
  }

  /// Load schedule separately
  Future<void> loadSchedule() async {
    try {
      _schedule = await _repository.getSchedule();
      notifyListeners();
    } catch (e) {
      _setError('Failed to load schedule: $e');
    }
  }

  // Private helpers
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
// lib/presentation/providers/analytics_viewmodel.dart
import 'package:flutter/material.dart';
import '../../data/models/analytics_model.dart';
import '../../data/repositories/analytics_repository.dart';

class AnalyticsViewModel extends ChangeNotifier {
  final AnalyticsRepository _repository;

  AnalyticsDashboard? _dashboard;
  bool _isLoading = false;
  String? _error;
  int _selectedDays = 30;

  AnalyticsViewModel(this._repository);

  AnalyticsDashboard? get dashboard => _dashboard;
  bool get isLoading => _isLoading;
  String? get error => _error;
  int get selectedDays => _selectedDays;

  void setDays(int days) {
    if (_selectedDays == days) return;
    _selectedDays = days;
    loadDashboard();
  }

  Future<void> loadDashboard() async {
    _setLoading(true);
    try {
      _dashboard = await _repository.getDashboard(days: _selectedDays);
      _error = null;
    } catch (e) {
      print('🔴 Analytics parse error: $e');
      _error = 'Failed to load analytics. Please try again.';
      _dashboard = null;
    } finally {
      _setLoading(false);
    }
  }

  void _setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }
}

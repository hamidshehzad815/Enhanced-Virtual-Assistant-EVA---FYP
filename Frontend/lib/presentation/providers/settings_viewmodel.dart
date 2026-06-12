import 'package:flutter/foundation.dart';
import '../../data/models/setting_model.dart';

class SettingsViewModel extends ChangeNotifier {
  late SettingsModel _settings;
  String _searchQuery = '';
  bool _isSaving = false;

  SettingsViewModel() {
    _loadDefaults();
  }

  SettingsModel get settings => _settings;
  String get searchQuery => _searchQuery;
  bool get isSaving => _isSaving;
  bool get hasSearch => _searchQuery.isNotEmpty;

  void updateSearchQuery(String query) {
    _searchQuery = query.toLowerCase();
    notifyListeners();
  }


  void clearSearch() {
    _searchQuery = '';
    notifyListeners();
  }

  Future<void> saveSettings() async {
    _isSaving = true;
    notifyListeners();

    await Future.delayed(const Duration(milliseconds: 350));

    _isSaving = false;
    notifyListeners();
  }

  void _loadDefaults() {
    _settings = SettingsModel();
  }
}

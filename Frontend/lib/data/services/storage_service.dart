import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

class StorageService {
  static const FlutterSecureStorage _storage = FlutterSecureStorage();

  static Future<void> saveAccessToken(String token) async {
    await _storage.write(key: 'access_token', value: token);
  }

  static Future<void> saveRefreshToken(String token) async {
    await _storage.write(key: 'refresh_token', value: token);
  }

  static Future<String?> getAccessToken() async {
    return await _storage.read(key: 'access_token');
  }

  static Future<void> clearTokens() async {
    await _storage.delete(key: 'access_token');

    await _storage.delete(key: 'refresh_token');
  }

static const String _selectedRoadmapLanguageKey = 'selected_roadmap_language';

static Future<void> saveSelectedRoadmapLanguage(String languageKey) async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.setString(_selectedRoadmapLanguageKey, languageKey);
}

static Future<String?> getSelectedRoadmapLanguage() async {
  final prefs = await SharedPreferences.getInstance();
  return prefs.getString(_selectedRoadmapLanguageKey);
}
}

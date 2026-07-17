import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

class StorageService {
  static const FlutterSecureStorage _storage = FlutterSecureStorage();

  // In-memory fallback — used when "remember me" is OFF.
  static String? _memoryAccessToken;
  static String? _memoryRefreshToken;

  static Future<void> saveAccessToken(String token, {bool persist = true}) async {
    if (persist) {
      _memoryAccessToken = null;
      await _storage.write(key: 'access_token', value: token);
    } else {
      _memoryAccessToken = token;
      await _storage.delete(key: 'access_token');
    }
  }

  static Future<void> saveRefreshToken(String token, {bool persist = true}) async {
    if (persist) {
      _memoryRefreshToken = null;
      await _storage.write(key: 'refresh_token', value: token);
    } else {
      _memoryRefreshToken = token;
      await _storage.delete(key: 'refresh_token');
    }
  }

  static Future<String?> getAccessToken() async {
    if (_memoryAccessToken != null) return _memoryAccessToken;
    return await _storage.read(key: 'access_token');
  }

  static Future<String?> getRefreshToken() async {
    if (_memoryRefreshToken != null) return _memoryRefreshToken;
    return await _storage.read(key: 'refresh_token');
  }

  static Future<void> clearTokens() async {
    _memoryAccessToken = null;
    _memoryRefreshToken = null;
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
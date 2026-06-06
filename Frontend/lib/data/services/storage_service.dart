import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class StorageService {
  static const FlutterSecureStorage _storage =
      FlutterSecureStorage();

  static Future<void> saveAccessToken(
    String token,
  ) async {
    await _storage.write(
      key: 'access_token',
      value: token,
    );
  }

  static Future<void> saveRefreshToken(
    String token,
  ) async {
    await _storage.write(
      key: 'refresh_token',
      value: token,
    );
  }

  static Future<String?> getAccessToken() async {
    return await _storage.read(
      key: 'access_token',
    );
  }

  static Future<void> clearTokens() async {
    await _storage.delete(
      key: 'access_token',
    );

    await _storage.delete(
      key: 'refresh_token',
    );
  }
}
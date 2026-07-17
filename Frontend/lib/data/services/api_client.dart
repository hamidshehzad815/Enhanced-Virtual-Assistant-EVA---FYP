import 'dart:convert';
import 'package:http/http.dart' as http;
import '../../core/constants/api_constants.dart';
import 'storage_service.dart';

class SessionExpiredException implements Exception {
  final String message;
  const SessionExpiredException([this.message = 'Session expired']);
  @override
  String toString() => message;
}

/// Shared authenticated HTTP helpers with refresh-on-401.
class ApiClient {
  /// Attempt to refresh access/refresh tokens. Returns true on success.
  static Future<bool> refreshSession() async {
    final refreshToken = await StorageService.getRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) return false;

    try {
      final response = await http
          .post(
            Uri.parse('${AppConstants.baseUrl}/auth/refresh'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'refresh_token': refreshToken}),
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode != 200) {
        return false;
      }

      final data = response.body.isNotEmpty ? jsonDecode(response.body) : {};
      final access = data['data']?['tokens']?['access_token'] as String?;
      final refresh = data['data']?['tokens']?['refresh_token'] as String?;
      if (access == null || access.isEmpty) return false;

      await StorageService.saveAccessToken(access);
      if (refresh != null && refresh.isNotEmpty) {
        await StorageService.saveRefreshToken(refresh);
      }
      return true;
    } catch (_) {
      return false;
    }
  }

  /// Validate stored session. Tries refresh when needed.
  /// On auth failure clears tokens and returns false.
  static Future<bool> ensureValidSession() async {
    final access = await StorageService.getAccessToken();
    if (access == null || access.isEmpty) {
      await StorageService.clearTokens();
      return false;
    }

    try {
      final probe = await http
          .get(
            Uri.parse('${AppConstants.baseUrl}/profile'),
            headers: {'Authorization': 'Bearer $access'},
          )
          .timeout(const Duration(seconds: 15));

      if (probe.statusCode == 200) return true;

      if (probe.statusCode == 401) {
        final refreshed = await refreshSession();
        if (!refreshed) {
          await StorageService.clearTokens();
          return false;
        }
        final retryToken = await StorageService.getAccessToken();
        if (retryToken == null) {
          await StorageService.clearTokens();
          return false;
        }
        final retry = await http
            .get(
              Uri.parse('${AppConstants.baseUrl}/profile'),
              headers: {'Authorization': 'Bearer $retryToken'},
            )
            .timeout(const Duration(seconds: 15));
        if (retry.statusCode == 200) return true;
      }

      await StorageService.clearTokens();
      return false;
    } catch (_) {
      // Network errors: keep tokens so offline reopen isn't a forced logout.
      return true;
    }
  }

  static Future<http.Response> get(
    Uri url, {
    Map<String, String>? headers,
  }) async {
    return _send(() async {
      final token = await StorageService.getAccessToken();
      if (token == null) throw const SessionExpiredException();
      return http.get(
        url,
        headers: {
          ...?headers,
          'Authorization': 'Bearer $token',
        },
      );
    });
  }

  static Future<http.Response> _send(
    Future<http.Response> Function() request,
  ) async {
    var response = await request();
    if (response.statusCode != 401) return response;

    final refreshed = await refreshSession();
    if (!refreshed) {
      await StorageService.clearTokens();
      throw const SessionExpiredException();
    }
    response = await request();
    if (response.statusCode == 401) {
      await StorageService.clearTokens();
      throw const SessionExpiredException();
    }
    return response;
  }
}

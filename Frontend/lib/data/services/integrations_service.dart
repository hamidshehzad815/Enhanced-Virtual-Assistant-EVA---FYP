import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../core/constants/api_constants.dart';

class IntegrationsService {
  Future<Map<String, dynamic>> getIntegrations(String token) async {
    final response = await http.get(
      Uri.parse('${AppConstants.baseUrl}/integrations'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
    );

    final body = response.body.isNotEmpty ? jsonDecode(response.body) : {};
    if (response.statusCode == 200) {
      return body;
    }
    throw Exception(body['message'] ?? 'Failed to load integrations');
  }

  Future<Map<String, dynamic>> connectGoogleCalendar(
    String token, {
    required String accessToken,
    String? serverAuthCode,
    String? refreshToken,
    String calendarId = 'primary',
    String? scope,
  }) async {
    final payload = <String, dynamic>{
      'calendar_id': calendarId,
      if (scope != null && scope.isNotEmpty) 'scope': scope,
    };

    if (serverAuthCode != null && serverAuthCode.isNotEmpty) {
      payload['server_auth_code'] = serverAuthCode;
      payload['access_token'] = accessToken;
    } else {
      payload['access_token'] = accessToken;
      if (refreshToken != null && refreshToken.isNotEmpty) {
        payload['refresh_token'] = refreshToken;
      }
    }

    final response = await http.post(
      Uri.parse('${AppConstants.baseUrl}/integrations/google/connect'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode(payload),
    );

    final body = response.body.isNotEmpty ? jsonDecode(response.body) : {};
    if (response.statusCode == 200) {
      return body;
    }
    throw Exception(body['message'] ?? 'Failed to connect Google Calendar');
  }

  Future<void> disconnectGoogleCalendar(String token) async {
    final response = await http.delete(
      Uri.parse('${AppConstants.baseUrl}/integrations/google'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      return;
    }

    final body = response.body.isNotEmpty ? jsonDecode(response.body) : {};
    throw Exception(body['message'] ?? 'Failed to disconnect Google Calendar');
  }
}

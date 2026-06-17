import 'dart:convert';
import 'package:http/http.dart' as http;
import '../../core/constants/api_constants.dart';

class SettingsService {
  // ----- Main settings -----
  Future<Map<String, dynamic>> getSettings(String token) async {
    final response = await http.get(
      Uri.parse('${AppConstants.baseUrl}/settings'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load settings: ${response.statusCode}');
    }
  }

  Future<Map<String, dynamic>> updateSettings(String token, Map<String, dynamic> body) async {
    final response = await http.patch(
      Uri.parse('${AppConstants.baseUrl}/settings'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode(body),
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['message'] ?? 'Failed to update settings');
    }
  }

  // ----- Learning Schedules CRUD -----
  Future<Map<String, dynamic>> getLearningSchedules(String token) async {
    final response = await http.get(
      Uri.parse('${AppConstants.baseUrl}/settings/learning-schedules'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load learning schedules');
    }
  }

  Future<Map<String, dynamic>> createLearningSchedule(
    String token,
    String label,
    List<Map<String, dynamic>> slots,
  ) async {
    final response = await http.post(
      Uri.parse('${AppConstants.baseUrl}/settings/learning-schedules'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({'label': label, 'slots': slots}),
    );
    if (response.statusCode == 201) {
      return jsonDecode(response.body);
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['message'] ?? 'Failed to create learning schedule');
    }
  }

  Future<Map<String, dynamic>> updateLearningSchedule(
    String token,
    String scheduleId,
    Map<String, dynamic> body,
  ) async {
    final response = await http.patch(
      Uri.parse('${AppConstants.baseUrl}/settings/learning-schedules/$scheduleId'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode(body),
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['message'] ?? 'Failed to update learning schedule');
    }
  }

  Future<Map<String, dynamic>> deleteLearningSchedule(String token, String scheduleId) async {
    final response = await http.delete(
      Uri.parse('${AppConstants.baseUrl}/settings/learning-schedules/$scheduleId'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['message'] ?? 'Failed to delete learning schedule');
    }
  }
}
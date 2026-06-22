import 'dart:convert';
import 'package:http/http.dart' as http;
import '../../core/constants/api_constants.dart';

class CalendarService {
  final String baseUrl = AppConstants.baseUrl;

  Future<List<dynamic>> getCalendarTasks(String token) async {
    final response = await http.get(
      Uri.parse('$baseUrl/tasks/calendar'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body)['data']['tasks'] as List<dynamic>;
    } else {
      throw _handleError(response);
    }
  }

  Future<Map<String, dynamic>> getTaskDetail(
    String token,
    String taskId,
  ) async {
    final response = await http.get(
      Uri.parse('$baseUrl/tasks/$taskId'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body)['data']['task'] as Map<String, dynamic>;
    } else {
      throw _handleError(response);
    }
  }

  Future<void> updateTask(
    String token,
    String taskId,
    Map<String, dynamic> body,
  ) async {
    final response = await http.patch(
      Uri.parse('$baseUrl/tasks/$taskId'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode(body),
    );
    if (response.statusCode != 200) {
      throw _handleError(response);
    }
  }

  Future<void> deleteTask(String token, String taskId) async {
    
    final response = await http.delete(
      Uri.parse('$baseUrl/tasks/$taskId'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode != 200) {
      throw _handleError(response);
    }
  }

  Exception _handleError(http.Response response) {
    try {
      final error = jsonDecode(response.body);
      return Exception(error['message'] ?? 'Request failed');
    } catch (_) {
      return Exception('Request failed with status ${response.statusCode}');
    }
  }
}

import 'dart:convert';
import 'package:http/http.dart' as http;
import '../../core/constants/api_constants.dart';

class DashboardService {
  Future<Map<String, dynamic>> getDashboard(String token) async {
    final response = await http.get(
      Uri.parse('${AppConstants.baseUrl}/dashboard'),
      headers: {'Authorization': 'Bearer $token'},
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load dashboard');
    }
  }
}

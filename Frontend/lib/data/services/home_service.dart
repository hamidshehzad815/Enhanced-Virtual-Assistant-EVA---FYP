import 'dart:convert';
import '../../core/constants/api_constants.dart';
import 'api_client.dart';

class DashboardService {
  Future<Map<String, dynamic>> getDashboard(String token) async {
    final response = await ApiClient.get(
      Uri.parse('${AppConstants.baseUrl}/dashboard'),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('Failed to load dashboard');
  }
}

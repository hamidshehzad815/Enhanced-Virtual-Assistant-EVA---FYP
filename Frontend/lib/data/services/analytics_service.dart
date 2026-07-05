import 'dart:convert';
import 'package:http/http.dart' as http;
import '../../core/constants/api_constants.dart';
import '../models/analytics_model.dart';

class AnalyticsService {
  Future<AnalyticsDashboard> getDashboard(String token, int days) async {
    final url = Uri.parse('${AppConstants.baseUrl}/analytics/dashboard?days=$days');

    final response = await http.get(
      url,
      headers: {'Authorization': 'Bearer $token'},
    );

    // print('🔵 Analytics response status: ${response.statusCode}');
    // print('🔵 Analytics response body: ${response.body}');

    if (response.statusCode == 200) {
      final json = jsonDecode(response.body);
      // If the response has a "data" wrapper
      if (json.containsKey('data')) {
        return AnalyticsDashboard.fromJson(json['data']);
      } else {
        // If the response is the data directly
        return AnalyticsDashboard.fromJson(json);
      }
    } else {
      throw Exception('Failed to load analytics: ${response.statusCode} – ${response.body}');
    }
  }
}
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../../core/constants/api_constants.dart';
import '../models/analytics_model.dart';

class AnalyticsService {
  Future<AnalyticsDashboard> getDashboard(String token, int days) async {
    final response = await http.get(
      Uri.parse('${AppConstants.baseUrl}/analytics/dashboard?days=$days'),
      headers: {'Authorization': 'Bearer $token'},
    );

    if (response.statusCode == 200) {
      final json = jsonDecode(response.body);
      return AnalyticsDashboard.fromJson(json['data']);
    } else {
      throw Exception('Failed to load analytics dashboard: ${response.statusCode}');
    }
  }
}
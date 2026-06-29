import '../models/analytics_model.dart';
import '../services/analytics_service.dart';
import '../services/storage_service.dart';

class AnalyticsRepository {
  final AnalyticsService _service;

  AnalyticsRepository(this._service);

  Future<String> _getToken() async {
    final token = await StorageService.getAccessToken();
    if (token == null) throw Exception('No access token found');
    return token;
  }

  Future<AnalyticsDashboard> getDashboard({int days = 30}) async {
    final token = await _getToken();
    return await _service.getDashboard(token, days);
  }
}

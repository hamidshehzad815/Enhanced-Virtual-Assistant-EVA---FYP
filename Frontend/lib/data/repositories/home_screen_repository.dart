import '../services/home_service.dart';

abstract class IHomeScreenRepository {
  Future<Map<String, dynamic>> getDashboard(String token);
}

class HomeScreenRepository implements IHomeScreenRepository {
  final DashboardService _dashboardService;

  HomeScreenRepository({
    DashboardService? dashboardService,
  }) : _dashboardService =
           dashboardService ?? DashboardService();

  @override
  Future<Map<String, dynamic>> getDashboard(
    String token,
  ) {
    return _dashboardService.getDashboard(token);
  }
}
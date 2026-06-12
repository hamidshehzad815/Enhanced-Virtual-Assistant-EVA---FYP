import '../services/home_service.dart';
import '../services/profile_service.dart';

abstract class IHomeScreenRepository {
  Future<Map<String, dynamic>> getDashboard(String token);
}

class HomeScreenRepository implements IHomeScreenRepository {
  final DashboardService _dashboardService;
  final ProfileService _profileService;

  HomeScreenRepository({
    DashboardService? dashboardService,
    ProfileService? profileService,
  }) : _dashboardService = dashboardService ?? DashboardService(),
       _profileService = profileService ?? ProfileService();

  @override
  Future<Map<String, dynamic>> getDashboard(String token) {
    return _dashboardService.getDashboard(token);
  }

  Future<Map<String, dynamic>> getProfile(String token) {
    return _profileService.getProfile(token);
  }
}

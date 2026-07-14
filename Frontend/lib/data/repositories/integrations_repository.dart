import '../../core/constants/google_calendar_constants.dart';
import '../models/integration_model.dart';
import '../services/google_calendar_auth_service.dart';
import '../services/integrations_service.dart';

class IntegrationsRepository {
  final IntegrationsService _service;

  IntegrationsRepository({IntegrationsService? service})
      : _service = service ?? IntegrationsService();

  Future<List<IntegrationModel>> getIntegrations(String token) async {
    final response = await _service.getIntegrations(token);
    final rows = response['data']?['integrations'] as List? ?? [];
    return rows
        .map((row) => IntegrationModel.fromJson(Map<String, dynamic>.from(row)))
        .toList();
  }

  Future<bool> isGoogleCalendarConnected(String token) async {
    final integrations = await getIntegrations(token);
    return integrations.any((row) => row.isGoogleCalendar);
  }

  Future<Map<String, dynamic>> connectGoogleCalendar(String token) async {
    final auth = await GoogleCalendarAuthService.authorizeForCalendar();
    return _service.connectGoogleCalendar(
      token,
      accessToken: auth.accessToken,
      serverAuthCode: auth.serverAuthCode,
      scope: GoogleCalendarConstants.calendarEventsScope,
    );
  }

  Future<void> disconnectGoogleCalendar(String token) {
    return _service.disconnectGoogleCalendar(token);
  }
}

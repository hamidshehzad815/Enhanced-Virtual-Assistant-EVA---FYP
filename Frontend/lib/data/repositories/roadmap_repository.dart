import '../../data/models/roadmap_model.dart';
import '../../data/services/roadmap_service.dart';
import '../../data/services/storage_service.dart';
import '../models/schedule_date_model.dart';

class RoadmapRepository {
  final RoadmapService _service;

  RoadmapRepository({required RoadmapService service}) : _service = service;

  Future<String> _getToken() async {
    final token = await StorageService.getAccessToken();
    if (token == null) throw Exception('No access token');
    return token;
  }

  // ── Get all plans ──
  Future<List<PlanSummary>> getPlans() async {
    final token = await _getToken();
    return await _service.getPlans(token);
  }

  // ── Get roadmap detail ──
  Future<RoadmapDetail> getRoadmapDetail(String goalId) async {
    final token = await _getToken();
    return await _service.getRoadmapDetail(token, goalId);
  }

  // ── Get session detail ──
  Future<Session> getSessionDetail(String goalId, String sessionId) async {
    final token = await _getToken();
    return await _service.getSessionDetail(token, goalId, sessionId);
  }

  // ── Update session ──
  Future<Map<String, dynamic>> updateSession({
    required String goalId,
    required String sessionId,
    String? scheduledDate,
    String? status,
  }) async {
    final token = await _getToken();
    return await _service.updateSession(
      token: token,
      goalId: goalId,
      sessionId: sessionId,
      scheduledDate: scheduledDate,
      status: status,
    );
  }

  // ── Update plan status ──
  Future<Map<String, dynamic>> updateGoalStatus({
    required String goalId,
    required String status,
  }) async {
    final token = await _getToken();
    return await _service.updateGoalStatus(
      token: token,
      goalId: goalId,
      status: status,
    );
  }

  // ── Get overdue current sessions across all active goals ──
  Future<List<OverdueSessionItem>> getOverdueSessions() async {
    final token = await _getToken();
    final data = await _service.getOverdueSessions(token);
    return data.map((e) => OverdueSessionItem.fromJson(e)).toList();
  }

  Future<ScheduleDatesResponse> getScheduleDates(
    String goalId, {
    int horizonWeeks = 12,
  }) async {
    final token = await _getToken();
    final data = await _service.getScheduleDates(
      token,
      goalId,
      horizonWeeks: horizonWeeks,
    );
    return ScheduleDatesResponse.fromJson(data);
  }
}

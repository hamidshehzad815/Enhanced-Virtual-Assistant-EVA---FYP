import 'dart:convert';
import 'package:http/http.dart' as http;
import '../../core/constants/api_constants.dart';
import '../models/roadmap_model.dart';

class RoadmapService {
  // ── GET /api/roadmaps/plans ──
  Future<List<PlanSummary>> getPlans(String token) async {
    final response = await http.get(
      Uri.parse('${AppConstants.baseUrl}/roadmaps/plans'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode == 200) {
      final json = jsonDecode(response.body);
      final list = (json['data']['roadmaps'] as List)
          .map((e) => PlanSummary.fromJson(e))
          .toList();
      return list;
    } else {
      throw Exception('Failed to load plans');
    }
  }

  // ── GET /api/roadmaps/:goalId ──
  Future<RoadmapDetail> getRoadmapDetail(String token, String goalId) async {
    final response = await http.get(
      Uri.parse('${AppConstants.baseUrl}/roadmaps/$goalId'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode == 200) {
      final json = jsonDecode(response.body);
      return RoadmapDetail.fromJson(json['data']['roadmap']);
    } else {
      throw Exception('Failed to load roadmap detail');
    }
  }

  // ── GET /api/learning/:goalId/sessions/:sessionId ──
  Future<Session> getSessionDetail(String token, String goalId, String sessionId) async {
    final response = await http.get(
      Uri.parse('${AppConstants.baseUrl}/learning/$goalId/sessions/$sessionId'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode == 200) {
      final json = jsonDecode(response.body);
      return Session.fromJson(json['data']['session']);
    } else {
      throw Exception('Failed to load session detail');
    }
  }

  // ── PATCH /api/learning/:goalId/sessions/:sessionId ──
  Future<Map<String, dynamic>> updateSession({
    required String token,
    required String goalId,
    required String sessionId,
    String? scheduledDate,
    String? status,
  }) async {
    final body = <String, dynamic>{};
    if (scheduledDate != null) body['scheduled_date'] = scheduledDate;
    if (status != null) body['status'] = status;
    final response = await http.patch(
      Uri.parse('${AppConstants.baseUrl}/learning/$goalId/sessions/$sessionId'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode(body),
    );
    if (response.statusCode == 200) {
      final json = jsonDecode(response.body);
      return json['data'];
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['message'] ?? 'Failed to update session');
    }
  }

  // ── PATCH /api/learning/:goalId/status ──
  Future<Map<String, dynamic>> updateGoalStatus({
    required String token,
    required String goalId,
    required String status,
  }) async {
    final response = await http.patch(
      Uri.parse('${AppConstants.baseUrl}/learning/$goalId/status'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({'status': status}),
    );
    if (response.statusCode == 200) {
      final json = jsonDecode(response.body);
      return json['data'];
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['message'] ?? 'Failed to update goal status');
    }
  }
}
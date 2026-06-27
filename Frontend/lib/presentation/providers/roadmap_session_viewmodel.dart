import 'package:flutter/material.dart';
import '../../data/models/roadmap_model.dart';
import '../../data/repositories/roadmap_repository.dart';

class RoadmapSessionViewmodel extends ChangeNotifier {
  final RoadmapRepository _repository;
  final String goalId;

  RoadmapDetail? _roadmap;
  bool _isLoading = false;
  String? _error;

  RoadmapSessionViewmodel(this._repository, this.goalId);

  RoadmapDetail? get roadmap => _roadmap;
  bool get isLoading => _isLoading;
  String? get error => _error;

  Future<void> loadRoadmap() async {
    _setLoading(true);
    try {
      _roadmap = await _repository.getRoadmapDetail(goalId);
      _error = null;
    } catch (e) {
      _error = e.toString();
      _roadmap = null;
    } finally {
      _setLoading(false);
    }
  }

  // ── Get single session (for popup refresh) ──
  Future<Session> getSessionDetail(String sessionId) async {
    return await _repository.getSessionDetail(goalId, sessionId);
  }

  // ── Update session ──
  Future<void> updateSession({
    required String sessionId,
    String? scheduledDate,
    String? status,
  }) async {
    if (_roadmap == null) return;
    _setLoading(true);
    try {
      final data = await _repository.updateSession(
        goalId: goalId,
        sessionId: sessionId,
        scheduledDate: scheduledDate,
        status: status,
      );
      if (data['roadmap'] != null) {
        _roadmap = RoadmapDetail.fromJson(data['roadmap']);
      } else {
        await loadRoadmap(); // refresh
      }
      _error = null;
    } catch (e) {
      _error = e.toString();
    } finally {
      _setLoading(false);
    }
  }

  // ── Update plan status ──
  Future<void> updatePlanStatus(String status) async {
    if (_roadmap == null) return;
    _setLoading(true);
    try {
      await _repository.updateGoalStatus(goalId: goalId, status: status);
      await loadRoadmap();
      _error = null;
    } catch (e) {
      _error = e.toString();
    } finally {
      _setLoading(false);
    }
  }

  void _setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }
}

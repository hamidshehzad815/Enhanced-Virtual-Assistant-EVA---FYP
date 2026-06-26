import 'package:flutter/material.dart';
import '../../data/models/roadmap_model.dart';
import '../../data/repositories/roadmap_repository.dart';

class RoadmapViewmodel extends ChangeNotifier {
  final RoadmapRepository _repository;

  List<PlanSummary> _plans = [];
  bool _isLoading = false;
  String? _error;

  RoadmapViewmodel(this._repository);

  List<PlanSummary> get plans => _plans;
  bool get isLoading => _isLoading;
  String? get error => _error;

  Future<void> loadPlans() async {
    _setLoading(true);
    try {
      _plans = await _repository.getPlans();
      _error = null;
    } catch (e) {
      _error = e.toString();
      _plans = [];
    } finally {
      _setLoading(false);
    }
  }

  void _setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }
}
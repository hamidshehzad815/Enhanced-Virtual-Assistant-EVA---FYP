import 'package:flutter/material.dart';

class TaskRefreshNotifier extends ChangeNotifier {
  bool _needsRefresh = false;

  /// True when tasks changed since the last consumer reloaded. Persists so a
  /// screen that wasn't mounted when the change happened still reloads on entry.
  bool get needsRefresh => _needsRefresh;

  /// Signal that tasks changed (e.g. a task added/updated/deleted from chat).
  void refresh() {
    _needsRefresh = true;
    notifyListeners();
  }

  /// Clear the flag once a screen has reloaded in response to it.
  void consume() {
    _needsRefresh = false;
  }
}

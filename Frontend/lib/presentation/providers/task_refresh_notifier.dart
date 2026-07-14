import 'package:flutter/material.dart';

class TaskRefreshNotifier extends ChangeNotifier {
  void refresh() {
    notifyListeners();
  }
}
import 'package:flutter/material.dart';
// app_keys.dart
class AppKeys {
  static final scaffoldKey = GlobalKey<ScaffoldState>(); // for drawer
  // Optionally, if you need messenger:
  static final scaffoldMessengerKey = GlobalKey<ScaffoldMessengerState>();
}
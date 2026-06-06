import 'package:flutter/material.dart';

/// App Constants - Single responsibility: Store all app-wide constants
class AppConstants {
  // Color pairs (light / dark) for home screen cards
  static const Color upNextColorLight = Color.fromARGB(255, 223, 180, 169);
  static const Color upNextColorDark = Color(0xFF2D2A2A);

  static const Color progressColorLight = Color.fromARGB(255, 209, 235, 217);
  static const Color progressColorDark = Color(0xFF1E2A24);

  static const Color focusColorLight = Color.fromARGB(255, 203, 194, 240);
  static const Color focusColorDark = Color(0xFF2D2A4A);

  static const Color scheduleColorLight = Color.fromARGB(255, 201, 225, 241);
  static const Color scheduleColorDark = Color(0xFF1A283A);

  // Animation durations
  static const Duration animationDuration = Duration(milliseconds: 1400);
  static const Duration shortAnimationDuration = Duration(milliseconds: 300);

  // Pagination
  static const int itemsPerPage = 10;
  static const int defaultTimeoutSeconds = 30;
}

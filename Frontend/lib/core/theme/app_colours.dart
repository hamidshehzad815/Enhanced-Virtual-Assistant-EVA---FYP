import 'package:flutter/material.dart';

class AppColors {
  // light mode

  /// Main screen background — soft warm beige
  static const backgroundLight = Color.fromARGB(255, 205, 198, 179);

  /// Primary headings & important text — dark charcoal
  static const primaryTextLight = Color(0xFF1F2937);

  /// Subtitles, hints, captions
  static const secondaryTextLight = Color(0xFF6B7280);

  /// Card / container backgrounds
  static const cardLight = Colors.white;

  /// Borders & dividers
  static const borderLight = Color.fromARGB(255, 186, 181, 181);

  /// Input field background
  static const inputFillLight = Colors.white;

  /// Scaffold background as a plain Color
  static const scaffoldColorLight = Color(0xFFF4F0E6);

  // dark mode

  /// Scaffold background — used as fallback / opaque base
  /// The actual gradient is applied via AppGradients.darkBackground
  static const scaffoldColorDark = Color(0xFF0B1120);

  /// Primary text — pure white
  static const primaryTextDark = Colors.white;

  /// Secondary / muted text — soft grey-blue
  static const secondaryTextDark = Color(0xFF8A95B0);

  /// Card background — dark navy panel (like the dashboard cards)
  static const cardDark = Color(0xFF161D2F);

  /// Slightly elevated card (e.g. inner containers)
  static const cardElevatedDark = Color.fromARGB(255, 42, 47, 68);

  /// Borders & dividers in dark mode
  static const borderDark = Color(0xFF243050);

  /// Input field fill
  static const inputFillDark = Color(0xFF1A2035);

  /// Hint / placeholder text
  static const hintDark = Color(0xFF4A5578);

  // Same stuff

  /// Primary amber — buttons, highlights, active states
  static const primary = Color(0xFFF59E0B);

  /// Darker amber — pressed / gradient end
  static const primaryDark = Color(0xFFD97706);

  /// Dark background gradient
  static const darkBackgroundGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color.fromARGB(255, 34, 34, 50),
      Color(0xFF161625),
      Color(0xFF2A1B14),
      Color(0xFF3D281C),
    ],
    stops: [0.1, 0.4, 0.7, 1.0],
  );
}

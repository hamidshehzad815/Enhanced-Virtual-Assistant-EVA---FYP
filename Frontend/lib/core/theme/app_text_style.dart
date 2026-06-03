import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
class AppTextStyles {
  // ── LOGO (EVA wordmark) ────────────────────────────────────────────────────
  // No color set — inherits from DefaultTextStyle / theme's titleLarge
  static TextStyle logo = GoogleFonts.libreBaskerville(
    fontSize: 24,
    fontWeight: FontWeight.bold,
  );

  // ── MAIN HEADLINE ──────────────────────────────────────────────────────────
  // No color — inherits from theme so it goes white in dark, dark in light
  static TextStyle headline = GoogleFonts.instrumentSerif(
    fontSize: 56,
    fontWeight: FontWeight.w500,
    height: 1.1,
  );

  // ── ITALIC YELLOW HIGHLIGHT ────────────────────────────────────────────────
  // Brand color is fixed — intentional, same in both modes
  static TextStyle headlineWithYellow = GoogleFonts.instrumentSerif(
    fontSize: 56,
    fontWeight: FontWeight.w500,
    fontStyle: FontStyle.italic,
    height: 1.1,
    color: const Color(0xFFF59E0B),
  );

  // ── BODY TEXT ──────────────────────────────────────────────────────────────
  // No color — inherits
  static TextStyle body = GoogleFonts.inter(
    fontSize: 16,
    fontWeight: FontWeight.normal,
  );

  // ── MEDIUM TITLE (for dialogs, card headers, auth titles) ───────────────
  static TextStyle titleMedium = GoogleFonts.instrumentSerif(
    fontSize: 26,
    fontWeight: FontWeight.w500,
    height: 1.1,
  );

  // ── HEADER LARGE ─────────────────────────────────────────────────────────
  static TextStyle headerLarge = GoogleFonts.inter(
    fontSize: 28,
    fontWeight: FontWeight.w700,
    height: 1.1,
  );

  // ── SMALL SUBTITLE / HELP TEXT ──────────────────────────────────────────
  static TextStyle subtitleSmall = GoogleFonts.inter(
    fontSize: 13,
    fontWeight: FontWeight.normal,
  );

  // ── MEDIUM SUBTITLE / CAPTION ────────────────────────────────────────────
  static TextStyle subtitleMedium = GoogleFonts.inter(
    fontSize: 13,
    fontWeight: FontWeight.w500,
  );

  // ── INFO / LABEL TEXT ──────────────────────────────────────────────────────
  // No color — inherits (will pick up secondaryText from theme)
  static TextStyle info = GoogleFonts.inter(fontSize: 10, letterSpacing: 1.2);

  // ── BUTTON TEXT ────────────────────────────────────────────────────────────
  // Always white — sits on colored button backgrounds
  static TextStyle button = GoogleFonts.inter(
    fontSize: 16,
    fontWeight: FontWeight.w600,
    // color: Colors.white,
  );
}

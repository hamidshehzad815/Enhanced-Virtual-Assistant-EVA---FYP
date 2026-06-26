import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

// ---------- COLORS ----------
const _c1 = Color(0xFF534AB7);
const _c2 = Color(0xFF185FA5);
const _c3 = Color(0xFF993C1D);
const _c4 = Color(0xFF0F6E56);
const _c5 = Color(0xFF854F0B);
const _c6 = Color(0xFF993556);
const _c7 = Color(0xFF3B6D11);

const _b1 = Color(0xFFEEEDFE);
const _b2 = Color(0xFFE6F1FB);
const _b3 = Color(0xFFFAECE7);
const _b4 = Color(0xFFE1F5EE);
const _b5 = Color(0xFFFAEEDA);
const _b6 = Color(0xFFFBEAF0);
const _b7 = Color(0xFFEAF3DE);

// ---------- INFO CLASS (only for the sheet) ----------
class RoadmapInfo {
  final String id;
  final String name;
  final String category;
  final IconData icon;
  final Color color;
  final Color bg;
  final String desc;
  final String topicsLabel;
  final String level;

  const RoadmapInfo({
    required this.id,
    required this.name,
    required this.category,
    required this.icon,
    required this.color,
    required this.bg,
    required this.desc,
    this.topicsLabel = '',
    this.level = '',
  });
}

// ---------- AVAILABLE ROADMAPS (for info sheet only) ----------
final List<RoadmapInfo> kAllRoadmaps = [
  RoadmapInfo(
    id: '1',
    name: 'Python',
    category: 'Programming Language',
    icon: FontAwesomeIcons.python,
    color: _c1,
    bg: _b1,
    desc: 'Python basics, data handling, OOP, and practical scripting.',
  ),
  RoadmapInfo(
    id: '2',
    name: 'JavaScript',
    category: 'Programming Language',
    icon: FontAwesomeIcons.js,
    color: _c3,
    bg: _b3,
    desc: 'JavaScript fundamentals, DOM, async programming, and APIs.',
  ),
  RoadmapInfo(
    id: '3',
    name: 'TypeScript',
    category: 'Programming Language',
    icon: FontAwesomeIcons.code,
    color: _c2,
    bg: _b2,
    desc: 'Typed JavaScript, interfaces, generics, and modern frontend use.',
  ),
  RoadmapInfo(
    id: '4',
    name: 'Java',
    category: 'Programming Language',
    icon: FontAwesomeIcons.java,
    color: _c4,
    bg: _b4,
    desc: 'Java syntax, OOP, collections, streams, and backend foundations.',
  ),
  RoadmapInfo(
    id: '5',
    name: 'C#',
    category: '.NET Language',
    icon: FontAwesomeIcons.microsoft,
    color: _c5,
    bg: _b5,
    desc: 'C# syntax, OOP, LINQ, and .NET development basics.',
  ),
  RoadmapInfo(
    id: '6',
    name: 'C++',
    category: 'Programming Language',
    icon: FontAwesomeIcons.plus,
    color: _c6,
    bg: _b6,
    desc: 'C++ fundamentals, memory, STL, OOP, and performance-focused coding.',
  ),
  RoadmapInfo(
    id: '7',
    name: 'Go (Golang)',
    category: 'Programming Language',
    icon: FontAwesomeIcons.golang,
    color: _c7,
    bg: _b7,
    desc: 'Go syntax, concurrency, packages, and backend service development.',
  ),
  RoadmapInfo(
    id: '8',
    name: 'Rust',
    category: 'Programming Language',
    icon: FontAwesomeIcons.rust,
    color: _c1,
    bg: _b1,
    desc: 'Rust ownership, borrowing, safety, and systems programming.',
  ),
  RoadmapInfo(
    id: '9',
    name: 'SQL',
    category: 'Database Language',
    icon: FontAwesomeIcons.database,
    color: _c2,
    bg: _b2,
    desc: 'SQL queries, joins, filtering, grouping, and database fundamentals.',
  ),
  RoadmapInfo(
    id: '10',
    name: 'PHP',
    category: 'Programming Language',
    icon: FontAwesomeIcons.php,
    color: _c3,
    bg: _b3,
    desc: 'PHP syntax, web basics, forms, sessions, and backend scripting.',
  ),
  RoadmapInfo(
    id: '11',
    name: 'Kotlin',
    category: 'Programming Language',
    icon: FontAwesomeIcons.code,
    color: _c4,
    bg: _b4,
    desc: 'Kotlin basics, null safety, OOP, and Android development foundations.',
  ),
  RoadmapInfo(
    id: '12',
    name: 'Swift',
    category: 'Programming Language',
    icon: FontAwesomeIcons.swift,
    color: _c5,
    bg: _b5,
    desc: 'Swift syntax, optionals, structs, classes, and iOS basics.',
  ),
  RoadmapInfo(
    id: '13',
    name: 'Ruby',
    category: 'Programming Language',
    icon: FontAwesomeIcons.gem,
    color: _c6,
    bg: _b6,
    desc: 'Ruby syntax, OOP, scripting, and web development fundamentals.',
  ),
  RoadmapInfo(
    id: '14',
    name: 'Dart',
    category: 'Programming Language',
    icon: FontAwesomeIcons.codiepie,
    color: _c7,
    bg: _b7,
    desc: 'Dart syntax, null safety, async code, and Flutter foundations.',
  ),
  RoadmapInfo(
    id: '15',
    name: 'C',
    category: 'Programming Language',
    icon: FontAwesomeIcons.c,
    color: _c1,
    bg: _b1,
    desc: 'C language basics, pointers, memory, and low-level programming.',
  ),
];

// ─── Helper functions to get icon and color from kAllRoadmaps ───
IconData? getLanguageIcon(String? languageKey) {
  if (languageKey == null) return null;
  final found = kAllRoadmaps.firstWhere(
    (r) => r.name.toLowerCase() == languageKey.toLowerCase(),
    orElse: () => kAllRoadmaps.first, // fallback
  );
  return found.icon;
}

Color? getLanguageColor(String? languageKey) {
  if (languageKey == null) return null;
  final found = kAllRoadmaps.firstWhere(
    (r) => r.name.toLowerCase() == languageKey.toLowerCase(),
    orElse: () => kAllRoadmaps.first, // fallback
  );
  return found.color;
}

// ─── For language key like "python", "javascript" etc. ───
IconData? getLanguageIconByKey(String? key) {
  if (key == null) return null;
  final found = kAllRoadmaps.firstWhere(
    (r) => r.name.toLowerCase() == key.toLowerCase(),
    orElse: () => kAllRoadmaps.first,
  );
  return found.icon;
}

Color? getLanguageColorByKey(String? key) {
  if (key == null) return null;
  final found = kAllRoadmaps.firstWhere(
    (r) => r.name.toLowerCase() == key.toLowerCase(),
    orElse: () => kAllRoadmaps.first,
  );
  return found.color;
}
import 'package:flutter/material.dart';

enum NodeStatus { completed, active, locked }

class RoadmapNode {
  final String id, label, sub, time, duration, desc, ytUrl, schedule;
  final dynamic icon;
  final Color color, bg;
  final NodeStatus status;
  final bool important;

  const RoadmapNode({
    required this.id,
    required this.label,
    required this.sub,
    required this.icon,
    required this.color,
    required this.bg,
    required this.status,
    required this.time,
    required this.duration,
    required this.desc,
    required this.ytUrl,
    required this.schedule,
    this.important = false,
  });
}

class RoadmapData {
  final String id, name, category, desc, topicsLabel, level;
  final dynamic icon;
  final Color color, bg;
  final List<RoadmapNode> nodes;

  const RoadmapData({
    required this.id,
    required this.name,
    required this.category,
    required this.icon,
    required this.color,
    required this.bg,
    required this.desc,
    required this.topicsLabel,
    required this.level,
    required this.nodes,
  });
}

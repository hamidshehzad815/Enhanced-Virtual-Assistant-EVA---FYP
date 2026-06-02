import 'package:flutter/material.dart';

enum TaskPriority { low, medium, high }

enum TaskCategory { exam, assignment, lecture, study, meeting, personal }

enum TaskStatus { pending, completed, missed }

class CalendarTask {
  final String id;
  final String title;
  final String? subtitle;       // room / description
  final DateTime date;
  final TimeOfDay startTime;
  final TimeOfDay? endTime;
  final TaskPriority priority;
  final TaskCategory category;
  bool isCompleted;
 TaskStatus status;

  CalendarTask({
    required this.id,
    required this.title,
   this.subtitle,
    required this.date,
    required this.startTime,
    this.endTime,
    required this.priority,
    required this.category,
    this.isCompleted = false,
    this.status = TaskStatus.pending,
  });

  // Formatted time string e.g. "10:00 AM" or "10:00 AM – 11:30 AM"
  String get timeLabel {
    String fmt(TimeOfDay t) {
      final h = t.hour;
      final m = t.minute.toString().padLeft(2, '0');
      final period = h >= 12 ? 'PM' : 'AM';
      final hour = h > 12 ? h - 12 : (h == 0 ? 12 : h);
      return '$hour:$m $period';
    }

    if (endTime != null) return '${fmt(startTime)} – ${fmt(endTime!)}';
    return fmt(startTime);
  }
}
import 'package:flutter/material.dart';

enum TaskPriority { low, medium, high }
enum TaskStatus { pending, ongoing, overdue, completed }

class CalendarTask {
  final String id;
  final String title;
  final String? description;
  final DateTime dueDateTime;          // from API `due_datetime`
  final int durationMinutes;           // from API `duration`
  final TaskPriority priority;
  final TaskStatus status;             // stored status
  final String displayStatus;          // use for badges
  final bool isLearningTask;
  final String? learningGoalId;
  final DateTime? completedAt;

  // convenience
  TimeOfDay get startTime => TimeOfDay.fromDateTime(dueDateTime);
  TimeOfDay get endTime {
    final end = dueDateTime.add(Duration(minutes: durationMinutes));
    return TimeOfDay.fromDateTime(end);
  }

  CalendarTask({
    required this.id,
    required this.title,
    this.description,
    required this.dueDateTime,
    required this.durationMinutes,
    required this.priority,
    required this.status,
    required this.displayStatus,
    this.isLearningTask = false,
    this.learningGoalId,
    this.completedAt,
  });

  CalendarTask copyWith({
    String? id,
    String? title,
    String? description,
    DateTime? dueDateTime,
    int? durationMinutes,
    TaskPriority? priority,
    TaskStatus? status,
    String? displayStatus,
    bool? isLearningTask,
    String? learningGoalId,
    DateTime? completedAt,
  }) {
    return CalendarTask(
      id: id ?? this.id,
      title: title ?? this.title,
      description: description ?? this.description,
      dueDateTime: dueDateTime ?? this.dueDateTime,
      durationMinutes: durationMinutes ?? this.durationMinutes,
      priority: priority ?? this.priority,
      status: status ?? this.status,
      displayStatus: displayStatus ?? this.displayStatus,
      isLearningTask: isLearningTask ?? this.isLearningTask,
      learningGoalId: learningGoalId ?? this.learningGoalId,
      completedAt: completedAt ?? this.completedAt,
    );
  }

factory CalendarTask.fromJson(Map<String, dynamic> json) {
  return CalendarTask(
    id: json['id'],
    title: json['title'],
    description: json['description'],
    dueDateTime: DateTime.parse(json['due_datetime']).toLocal(), //fix no 4
    durationMinutes: json['duration'] ?? 0,
    priority: TaskPriority.values.firstWhere(
      (e) => e.name == json['priority'],
      orElse: () => TaskPriority.medium,
    ),
    status: TaskStatus.values.firstWhere(
      (e) => e.name == json['status'],
      orElse: () => TaskStatus.pending,
    ),
    displayStatus: json['display_status'] ?? 'pending',
    isLearningTask: json['is_learning_task'] ?? false,
    learningGoalId: json['learning_goal_id'],
    completedAt: json['completed_at'] != null
        ? DateTime.parse(json['completed_at'])
        : null,
  );
}

  Map<String, dynamic> toJson() => {
    'title': title,
    'description': description,
    'due_datetime': dueDateTime.toIso8601String(),
    'duration': durationMinutes,
    'priority': priority.name,
    'status': status.name,
  };

  @override
  bool operator ==(Object other) =>
      other is CalendarTask && runtimeType == other.runtimeType && id == other.id;
  @override
  int get hashCode => id.hashCode;
}
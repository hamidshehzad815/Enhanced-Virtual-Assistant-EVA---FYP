import 'package:flutter/material.dart';

class SettingsModel {
  // App Preferences
  String theme;
  bool googleCalendarSyncEnabled;
  bool behavioralAnalyticsEnabled;

  // Notifications
  bool notificationsEnabled;
  bool pushNotificationsEnabled;
  bool emailNotificationsEnabled;
  bool quietHoursEnabled;
  List<QuietHourInterval> quietHours;

  // Task Scheduling
  int defaultReminderMinutes;
  int defaultTaskDuration;

  // Learning Scheduling
  int defaultLearningReminderMinutes;
  List<LearningSchedule> learningSchedules;

  // Privacy & Social
  bool allowFriendRequests;

  SettingsModel({
    this.theme = 'system',
    this.googleCalendarSyncEnabled = false,
    this.behavioralAnalyticsEnabled = true,
    this.notificationsEnabled = true,
    this.pushNotificationsEnabled = true,
    this.emailNotificationsEnabled = false,
    this.quietHoursEnabled = false,
    this.quietHours = const [],
    this.defaultReminderMinutes = 30,
    this.defaultTaskDuration = 120,
    this.defaultLearningReminderMinutes = 15,
    this.learningSchedules = const [],
    this.allowFriendRequests = true,
  });

  factory SettingsModel.fromJson(Map<String, dynamic> json) {
    final data = json['data']?['settings'] ?? json;
    return SettingsModel(
      theme: data['theme'] ?? 'light',
      googleCalendarSyncEnabled: data['google_calendar_sync_enabled'] ?? false,
      behavioralAnalyticsEnabled: data['behavioral_analytics_enabled'] ?? true,
      notificationsEnabled: data['notifications_enabled'] ?? true,
      pushNotificationsEnabled: data['push_notifications_enabled'] ?? true,
      emailNotificationsEnabled: data['email_notifications_enabled'] ?? false,
      quietHoursEnabled: data['quiet_hours_enabled'] ?? false,
      quietHours: (data['quiet_hours'] as List?)
              ?.map((e) => QuietHourInterval.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      defaultReminderMinutes: data['default_reminder_minutes'] ?? 30,
      defaultTaskDuration: data['default_task_duration'] ?? 120,
      defaultLearningReminderMinutes: data['default_learning_reminder_minutes'] ?? 15,
      learningSchedules: (data['preferred_learning_schedules'] as List?)
              ?.map((e) => LearningSchedule.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      allowFriendRequests: data['allow_friend_requests'] ?? true,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'theme': theme,
      'google_calendar_sync_enabled': googleCalendarSyncEnabled,
      'behavioral_analytics_enabled': behavioralAnalyticsEnabled,
      'notifications_enabled': notificationsEnabled,
      'push_notifications_enabled': pushNotificationsEnabled,
      'email_notifications_enabled': emailNotificationsEnabled,
      'quiet_hours_enabled': quietHoursEnabled,
      'quiet_hours': quietHours.map((e) => e.toJson()).toList(),
      'default_reminder_minutes': defaultReminderMinutes,
      'default_task_duration': defaultTaskDuration,
      'default_learning_reminder_minutes': defaultLearningReminderMinutes,
      // Do NOT include preferred_learning_schedules – updates go via separate endpoints
      'allow_friend_requests': allowFriendRequests,
    };
  }

  SettingsModel copyWith({
    String? theme,
    bool? googleCalendarSyncEnabled,
    bool? behavioralAnalyticsEnabled,
    bool? notificationsEnabled,
    bool? pushNotificationsEnabled,
    bool? emailNotificationsEnabled,
    bool? quietHoursEnabled,
    List<QuietHourInterval>? quietHours,
    int? defaultReminderMinutes,
    int? defaultTaskDuration,
    int? defaultLearningReminderMinutes,
    List<LearningSchedule>? learningSchedules,
    bool? allowFriendRequests,
  }) {
    return SettingsModel(
      theme: theme ?? this.theme,
      googleCalendarSyncEnabled: googleCalendarSyncEnabled ?? this.googleCalendarSyncEnabled,
      behavioralAnalyticsEnabled: behavioralAnalyticsEnabled ?? this.behavioralAnalyticsEnabled,
      notificationsEnabled: notificationsEnabled ?? this.notificationsEnabled,
      pushNotificationsEnabled: pushNotificationsEnabled ?? this.pushNotificationsEnabled,
      emailNotificationsEnabled: emailNotificationsEnabled ?? this.emailNotificationsEnabled,
      quietHoursEnabled: quietHoursEnabled ?? this.quietHoursEnabled,
      quietHours: quietHours ?? this.quietHours,
      defaultReminderMinutes: defaultReminderMinutes ?? this.defaultReminderMinutes,
      defaultTaskDuration: defaultTaskDuration ?? this.defaultTaskDuration,
      defaultLearningReminderMinutes: defaultLearningReminderMinutes ?? this.defaultLearningReminderMinutes,
      learningSchedules: learningSchedules ?? this.learningSchedules,
      allowFriendRequests: allowFriendRequests ?? this.allowFriendRequests,
    );
  }
}

class QuietHourInterval {
  String label;
  TimeOfDay startTime;
  TimeOfDay endTime;
  bool enabled;

  QuietHourInterval({
    required this.label,
    required this.startTime,
    required this.endTime,
    this.enabled = true,
  });

  static TimeOfDay _parseTime(String time) {
    final parts = time.split(':');
    return TimeOfDay(hour: int.parse(parts[0]), minute: int.parse(parts[1]));
  }

  static String _formatTime(TimeOfDay time) {
    final hour = time.hour.toString().padLeft(2, '0');
    final minute = time.minute.toString().padLeft(2, '0');
    return '$hour:$minute';
  }

  factory QuietHourInterval.fromJson(Map<String, dynamic> json) {
    return QuietHourInterval(
      label: json['label'] ?? '',
      startTime: _parseTime(json['start']),
      endTime: _parseTime(json['end']),
      enabled: json['enabled'] ?? true,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'label': label,
      'start': _formatTime(startTime),
      'end': _formatTime(endTime),
      'enabled': enabled,
    };
  }
}

class LearningSchedule {
  final String id;
  final String label;
  final List<ScheduleSlot> slots;

  LearningSchedule({
    required this.id,
    required this.label,
    required this.slots,
  });

  factory LearningSchedule.fromJson(Map<String, dynamic> json) {
    return LearningSchedule(
      id: json['id'] ?? '',
      label: json['label'] ?? '',
      slots: (json['slots'] as List?)
              ?.map((e) => ScheduleSlot.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'label': label,
      'slots': slots.map((e) => e.toJson()).toList(),
    };
  }
}

class ScheduleSlot {
  final int day;
  final String time;
  final int durationMinutes;

  ScheduleSlot({
    required this.day,
    required this.time,
    required this.durationMinutes,
  });

  factory ScheduleSlot.fromJson(Map<String, dynamic> json) {
    return ScheduleSlot(
      day: json['day'] ?? 0,
      time: json['time'] ?? '',
      durationMinutes: json['duration_minutes'] ?? 15,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'day': day,
      'time': time,
      'duration_minutes': durationMinutes,
    };
  }
}
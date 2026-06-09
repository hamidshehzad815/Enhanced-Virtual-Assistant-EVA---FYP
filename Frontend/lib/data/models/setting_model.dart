import 'package:flutter/material.dart';

class SettingsModel {
  // ── Notifications ──────────────────────────────────────────────────────────
  bool notificationsEnabled;
  bool pushNotificationsEnabled;
  bool emailNotificationsEnabled;
  bool quietHoursEnabled;
  List<QuietHourInterval> quietHours = [];
  int defaultReminderMinutes;
  int defaultTopicReminderMinutes;

  // ── Task defaults ──────────────────────────────────────────────────────────
  String defaultTaskPriority; // 'low' | 'medium' | 'high'
  int defaultTaskDuration; // minutes

  // ── Task Scheduling ───────────────────────────────────────────────────
  int preferredLearningDuration; // minutes

  // ── Learning Scheduling ───────────────────────────────────────────────────
  List<LearningSchedule> learningSchedules = [];
  TimeOfDay? learningStartTime; // e.g. TimeOfDay(hour: 17, minute: 0)

  // ── Integrations ──────────────────────────────────────────────────────────
  bool googleCalendarSyncEnabled;

  // ── Privacy & Social ───────────────────────────────────────────────────────
  bool allowFriendRequests;
  bool showLastActive;
  int analyticsMinTasksThreshold;

  // ── App ────────────────────────────────────────────────────────────────────
  String theme; // 'light' | 'dark' | 'system'
  bool behavioralAnalyticsEnabled;

  SettingsModel({
    this.notificationsEnabled = true,
    this.pushNotificationsEnabled = true,
    this.emailNotificationsEnabled = false,
    this.quietHoursEnabled = false,
    this.quietHours = const [],
    this.defaultReminderMinutes = 30,
    this.defaultTopicReminderMinutes = 15,
    this.defaultTaskPriority = 'medium',
    this.defaultTaskDuration = 120,
    this.preferredLearningDuration = 90,

    this.googleCalendarSyncEnabled = false,
    this.allowFriendRequests = true,
    this.showLastActive = true,
    this.behavioralAnalyticsEnabled = false,
    this.analyticsMinTasksThreshold = 10,
    this.theme = 'light',
  });

  // Populate from API JSON map
  factory SettingsModel.fromJson(Map<String, dynamic> json) {
    final s = json['data']?['settings'] ?? json;
    return SettingsModel(
      notificationsEnabled: s['notifications_enabled'] ?? true,
      pushNotificationsEnabled: s['push_notifications_enabled'] ?? true,
      emailNotificationsEnabled: s['email_notifications_enabled'] ?? false,
      quietHours:
          (s['quiet_hours'] as List<dynamic>?)
              ?.map((qh) => QuietHourInterval.fromJson(qh))
              .toList() ??
          [],
      defaultReminderMinutes: s['default_reminder_minutes'] ?? 30,
      defaultTopicReminderMinutes: s['default_topic_reminder_minutes'] ?? 15,
      defaultTaskPriority: s['default_task_priority'] ?? 'medium',
      defaultTaskDuration: s['default_task_duration'] ?? 120,
      preferredLearningDuration: s['preferred_learning_duration'] ?? 90,
      googleCalendarSyncEnabled: s['google_calendar_sync_enabled'] ?? false,
      allowFriendRequests: s['allow_friend_requests'] ?? true,
      showLastActive: s['show_last_active'] ?? true,
      quietHoursEnabled: s['quiet_hours_enabled'] ?? false,
      behavioralAnalyticsEnabled: s['behavioral_analytics_enabled'] ?? false,
      analyticsMinTasksThreshold: s['analytics_min_tasks_threshold'] ?? 10,
      theme: s['theme'] ?? 'light',
    );
  }

  Map<String, dynamic> toJson() => {
    'notifications_enabled': notificationsEnabled,
    'push_notifications_enabled': pushNotificationsEnabled,
    'email_notifications_enabled': emailNotificationsEnabled,
    'default_reminder_minutes': defaultReminderMinutes,
    'default_topic_reminder_minutes': defaultTopicReminderMinutes,
    'default_task_priority': defaultTaskPriority,
    'default_task_duration': defaultTaskDuration,
    'preferred_learning_duration': preferredLearningDuration,
    'google_calendar_sync_enabled': googleCalendarSyncEnabled,
    'allow_friend_requests': allowFriendRequests,
    'show_last_active': showLastActive,
    'quiet_hours_enabled': quietHoursEnabled,
    'quiet_hours': quietHours.map((qh) => qh.toJson()).toList(),
    'behavioral_analytics_enabled': behavioralAnalyticsEnabled,
    'analytics_min_tasks_threshold': analyticsMinTasksThreshold,
    'theme': theme,
    //  'language': language,
  };
}

class QuietHourInterval {
  String label;
  TimeOfDay startTime;
  TimeOfDay endTime;

  QuietHourInterval({
    required this.label,
    required this.startTime,
    required this.endTime,
  });

  Map<String, dynamic> toJson() => {
    'label': label,
    'startHour': startTime.hour,
    'startMinute': startTime.minute,
    'endHour': endTime.hour,
    'endMinute': endTime.minute,
  };

  factory QuietHourInterval.fromJson(Map<String, dynamic> json) =>
      QuietHourInterval(
        label: json['label'],
        startTime: TimeOfDay(
          hour: json['startHour'],
          minute: json['startMinute'],
        ),
        endTime: TimeOfDay(hour: json['endHour'], minute: json['endMinute']),
      );
}

class LearningSchedule {
  String label;
  List<String> days; // 'monday', 'tuesday', ...
  TimeOfDay startTime;
  int durationMinutes; // can be > 60

  LearningSchedule({
    required this.label,
    required this.days,
    required this.startTime,
    required this.durationMinutes,
  });

  Map<String, dynamic> toJson() => {
    'label': label,
    'days': days,
    'startHour': startTime.hour,
    'startMinute': startTime.minute,
    'durationMinutes': durationMinutes,
  };

  factory LearningSchedule.fromJson(Map<String, dynamic> json) =>
      LearningSchedule(
        label: json['label'],
        days: List<String>.from(json['days']),
        startTime: TimeOfDay(
          hour: json['startHour'],
          minute: json['startMinute'],
        ),
        durationMinutes: json['durationMinutes'],
      );
}

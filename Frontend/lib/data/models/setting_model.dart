import 'package:flutter/material.dart';
class SettingsModel {
  // ── Notifications ──────────────────────────────────────────────────────────
  bool notificationsEnabled;
  bool pushNotificationsEnabled;
  bool emailNotificationsEnabled;
  bool quietHoursEnabled;
  int defaultReminderMinutes;
  int defaultTopicReminderMinutes;

  // ── Task defaults ──────────────────────────────────────────────────────────
  String defaultTaskPriority; // 'low' | 'medium' | 'high'
  int defaultTaskDuration; // minutes

  // ── Task Scheduling ───────────────────────────────────────────────────
  int preferredLearningDuration; // minutes
  String preferredLearningTime; // 'morning' | 'afternoon' | 'evening' | 'night'


  // ── Learning Scheduling ───────────────────────────────────────────────────
  List<String> preferredLearningDaysList = ['monday', 'wednesday', 'friday'];
  TimeOfDay? learningStartTime; // e.g. TimeOfDay(hour: 17, minute: 0)

  // ── Integrations ──────────────────────────────────────────────────────────
  bool googleCalendarSyncEnabled;

  // ── Privacy & Social ───────────────────────────────────────────────────────
  String allowFriendRequests; // 'everyone' | 'friends' | 'nobody'
  bool showLastActive;
  bool behavioralAnalyticsEnabled;
  int analyticsMinTasksThreshold;

  // ── App ────────────────────────────────────────────────────────────────────
  String theme; // 'light' | 'dark' | 'system'
  String language; // 'en' | 'ar' | etc.

  SettingsModel({
    this.notificationsEnabled = true,
    this.pushNotificationsEnabled = true,
    this.emailNotificationsEnabled = false,
    this.quietHoursEnabled = false,
    this.defaultReminderMinutes = 30,
    this.defaultTopicReminderMinutes = 15,
    this.defaultTaskPriority = 'medium',
    this.defaultTaskDuration = 120,
    this.preferredLearningDuration = 90,
    this.preferredLearningTime = 'afternoon',

    this.googleCalendarSyncEnabled = false,
    this.allowFriendRequests = 'everyone',
    this.showLastActive = true,
    this.behavioralAnalyticsEnabled = true,
    this.analyticsMinTasksThreshold = 10,
    this.theme = 'light',
    this.language = 'en',
  });

  // Populate from API JSON map
  factory SettingsModel.fromJson(Map<String, dynamic> json) {
    final s = json['data']?['settings'] ?? json;
    return SettingsModel(
      notificationsEnabled: s['notifications_enabled'] ?? true,
      pushNotificationsEnabled: s['push_notifications_enabled'] ?? true,
      emailNotificationsEnabled: s['email_notifications_enabled'] ?? false,
      quietHoursEnabled: s['quiet_hours_enabled'] ?? false,
      defaultReminderMinutes: s['default_reminder_minutes'] ?? 30,
      defaultTopicReminderMinutes: s['default_topic_reminder_minutes'] ?? 15,
      defaultTaskPriority: s['default_task_priority'] ?? 'medium',
      defaultTaskDuration: s['default_task_duration'] ?? 120,
      preferredLearningDuration: s['preferred_learning_duration'] ?? 90,
      preferredLearningTime: s['preferred_learning_time'] ?? 'afternoon',
      googleCalendarSyncEnabled: s['google_calendar_sync_enabled'] ?? false,
      allowFriendRequests: s['allow_friend_requests'] ?? 'everyone',
      showLastActive: s['show_last_active'] ?? true,
      behavioralAnalyticsEnabled: s['behavioral_analytics_enabled'] ?? true,
      analyticsMinTasksThreshold: s['analytics_min_tasks_threshold'] ?? 10,
      theme: s['theme'] ?? 'light',
      language: s['language'] ?? 'en',
    );
  }

  Map<String, dynamic> toJson() => {
    'notifications_enabled': notificationsEnabled,
    'push_notifications_enabled': pushNotificationsEnabled,
    'email_notifications_enabled': emailNotificationsEnabled,
    'quiet_hours_enabled': quietHoursEnabled,
    'default_reminder_minutes': defaultReminderMinutes,
    'default_topic_reminder_minutes': defaultTopicReminderMinutes,
    'default_task_priority': defaultTaskPriority,
    'default_task_duration': defaultTaskDuration,
    'preferred_learning_duration': preferredLearningDuration,
    'preferred_learning_time': preferredLearningTime,
    'google_calendar_sync_enabled': googleCalendarSyncEnabled,
    'allow_friend_requests': allowFriendRequests,
    'show_last_active': showLastActive,
    'behavioral_analytics_enabled': behavioralAnalyticsEnabled,
    'analytics_min_tasks_threshold': analyticsMinTasksThreshold,
    'theme': theme,
    'language': language,
  };
}
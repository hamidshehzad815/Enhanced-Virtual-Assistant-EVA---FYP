import 'package:flutter/material.dart';
import '../models/user_profile.dart';
import '../models/task_data.dart';
import '../models/focus_data.dart';
import '../models/schedule_item.dart';

/// Home Screen Data Service
class HomeScreenService {
  Future<UserProfile> getUserProfile() async {
    return Future.value(
      UserProfile(name: 'Areej', userInitial: 'A', dailyProgress: 0.65),
    );
  }

  Future<TaskData> getUpcomingTask() async {
    return Future.value(
      TaskData(
        title: 'NLP Mid Exam',
        subtitle: 'Monday   5:00 PM ',
        icon: Icons.edit_note_rounded.codePoint,
        cardColor: const Color(0xFFDBEAFE).value,
        iconColor: const Color(0xFF3B82F6).value,
      ),
    );
  }

  /// ✅ Returns a LIST of focus items
  Future<List<FocusData>> getCurrentFocusList() async {
    return Future.value([
      FocusData(
        title: 'Python Roadmap',
        nextTopic: 'OOP Concepts',
        nextTopicTime: DateTime.now().add(const Duration(hours: 2)),
      ),
      FocusData(
        title: 'Flutter Animations',
        nextTopic: 'CustomPaint & Animations',
        nextTopicTime: DateTime.now().add(const Duration(hours: 5)),
      ),
    ]);
  }

  Future<List<ScheduleItem>> getSchedule() async {
    return Future.value([
      ScheduleItem(time: DateTime(2023, 10, 1, 8, 0), title: 'Math Lecture', tag: 'completed'),
      ScheduleItem(time: DateTime(2023, 10, 1, 10, 0), title: 'Intro to AI', tag: 'pending'),
      ScheduleItem(time: DateTime(2023, 10, 1, 13, 0), title: 'Physics Lab', tag: 'ongoing'),
      ScheduleItem(time: DateTime(2023, 10, 1, 15, 30), title: 'Group Study', tag: 'due'),
      ScheduleItem(time: DateTime(2023, 10, 1, 17, 0), title: 'NLP Exam Prep', tag: 'pending'),
    ]);
  }
}

/// Repository interface
abstract class IHomeScreenRepository {
  Future<UserProfile> getUserProfile();
  Future<TaskData> getUpcomingTask();
  Future<List<FocusData>> getCurrentFocusList(); // ✅ changed
  Future<List<ScheduleItem>> getSchedule();
}

/// Implementation
class HomeScreenRepository implements IHomeScreenRepository {
  final HomeScreenService _service;
  HomeScreenRepository({HomeScreenService? service})
      : _service = service ?? HomeScreenService();

  @override
  Future<UserProfile> getUserProfile() => _service.getUserProfile();

  @override
  Future<TaskData> getUpcomingTask() => _service.getUpcomingTask();

  @override
  Future<List<FocusData>> getCurrentFocusList() => _service.getCurrentFocusList();

  @override
  Future<List<ScheduleItem>> getSchedule() => _service.getSchedule();
}
import 'package:flutter/material.dart';
import 'package:table_calendar/table_calendar.dart';
import '../../data/models/calendar_task_model.dart';

List<CalendarTask> _buildPlaceholderTasks() {
  final now = DateTime.now();
  final today = DateTime(now.year, now.month, now.day);
  final tomorrow = today.add(const Duration(days: 1));
  final dayAfter = today.add(const Duration(days: 2));
  final yesterday = today.subtract(const Duration(days: 1));
  final nextWeek = today.add(const Duration(days: 5));

  return [
    CalendarTask(
      id: '1',
      title: 'Math Lecture',
      date: today,
      startTime: const TimeOfDay(hour: 8, minute: 0),
      endTime: const TimeOfDay(hour: 9, minute: 30),
      priority: TaskPriority.medium,
      category: TaskCategory.lecture,
      isCompleted: true,
    ),
    CalendarTask(
      id: '2',
      title: 'Intro to AI',
      date: today,
      startTime: const TimeOfDay(hour: 10, minute: 0),
      endTime: const TimeOfDay(hour: 11, minute: 30),
      priority: TaskPriority.high,
      category: TaskCategory.lecture,
    ),
    CalendarTask(
      id: '3',
      title: 'NLP Assignment Submission',
      date: today,
      startTime: const TimeOfDay(hour: 13, minute: 0),
      priority: TaskPriority.high,
      category: TaskCategory.assignment,
    ),
    CalendarTask(
      id: '4',
      title: 'Group Study Session',
      date: today,
      startTime: const TimeOfDay(hour: 15, minute: 30),
      endTime: const TimeOfDay(hour: 17, minute: 0),
      priority: TaskPriority.low,
      category: TaskCategory.study,
    ),
    CalendarTask(
      id: '5',
      title: 'Physics Lab',
      date: today,
      startTime: const TimeOfDay(hour: 13, minute: 0),
      endTime: const TimeOfDay(hour: 15, minute: 0),
      priority: TaskPriority.medium,
      category: TaskCategory.lecture,
    ),
    CalendarTask(
      id: '6',
      title: 'NLP Mid Exam',
      date: tomorrow,
      startTime: const TimeOfDay(hour: 17, minute: 0),
      endTime: const TimeOfDay(hour: 19, minute: 0),
      priority: TaskPriority.high,
      category: TaskCategory.exam,
    ),
    CalendarTask(
      id: '7',
      title: 'Python Roadmap – Module 3',
      date: tomorrow,
      startTime: const TimeOfDay(hour: 10, minute: 0),
      endTime: const TimeOfDay(hour: 11, minute: 30),
      priority: TaskPriority.medium,
      category: TaskCategory.study,
    ),
    CalendarTask(
      id: '8',
      title: 'FYP Meeting',
      date: dayAfter,
      startTime: const TimeOfDay(hour: 14, minute: 0),
      endTime: const TimeOfDay(hour: 15, minute: 0),
      priority: TaskPriority.high,
      category: TaskCategory.meeting,
    ),
    CalendarTask(
      id: '9',
      title: 'Database Quiz',
      date: yesterday,
      startTime: const TimeOfDay(hour: 9, minute: 0),
      priority: TaskPriority.high,
      category: TaskCategory.exam,
      isCompleted: true,
    ),
    CalendarTask(
      id: '10',
      title: 'Software Engineering Presentation',
      date: nextWeek,
      startTime: const TimeOfDay(hour: 11, minute: 0),
      endTime: const TimeOfDay(hour: 12, minute: 0),
      priority: TaskPriority.high,
      category: TaskCategory.assignment,
    ),
  ];
}

class CalendarViewModel extends ChangeNotifier {
  DateTime _focusedDay = DateTime.now();
  DateTime _selectedDay = DateTime.now();
  CalendarFormat _calendarFormat = CalendarFormat.month;
  final List<CalendarTask> _allTasks = _buildPlaceholderTasks();
  TaskPriority? _filterPriority;
  TaskCategory? _filterCategory;
  bool _showPendingOnly = false;

  DateTime get focusedDay => _focusedDay;
  DateTime get selectedDay => _selectedDay;
  CalendarFormat get calendarFormat => _calendarFormat;
  TaskPriority? get filterPriority => _filterPriority;
  TaskCategory? get filterCategory => _filterCategory;
  bool get showPendingOnly => _showPendingOnly;

  List<CalendarTask> get filteredTasks {
    var tasks = _tasksForDay(_selectedDay);

    if (_filterPriority != null) {
      tasks = tasks.where((t) => t.priority == _filterPriority).toList();
    }
    if (_filterCategory != null) {
      tasks = tasks.where((t) => t.category == _filterCategory).toList();
    }
    if (_showPendingOnly) {
      tasks = tasks.where((t) => !t.isCompleted).toList();
    }

    tasks.sort((a, b) {
      if (a.isCompleted != b.isCompleted) {
        return a.isCompleted ? 1 : -1;
      }
      final aMin = a.startTime.hour * 60 + a.startTime.minute;
      final bMin = b.startTime.hour * 60 + b.startTime.minute;
      return aMin.compareTo(bMin);
    });

    return tasks;
  }

  int get selectedTotal => _tasksForDay(_selectedDay).length;

  List<CalendarTask> eventLoader(DateTime day) => _tasksForDay(day);

  void onDaySelected(DateTime selected, DateTime focused) {
    _selectedDay = selected;
    _focusedDay = focused;
    notifyListeners();
  }

  void setCalendarFormat(CalendarFormat format) {
    _calendarFormat = format;
    notifyListeners();
  }

  void setFocusedDay(DateTime focusedDay) {
    _focusedDay = focusedDay;
    notifyListeners();
  }

  void setFilterPriority(TaskPriority? priority) {
    _filterPriority = priority;
    notifyListeners();
  }

  void setFilterCategory(TaskCategory? category) {
    _filterCategory = category;
    notifyListeners();
  }

  void togglePendingOnly() {
    _showPendingOnly = !_showPendingOnly;
    notifyListeners();
  }

  void toggleTask(CalendarTask task) {
    task.isCompleted = !task.isCompleted;
    notifyListeners();
  }

  void deleteTask(CalendarTask task) {
    _allTasks.removeWhere((t) => t.id == task.id);
    notifyListeners();
  }

  void restoreTask(CalendarTask task) {
    _allTasks.add(task);
    notifyListeners();
  }

  String formatTimeRange(CalendarTask task, BuildContext context) {
    final start = task.startTime.format(context);
    if (task.endTime != null) {
      final end = task.endTime!.format(context);
      return '$start – $end';
    }
    return start;
  }

  List<CalendarTask> _tasksForDay(DateTime day) {
    final norm = _normalize(day);
    return _allTasks.where((t) => _normalize(t.date) == norm).toList();
  }

  DateTime _normalize(DateTime d) => DateTime(d.year, d.month, d.day);
}

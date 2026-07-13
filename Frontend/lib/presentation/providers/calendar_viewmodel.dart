import 'package:flutter/material.dart';
import 'package:table_calendar/table_calendar.dart';
import '../../data/models/calendar_task_model.dart';
import '../../data/repositories/calendar_screen_repository.dart';

class CalendarViewModel extends ChangeNotifier {
  final CalendarRepository _repository;

  // state
  DateTime _focusedDay = DateTime.now();
  DateTime _selectedDay = DateTime.now();
  CalendarFormat _calendarFormat = CalendarFormat.month;
  List<CalendarTask> _allTasks = [];
  bool _isLoading = false;
  String? _error;

  // filters
  TaskPriority? _filterPriority;
  bool _showPendingOnly = false;

  // getters
  DateTime get focusedDay => _focusedDay;
  DateTime get selectedDay => _selectedDay;
  CalendarFormat get calendarFormat => _calendarFormat;
  List<CalendarTask> get tasks => _allTasks;
  bool get isLoading => _isLoading;
  String? get error => _error;

  CalendarViewModel(this._repository) {
    Future.microtask(() => loadTasks());
  }

  Future<void> loadTasks() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _allTasks = await _repository.fetchCalendarTasks();
    } catch (e) {
      _error = e.toString();
      _allTasks = [];
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  List<CalendarTask> get filteredTasks {
    var tasks = _tasksForDay(_selectedDay);

    if (_filterPriority != null) {
      tasks = tasks.where((t) => t.priority == _filterPriority).toList();
    }
    // if you have category field, filter here
    if (_showPendingOnly) {
      tasks = tasks.where((t) => t.status != TaskStatus.completed).toList();
    }

    tasks.sort((a, b) {
      // completed last
      if (a.status == TaskStatus.completed && b.status != TaskStatus.completed)
        return 1;
      if (b.status == TaskStatus.completed && a.status != TaskStatus.completed)
        return -1;
      return a.dueDateTime.compareTo(b.dueDateTime);
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

  void togglePendingOnly() {
    _showPendingOnly = !_showPendingOnly;
    notifyListeners();
  }

  // ---- API operations ----
  Future<void> toggleTask(CalendarTask task) async {
    final oldStatus = task.status;
    final newStatus = oldStatus == TaskStatus.completed
        ? TaskStatus.pending
        : TaskStatus.completed;
    final index = _allTasks.indexWhere((t) => t.id == task.id);
    if (index == -1) return;

    _allTasks[index] = task.copyWith(status: newStatus);
    notifyListeners();

    try {
      await _repository.updateTask(_allTasks[index]);
    } catch (e) {
      _allTasks[index] = task.copyWith(status: oldStatus);
      notifyListeners();
      rethrow;
    }
  }

  Future<void> deleteTask(CalendarTask task) async {
    final index = _allTasks.indexWhere((t) => t.id == task.id);
    if (index == -1) return;
    final removed = _allTasks.removeAt(index);
    notifyListeners();

    try {
      await _repository.deleteTask(task.id);
    } catch (e) {
      _allTasks.insert(index, removed);
      notifyListeners();
      rethrow;
    }
  }

  Future<void> updateTask(CalendarTask updatedTask) async {
    final index = _allTasks.indexWhere((t) => t.id == updatedTask.id);
    if (index == -1) return;
    final old = _allTasks[index];
    _allTasks[index] = updatedTask;
    notifyListeners();

    try {
      await _repository.updateTask(updatedTask);
    } catch (e) {
      _allTasks[index] = old;
      notifyListeners();
      rethrow;
    }
  }

  // ---- helpers ----
  List<CalendarTask> _tasksForDay(DateTime day) {
    final norm = DateTime(day.year, day.month, day.day);
    return _allTasks.where((t) {
      final d = DateTime(
        t.dueDateTime.year,
        t.dueDateTime.month,
        t.dueDateTime.day,
      );
      return d == norm;
    }).toList();
  }

  String formatTimeRange(CalendarTask task, BuildContext context) {
    final start = task.startTime.format(context);
    final end = task.endTime.format(context);
    return '$start – $end';
  }

  // void injectDummyTasks() {
  //   if (_allTasks.isNotEmpty) return

  //   final today = DateTime.now();
  //   final todayDate = DateTime(today.year, today.month, today.day);

  //   _allTasks = [
  //     CalendarTask(
  //       id: 'd1',
  //       title: 'Meeting Teams',
  //       description: 'Discuss project status',
  //       dueDateTime: DateTime(
  //         todayDate.year,
  //         todayDate.month,
  //         todayDate.day,
  //         9,
  //         0,
  //       ),
  //       durationMinutes: 60,
  //       priority: TaskPriority.high,
  //       status: TaskStatus.pending,
  //       displayStatus: 'pending',
  //     ),
  //     CalendarTask(
  //       id: 'd2',
  //       title: 'Landing Page - Project 1',
  //       description: 'Design review',
  //       dueDateTime: DateTime(
  //         todayDate.year,
  //         todayDate.month,
  //         todayDate.day,
  //         10,
  //         0,
  //       ),
  //       durationMinutes: 150,
  //       priority: TaskPriority.medium,
  //       status: TaskStatus.pending,
  //       displayStatus: 'ongoing',
  //     ),
  //     CalendarTask(
  //       id: 'd3',
  //       title: 'Lunch with Emma',
  //       description: 'Cafe near office',
  //       dueDateTime: DateTime(
  //         todayDate.year,
  //         todayDate.month,
  //         todayDate.day,
  //         13,
  //         30,
  //       ),
  //       durationMinutes: 45,
  //       priority: TaskPriority.low,
  //       status: TaskStatus.pending,
  //       displayStatus: 'pending',
  //     ),
  //     CalendarTask(
  //       id: 'd4',
  //       title: 'Code Review – Eva App',
  //       description: 'Review pull requests',
  //       dueDateTime: DateTime(
  //         todayDate.year,
  //         todayDate.month,
  //         todayDate.day,
  //         15,
  //         0,
  //       ),
  //       durationMinutes: 90,
  //       priority: TaskPriority.medium,
  //       status: TaskStatus.pending,
  //       displayStatus: 'pending',
  //     ),
  //     CalendarTask(
  //       id: 'd5',
  //       title: 'Gym Workout',
  //       description: 'Evening session',
  //       dueDateTime: DateTime(
  //         todayDate.year,
  //         todayDate.month,
  //         todayDate.day,
  //         18,
  //         30,
  //       ),
  //       durationMinutes: 60,
  //       priority: TaskPriority.low,
  //       status: TaskStatus.pending,
  //       displayStatus: 'pending',
  //     ),
  //   ];
  //   notifyListeners();
  // }
}

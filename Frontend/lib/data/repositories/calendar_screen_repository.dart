import '../../data/models/calendar_task_model.dart';
import '../../data/services/calendar_service.dart';
import '../../data/services/storage_service.dart';

class CalendarRepository {
  final CalendarService _service;

  CalendarRepository(this._service);

  Future<String> _getToken() async {
    final token = await StorageService.getAccessToken();
    if (token == null) throw Exception('No access token found');
    return token;
  }

  Future<List<CalendarTask>> fetchCalendarTasks() async {
    final token = await _getToken();
    final jsonList = await _service.getCalendarTasks(token);
    return jsonList.map((json) => CalendarTask.fromJson(json)).toList();
  }

  Future<CalendarTask> fetchTaskDetail(String taskId) async {
    final token = await _getToken();
    final json = await _service.getTaskDetail(token, taskId);
    return CalendarTask.fromJson(json);
  }

  Future<void> updateTask(CalendarTask task) async {
    final token = await _getToken();
    await _service.updateTask(token, task.id, task.toJson());
  }

  Future<void> deleteTask(String taskId) async {
    final token = await _getToken();
    await _service.deleteTask(token, taskId);
  }
}

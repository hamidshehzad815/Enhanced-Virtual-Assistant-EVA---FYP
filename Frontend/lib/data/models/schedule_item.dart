class ScheduleItem {
  final String title;
  final String status;
  final String time;
  final String? taskId;
  final DateTime? taskDate;

  ScheduleItem({
    required this.title,
    required this.status,
    required this.time,
    this.taskId,
    this.taskDate,
  });

  factory ScheduleItem.fromJson(Map<String, dynamic> json) {
    return ScheduleItem(
      title: json['title'] ?? '',
      status: json['display_status'] ?? '',
      time: json['time'] ?? '',
      taskId: json['task_id'] as String?,
      taskDate: json['due_date'] != null
          ? DateTime.parse(json['due_date'])
          : null,
    );
  }
}
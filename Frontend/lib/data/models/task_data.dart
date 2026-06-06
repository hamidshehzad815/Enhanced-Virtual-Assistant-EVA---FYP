class TaskData {
  final String title;
  final String day;
  final String taskTime;

  TaskData({
    required this.title,
    required this.day,
    required this.taskTime,
  });

  factory TaskData.fromJson(
    Map<String, dynamic> json,
  ) {
    return TaskData(
      title: json['title'] ?? '',
      day: json['day'] ?? '',
      taskTime: json['time'] ?? '',
    );
  }
}
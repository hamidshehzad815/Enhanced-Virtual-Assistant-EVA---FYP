class ScheduleItem {
  final String title;
  final String status;
  final String time;

  ScheduleItem({
    required this.title,
    required this.status,
    required this.time,
  });

  factory ScheduleItem.fromJson(
    Map<String, dynamic> json,
  ) {
    return ScheduleItem(
      title: json['title'] ?? '',
      status: json['display_status'] ?? '',
      time: json['time'] ?? '',
    );
  }
}
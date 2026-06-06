class ScheduleItem {
  final String title;
  final String tag;
  final DateTime time;

  ScheduleItem({
    required this.title,
    required this.tag,
    required this.time,
  });

  factory ScheduleItem.fromJson(
    Map<String, dynamic> json,
  ) {
    return ScheduleItem(
      title: json['title'] ?? '',
      tag: json['display_status'] ?? '',
      time: DateTime.now(),
    );
  }
}
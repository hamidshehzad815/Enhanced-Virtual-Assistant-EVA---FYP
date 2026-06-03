/// Schedule item model - ready for API integration
class ScheduleItem {
  final DateTime time;
  final String title;
  final String tag; // e.g., complete , pending , ongoing , due 

  ScheduleItem({
    required this.time,
    required this.title,
    required this.tag,
  });

  /// Convert to JSON for API calls
  Map<String, dynamic> toJson() {
    return {'time': time.toIso8601String(), 'title': title};
  }

  /// Create from JSON API response
  factory ScheduleItem.fromJson(Map<String, dynamic> json) {
    return ScheduleItem(
      time: DateTime.parse(json['time'] as String),
      title: json['title'] as String,
      tag: json['tag'] as String,
    );
  }
}

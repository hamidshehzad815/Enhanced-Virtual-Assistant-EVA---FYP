class UpNextData {
  final String title;
  final String day;
  final String time;

  UpNextData({
    required this.title,
    required this.day,
    required this.time,
  });

  factory UpNextData.fromJson(
    Map<String, dynamic> json,
  ) {
    return UpNextData(
      title: json['title'] ?? '',
      day: json['day'] ?? '',
      time: json['time'] ?? '',
    );
  }
}
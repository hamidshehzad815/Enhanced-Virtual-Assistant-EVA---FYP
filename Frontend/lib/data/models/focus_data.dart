class FocusData {
  final String title;
  final String nextTopic;
  final DateTime nextTopicTime;

  FocusData({
    required this.title,
    required this.nextTopic,
    required this.nextTopicTime,
  });

  factory FocusData.fromJson(
    Map<String, dynamic> json,
  ) {
    return FocusData(
      title: json['title'] ?? '',
      nextTopic:
          json['next_topic']['title'] ?? '',
      nextTopicTime: DateTime.parse(
        json['next_topic']
            ['scheduled_datetime'],
      ),
    );
  }
}
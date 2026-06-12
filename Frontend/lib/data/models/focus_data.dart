class FocusData {
  final String title;
  final String nextTopic;
  final String nextTopicTime;

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
      nextTopicTime: json['next_topic']['time'] ?? '',
    );
  }
}
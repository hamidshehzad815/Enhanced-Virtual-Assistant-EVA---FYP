/// Focus/Roadmap data model - ready for API integration
class FocusData {
  final String title;
  final String nextTopic;
  final DateTime nextTopicTime;

  FocusData({
    required this.title,
    required this.nextTopic,
    required this.nextTopicTime,
  });

  /// Convert to JSON for API calls
  Map<String, dynamic> toJson() {
    return {
      'title': title,
      'nextTopic': nextTopic,
    };
  }

  /// Create from JSON API response
  factory FocusData.fromJson(Map<String, dynamic> json) {
    return FocusData(
      title: json['title'] as String,
      nextTopic: json['nextTopic'] as String,
      nextTopicTime: DateTime.parse(json['nextTopicTime'] as String),
    );
  }
}

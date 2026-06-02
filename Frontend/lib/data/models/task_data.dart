/// Task data model - ready for API integration
class TaskData {
  final String title;
  final String subtitle;
  final int icon; // IconData value
  final int cardColor; // Color value
  final int iconColor; // Color value

  TaskData({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.cardColor,
    required this.iconColor,
  });

  /// Convert to JSON for API calls
  Map<String, dynamic> toJson() {
    return {
      'title': title,
      'subtitle': subtitle,
      'icon': icon,
      'cardColor': cardColor,
      'iconColor': iconColor,
    };
  }

  /// Create from JSON API response
  factory TaskData.fromJson(Map<String, dynamic> json) {
    return TaskData(
      title: json['title'] as String,
      subtitle: json['subtitle'] as String,
      icon: json['icon'] as int,
      cardColor: json['cardColor'] as int,
      iconColor: json['iconColor'] as int,
    );
  }
}

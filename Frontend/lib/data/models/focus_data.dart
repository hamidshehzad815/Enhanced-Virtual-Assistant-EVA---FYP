import 'package:intl/intl.dart';

class FocusData {
  final String title;
  final String nextTopic;
  final String nextTopicTime; // keep this – but we'll change its value
  final DateTime scheduledDateTime; // new field

  FocusData({
    required this.title,
    required this.nextTopic,
    required this.nextTopicTime,
    required this.scheduledDateTime,
  });

  factory FocusData.fromJson(Map<String, dynamic> json) {
    final nextTopicJson = json['next_topic'] ?? {};
    final scheduledDT = DateTime.parse(nextTopicJson['scheduled_datetime']).toLocal();

    // Format: "Jun 5, 7:00 PM"
    final formatted = DateFormat('MMM d, h:mm a').format(scheduledDT);

    return FocusData(
      title: json['title'] ?? '',
      nextTopic: nextTopicJson['title'] ?? '',
      nextTopicTime: formatted, // now contains date + time
      scheduledDateTime: scheduledDT,
    );
  }
}
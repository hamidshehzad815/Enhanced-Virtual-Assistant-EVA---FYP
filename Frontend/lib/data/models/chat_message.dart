/// Chat message model with status and helpers.
/// Use this shared model from UI, service, repository, and viewmodel layers.
enum MessageStatus { sending, sent, failed }

class ChatMessage {
  final String id;
  final String text;
  final bool isEva;
  final DateTime timestamp;
  final MessageStatus status;

  ChatMessage({
    required this.id,
    required this.text,
    required this.isEva,
    required this.timestamp,
    this.status = MessageStatus.sent,
  });

  bool get isSentByMe => !isEva;

  /// Format time as 12-hour clock with AM/PM
  String get formattedTime {
    final h = timestamp.hour;
    final m = timestamp.minute.toString().padLeft(2, '0');
    final period = h >= 12 ? 'PM' : 'AM';
    final hour = h > 12 ? h - 12 : (h == 0 ? 12 : h);
    return '$hour:$m $period';
  }

  /// Convert to JSON for API calls
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'text': text,
      'isEva': isEva,
      'timestamp': timestamp.toIso8601String(),
      'status': status.name,
    };
  }

  /// Create from JSON API response
  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id:
          json['id'] as String? ??
          DateTime.now().millisecondsSinceEpoch.toString(),
      text: json['text'] as String,
      isEva: json['isEva'] as bool? ?? false,
      timestamp: json['timestamp'] != null
          ? DateTime.parse(json['timestamp'] as String)
          : DateTime.now(),
      status: MessageStatus.values.firstWhere(
        (value) => value.name == (json['status'] as String? ?? 'sent'),
        orElse: () => MessageStatus.sent,
      ),
    );
  }

  factory ChatMessage.fromUser(String text) => ChatMessage(
    id: DateTime.now().millisecondsSinceEpoch.toString(),
    text: text,
    isEva: false,
    timestamp: DateTime.now(),
  );

  factory ChatMessage.fromEva(String text) => ChatMessage(
    id: '${DateTime.now().millisecondsSinceEpoch}_eva',
    text: text,
    isEva: true,
    timestamp: DateTime.now(),
  );

  ChatMessage copyWith({
    String? id,
    String? text,
    bool? isEva,
    DateTime? timestamp,
    MessageStatus? status,
  }) {
    return ChatMessage(
      id: id ?? this.id,
      text: text ?? this.text,
      isEva: isEva ?? this.isEva,
      timestamp: timestamp ?? this.timestamp,
      status: status ?? this.status,
    );
  }
}

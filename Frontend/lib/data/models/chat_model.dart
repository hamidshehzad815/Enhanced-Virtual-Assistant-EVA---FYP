class SessionSummary {
  final String id;
  final String title;
  final String lastMessagePreview;
  final DateTime? lastMessageAt;
  final DateTime createdAt;
  final DateTime updatedAt;

  SessionSummary({
    required this.id,
    required this.title,
    required this.lastMessagePreview,
    this.lastMessageAt,
    required this.createdAt,
    required this.updatedAt,
  });

  factory SessionSummary.fromJson(Map<String, dynamic> json) {
    return SessionSummary(
      id: json['id'],
      title: json['title'] ?? 'New Chat',
      lastMessagePreview: json['last_message_preview'] ?? '',
      lastMessageAt: json['last_message_at'] != null
          ? DateTime.parse(json['last_message_at'])
          : null,
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }
}

class ChatAction {
  final String type;
  final String id;
  final String label;

  ChatAction({
    required this.type,
    required this.id,
    required this.label,
  });

  factory ChatAction.fromJson(Map<String, dynamic> json) {
    return ChatAction(
      type: (json['type'] ?? '').toString(),
      id: (json['id'] ?? '').toString(),
      label: (json['label'] ?? 'Open').toString(),
    );
  }

  Map<String, dynamic> toJson() => {
        'type': type,
        'id': id,
        'label': label,
      };
}

class ChatMessage {
  final String id;
  final String role; // "user" or "eva"
  final String content;
  final String inputType; // "text" or "voice"
  final String? intent;
  final String status; // "processed", "pending", "failed"
  final DateTime createdAt;
  final ChatAction? action;

  ChatMessage({
    required this.id,
    required this.role,
    required this.content,
    this.inputType = 'text',
    this.intent,
    this.status = 'processed',
    required this.createdAt,
    this.action,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    final rawAction = json['action'];
    return ChatMessage(
      id: json['id'],
      role: json['role'],
      content: json['content'],
      inputType: json['input_type'] ?? 'text',
      intent: json['intent'],
      status: json['status'] ?? 'processed',
      createdAt: DateTime.parse(json['created_at']),
      action: rawAction is Map<String, dynamic>
          ? ChatAction.fromJson(rawAction)
          : (rawAction is Map ? ChatAction.fromJson(Map<String, dynamic>.from(rawAction)) : null),
    );
  }
}

class ProcessResponse {
  final String sessionId;
  final bool sessionCreated;
  final String title;
  final String responseText;
  final String? intent;
  final String? aiStatus;
  final NotificationSummary? notifications;
  final ChatAction? action;

  ProcessResponse({
    required this.sessionId,
    required this.sessionCreated,
    required this.title,
    required this.responseText,
    this.intent,
    this.aiStatus,
    this.notifications,
    this.action,
  });

  factory ProcessResponse.fromJson(Map<String, dynamic> json) {
    final rawAction = json['action'];
    return ProcessResponse(
      sessionId: json['session_id'],
      sessionCreated: json['session_created'] ?? false,
      title: json['title'] ?? '',
      responseText: json['response_text'] ?? '',
      intent: json['intent'],
      aiStatus: json['ai_status'],
      notifications: json['notifications'] != null
          ? NotificationSummary.fromJson(json['notifications'])
          : null,
      action: rawAction is Map<String, dynamic>
          ? ChatAction.fromJson(rawAction)
          : (rawAction is Map ? ChatAction.fromJson(Map<String, dynamic>.from(rawAction)) : null),
    );
  }
}

class NotificationSummary {
  final int requested;
  final int inserted;
  final int dispatchedPush;
  final int dispatchedEmail;
  final int failed;
  final List<dynamic> results;

  NotificationSummary({
    this.requested = 0,
    this.inserted = 0,
    this.dispatchedPush = 0,
    this.dispatchedEmail = 0,
    this.failed = 0,
    this.results = const [],
  });

  factory NotificationSummary.fromJson(Map<String, dynamic> json) {
    return NotificationSummary(
      requested: json['requested'] ?? 0,
      inserted: json['inserted'] ?? 0,
      dispatchedPush: json['dispatched_push'] ?? 0,
      dispatchedEmail: json['dispatched_email'] ?? 0,
      failed: json['failed'] ?? 0,
      results: json['results'] ?? [],
    );
  }
}

class SessionsResponse {
  final List<SessionSummary> sessions;

  SessionsResponse({required this.sessions});

  factory SessionsResponse.fromJson(Map<String, dynamic> json) {
    final list = json['data']?['sessions'] as List? ?? [];
    return SessionsResponse(
      sessions: list.map((s) => SessionSummary.fromJson(s)).toList(),
    );
  }
}

class MessagesResponse {
  final String sessionId;
  final String title;
  final List<ChatMessage> messages;

  MessagesResponse({
    required this.sessionId,
    required this.title,
    required this.messages,
  });

  factory MessagesResponse.fromJson(Map<String, dynamic> json) {
    final data = json['data'];
    return MessagesResponse(
      sessionId: data['session_id'],
      title: data['title'] ?? '',
      messages:
          (data['messages'] as List?)
              ?.map((m) => ChatMessage.fromJson(m))
              .toList() ??
          [],
    );
  }
}

// lib/data/models/app_notification.dart
//
// In-app notification (dashboard bell). See Api's documentation/notifications-api.md.

class NotificationSender {
  final String id;
  final String? name;
  final String? username;
  final String? profilePicture;

  NotificationSender({
    required this.id,
    this.name,
    this.username,
    this.profilePicture,
  });

  factory NotificationSender.fromJson(Map<String, dynamic> json) {
    return NotificationSender(
      id: json['_id']?.toString() ?? '',
      name: json['name']?.toString(),
      username: json['username']?.toString(),
      profilePicture: json['profile_picture']?.toString(),
    );
  }
}

class AppNotification {
  final String id;
  final String type;
  final String title;
  final String message;
  final String? referenceType;
  final String? referenceId;
  final bool isRead;
  final bool actionRequired;
  final String? actionTaken; // 'accepted' | 'rejected' | null
  final DateTime? createdAt;
  final NotificationSender? sender;

  AppNotification({
    required this.id,
    required this.type,
    required this.title,
    required this.message,
    this.referenceType,
    this.referenceId,
    this.isRead = false,
    this.actionRequired = false,
    this.actionTaken,
    this.createdAt,
    this.sender,
  });

  /// A collaboration invite that can be accepted/rejected in-app.
  bool get isInvite =>
      type == 'collaboration_invite' ||
      type == 'learning_collaboration_invite';

  /// Whether Accept/Reject buttons should be shown for this notification.
  bool get canRespond => isInvite && actionRequired && actionTaken == null;

  factory AppNotification.fromJson(Map<String, dynamic> json) {
    final createdRaw = json['created_at']?.toString();
    return AppNotification(
      id: json['_id']?.toString() ?? '',
      type: json['type']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      message: json['message']?.toString() ?? '',
      referenceType: json['reference_type']?.toString(),
      referenceId: json['reference_id']?.toString(),
      isRead: json['is_read'] == true,
      actionRequired: json['action_required'] == true,
      actionTaken: json['action_taken']?.toString(),
      createdAt: createdRaw != null ? DateTime.tryParse(createdRaw) : null,
      sender: json['sender'] is Map<String, dynamic>
          ? NotificationSender.fromJson(json['sender'])
          : null,
    );
  }

  AppNotification copyWith({bool? isRead, String? actionTaken}) {
    return AppNotification(
      id: id,
      type: type,
      title: title,
      message: message,
      referenceType: referenceType,
      referenceId: referenceId,
      isRead: isRead ?? this.isRead,
      actionRequired: actionRequired,
      actionTaken: actionTaken ?? this.actionTaken,
      createdAt: createdAt,
      sender: sender,
    );
  }
}

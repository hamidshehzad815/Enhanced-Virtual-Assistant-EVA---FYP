import 'package:flutter/material.dart';

/// Conversation summary model for the collaboration screen.
class ConversationModel {
  final String id;
  final String displayName;
  final String avatarInitials;
  final Color avatarColor;
  final String lastMessage;
  final String timestamp;
  final int unreadCount;

  const ConversationModel({
    required this.id,
    required this.displayName,
    required this.avatarInitials,
    required this.avatarColor,
    required this.lastMessage,
    required this.timestamp,
    this.unreadCount = 0,
  });

  bool get hasUnread => unreadCount > 0;
}

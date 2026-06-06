/// Conversation summary model for chat history.
class ConversationModel {
  final String id;
  final String title;
  final String lastMessage;
  final DateTime lastUpdated;

  const ConversationModel({
    required this.id,
    required this.title,
    required this.lastMessage,
    required this.lastUpdated,
  });

  String get timeAgo {
    final diff = DateTime.now().difference(lastUpdated);
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    return '${diff.inDays}d ago';
  }
}

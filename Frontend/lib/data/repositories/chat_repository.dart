import '../models/chat_message.dart';
import '../services/chat_service.dart';

/// Repository pattern - Single responsibility: Data access layer
/// Abstracts data source (API, local DB, mock) from business logic
abstract class IChatRepository {
  Future<List<ChatMessage>> getMessages();
  Future<void> sendMessage(String text);
  Stream<List<ChatMessage>> messagesStream();
}

/// Implementation using ChatService as datasource
class ChatRepository implements IChatRepository {
  final ChatService _chatService;

  ChatRepository({ChatService? chatService})
    : _chatService = chatService ?? ChatService();

  @override
  Future<List<ChatMessage>> getMessages() async {
    try {
      return await _chatService.fetchMessages();
    } catch (e) {
      rethrow;
    }
  }

  @override
  Future<void> sendMessage(String text) async {
    if (text.trim().isEmpty) {
      throw ArgumentError('Message cannot be empty');
    }
    try {
      await _chatService.sendMessage(text);
    } catch (e) {
      rethrow;
    }
  }

  @override
  Stream<List<ChatMessage>> messagesStream() {
    return _chatService.messagesStream();
  }
}

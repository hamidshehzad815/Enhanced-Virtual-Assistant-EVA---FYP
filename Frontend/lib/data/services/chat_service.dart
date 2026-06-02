import 'dart:async';
import '../models/chat_message.dart';

/// Service layer - Single responsibility: Handle API communication
/// In production, replace mock data with actual API calls
class ChatService {
  final List<ChatMessage> _messages = [];
  final StreamController<List<ChatMessage>> _messagesController =
      StreamController<List<ChatMessage>>.broadcast();

  ChatService() {
    _initializeMockData();
  }

  /// Initialize with mock data - Replace with API call in production
  void _initializeMockData() {
    _messages.addAll([
      ChatMessage(
        id: '1',
        text: "Hi there!",
        isEva: false,
        timestamp: DateTime.now().subtract(const Duration(hours: 2)),
      ),
      ChatMessage(
        id: '2',
        text: "Hello! How can I help you today?",
        isEva: true,
        timestamp: DateTime.now().subtract(
          const Duration(hours: 2, minutes: 1),
        ),
      ),
      ChatMessage(
        id: '3',
        text: "Schedule my NLP exam due on coming Monday.",
        isEva: false,
        timestamp: DateTime.now().subtract(
          const Duration(hours: 2, minutes: 2),
        ),
      ),
      ChatMessage(
        id: '4',
        text: "Sure! I've added your NLP exam to your schedule for Monday.",
        isEva: true,
        timestamp: DateTime.now().subtract(
          const Duration(hours: 2, minutes: 3),
        ),
      ),
    ]);
    _messagesController.add(List.from(_messages));
  }

  /// Fetch messages - Ready for API integration
  /// In production: return await _apiClient.get('/chat/messages');
  Future<List<ChatMessage>> fetchMessages() async {
    // TODO: Replace with actual API call
    // return await _apiClient.get('/messages').then((response) =>
    //   (response as List).map((m) => ChatMessage.fromJson(m)).toList());
    return Future.value(List.from(_messages));
  }

  /// Get in-memory messages (for quick access)
  List<ChatMessage> getMessages() => List.from(_messages);

  /// Stream of messages for real-time updates
  Stream<List<ChatMessage>> messagesStream() => _messagesController.stream;

  /// Send message - Ready for API integration
  /// In production: await _apiClient.post('/messages', data: {'text': text});
  Future<void> sendMessage(String text) async {
    if (text.trim().isEmpty) return;

    // Create user message
    final userMessage = ChatMessage(
      id: '5',
      text: text,
      isEva: false,
      timestamp: DateTime.now(),
    );

    _messages.add(userMessage);
    _messagesController.add(List.from(_messages));

    // TODO: Send to API here
    // await _apiClient.post('/messages', data: userMessage.toJson());

    // Simulate API response after delay
    await Future.delayed(const Duration(milliseconds: 800));

    final botResponse = ChatMessage(
      id: '6',
      text: "Thanks for your message! Hard coded reponse",
      isEva: true,
      timestamp: DateTime.now(),
    );

    _messages.add(botResponse);
    _messagesController.add(List.from(_messages));
  }

  /// Cleanup resources
  void dispose() {
    _messagesController.close();
  }
}

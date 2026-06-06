import 'package:flutter/foundation.dart';
import '../../data/models/chat_message.dart';
import '../../data/repositories/chat_repository.dart';

/// ViewModel for Chat - Single responsibility: Business logic & state management
/// Handles all chat-related logic without knowing about UI details
class ChatViewModel extends ChangeNotifier {
  final ChatRepository _repository;

  List<ChatMessage> _messages = [];
  bool _isLoading = false;
  String? _error;

  ChatViewModel({ChatRepository? repository})
    : _repository = repository ?? ChatRepository();

  // Getters
  List<ChatMessage> get messages => List.unmodifiable(_messages);
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get hasMessages => _messages.isNotEmpty;

  /// Load messages from repository
  Future<void> loadMessages() async {
    _setLoading(true);
    _clearError();

    try {
      _messages = await _repository.getMessages();
      notifyListeners();
    } catch (e) {
      _setError('Failed to load messages: $e');
    } finally {
      _setLoading(false);
    }
  }

  /// Send a new message
  Future<void> sendMessage(String text) async {
    if (text.trim().isEmpty) {
      _setError('Message cannot be empty');
      return;
    }

    _clearError();

    try {
      await _repository.sendMessage(text);
      // Reload messages after sending
      _messages = await _repository.getMessages();
      notifyListeners();
    } catch (e) {
      _setError('Failed to send message: $e');
    }
  }

  /// Listen to real-time message updates
  void subscribeToMessages() {
    _repository.messagesStream().listen(
      (messages) {
        _messages = messages;
        notifyListeners();
      },
      onError: (error) {
        _setError('Stream error: $error');
      },
    );
  }

  /// Clear all messages
  void clearMessages() {
    _messages.clear();
    _clearError();
    notifyListeners();
  }

  // Private helpers
  void _setLoading(bool value) {
    _isLoading = value;
    notifyListeners();
  }

  void _setError(String? value) {
    _error = value;
    notifyListeners();
  }

  void _clearError() {
    _error = null;
  }
}

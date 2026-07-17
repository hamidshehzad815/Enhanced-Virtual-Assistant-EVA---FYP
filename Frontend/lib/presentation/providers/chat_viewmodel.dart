// lib/presentation/providers/chat_viewmodel.dart
import 'package:flutter/material.dart';
import '../../data/models/chat_model.dart';
import '../../data/repositories/chat_repository.dart';

class ChatViewModel extends ChangeNotifier {
  final ChatRepository _repository;

  // ─── State ──────────────────────────────────────────────────────────
  List<SessionSummary> _sessions = [];
  List<ChatMessage> _messages = [];
  String? _currentSessionId;
  bool _isLoading = false;
  bool _isSending = false;
  String? _error;

  ChatViewModel(this._repository) {
    // Load sessions on creation if you want, or call explicitly.
  }

  // ─── Getters ────────────────────────────────────────────────────────
  List<SessionSummary> get sessions => _sessions;
  List<ChatMessage> get messages => _messages;
  String? get currentSessionId => _currentSessionId;
  bool get isLoading => _isLoading;
  bool get isSending => _isSending;
  String? get error => _error;

  // ─── Load sessions ──────────────────────────────────────────────────
  Future<void> loadSessions({int limit = 50}) async {
    _setLoading(true);
    try {
      _sessions = await _repository.getSessions(limit: limit);
      _error = null;
    } catch (e) {
      _error = e.toString();
      _sessions = [];
    } finally {
      _setLoading(false);
    }
  }

  // ─── Load messages for a session ────────────────────────────────────
  Future<void> loadMessages(String sessionId) async {
    if (sessionId.isEmpty) {
      _messages = [];
      _currentSessionId = null;
      notifyListeners();
      return;
    }
    _setLoading(true);
    try {
      final response = await _repository.getMessages(sessionId);
      _messages = response.messages;
      _currentSessionId = sessionId;
      _error = null;
    } catch (e) {
      _error = e.toString();
      _messages = [];
    } finally {
      _setLoading(false);
    }
  }

  // ─── Start a new chat (draft) ──────────────────────────────────────
  void startNewChat() {
    _messages = [];
    _currentSessionId = null;
    _error = null;
    notifyListeners();
  }

  // ─── Send a message ────────────────────────────────────────────────
  Future<ProcessResponse> sendMessage(
    String message, {
    String? sessionId,
    String inputType = 'text',
  }) async {
    // optimistic update
    final tempId = 'temp-${DateTime.now().millisecondsSinceEpoch}';
    final tempMessage = ChatMessage(
      id: tempId,
      role: 'user',
      content: message,
      inputType: inputType,
      status: 'pending',
      createdAt: DateTime.now(),
    );
    _messages.add(tempMessage);
    _isSending = true;
    notifyListeners();

    try {
      final response = await _repository.sendMessage(
        message,
        sessionId: sessionId ?? _currentSessionId,
        inputType: inputType,
      );

      // Replace temp with real message or keep (messages are stored)
      // Remove temp and add both real user & EVA messages? Actually the response only gives EVA text.
      // We'll remove the temp and append real messages.
      _messages.removeWhere((m) => m.id == tempId);
      // Add a real user message? The backend has already stored it, but we don't get it back.
      // We can keep the temp as the real user message (replace id with actual if needed)
      // Better: fetch messages again? Or keep our own.
      // We'll keep our temp user message and add EVA response.
      final realUserMessage = ChatMessage(
        id: tempId, // keep the same id, or we could use a placeholder
        role: 'user',
        content: message,
        inputType: inputType,
        status: 'processed',
        createdAt: DateTime.now(),
      );
      _messages.removeWhere((m) => m.id == tempId);
      _messages.add(realUserMessage);

      final evaMessage = ChatMessage(
        id: 'eva-${DateTime.now().millisecondsSinceEpoch}',
        role: 'eva',
        content: response.responseText,
        inputType: 'text',
        intent: response.intent,
        status: 'processed',
        createdAt: DateTime.now(),
        action: response.action,
      );
      _messages.add(evaMessage);

      // Update session id
      if (response.sessionCreated) {
        _currentSessionId = response.sessionId;
        // Refresh sessions list
        await loadSessions();
      } else if (_currentSessionId == null) {
        _currentSessionId = response.sessionId;
      }

      _error = null;
      _isSending = false;
      notifyListeners();
      return response;
    } catch (e) {
      // Remove temp message
      _messages.removeWhere((m) => m.id == tempId);
      _error = e.toString();
      _isSending = false;
      notifyListeners();
      rethrow;
    }
  }

  // ─── Delete a session ──────────────────────────────────────────────
  Future<void> deleteSession(String sessionId) async {
    try {
      await _repository.deleteSession(sessionId);
      // Remove from list
      _sessions.removeWhere((s) => s.id == sessionId);
      if (_currentSessionId == sessionId) {
        _messages = [];
        _currentSessionId = null;
      }
      _error = null;
      notifyListeners();
    } catch (e) {
      _error = e.toString();
      rethrow;
    }
  }

  void _setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }
}
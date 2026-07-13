// lib/data/repositories/chat_repository.dart
import '../models/chat_model.dart';
import '../services/chat_service.dart';
import '../services/storage_service.dart';

class ChatRepository {
  final ChatService _service;

  ChatRepository(this._service);

  Future<String> _getToken() async {
    final token = await StorageService.getAccessToken();
    if (token == null) throw Exception('No access token');
    return token;
  }

  Future<List<SessionSummary>> getSessions({int limit = 50}) async {
    final token = await _getToken();
    return await _service.getSessions(token, limit: limit);
  }

  Future<MessagesResponse> getMessages(String sessionId, {int limit = 100}) async {
    final token = await _getToken();
    return await _service.getMessages(token, sessionId, limit: limit);
  }

  Future<ProcessResponse> sendMessage(
    String message, {
    String? sessionId,
    String inputType = 'text',
  }) async {
    final token = await _getToken();
    return await _service.sendMessage(token, message, sessionId: sessionId, inputType: inputType);
  }

  Future<void> deleteSession(String sessionId) async {
    final token = await _getToken();
    return await _service.deleteSession(token, sessionId);
  }
}
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../../core/constants/api_constants.dart';
import '../models/chat_model.dart';

class ChatService {
  Future<List<SessionSummary>> getSessions(
    String token, {
    int limit = 50,
  }) async {
    final response = await http.get(
      Uri.parse('${AppConstants.baseUrl}/chat/sessions?limit=$limit'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode == 200) {
      final json = jsonDecode(response.body);
      return SessionsResponse.fromJson(json).sessions;
    } else {
      throw Exception('Failed to load sessions: ${response.statusCode}');
    }
  }

  Future<MessagesResponse> getMessages(
    String token,
    String sessionId, {
    int limit = 100,
  }) async {
    final response = await http.get(
      Uri.parse(
        '${AppConstants.baseUrl}/chat/sessions/$sessionId/messages?limit=$limit',
      ),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode == 200) {
      final json = jsonDecode(response.body);
      return MessagesResponse.fromJson(json);
    } else {
      throw Exception('Failed to load messages: ${response.statusCode}');
    }
  }

  Future<ProcessResponse> sendMessage(
    String token,
    String message, {
    String? sessionId,
    String inputType = 'text',
  }) async {
    final body = <String, dynamic>{'message': message, 'input_type': inputType};
    if (sessionId != null) body['session_id'] = sessionId;

    final response = await http.post(
      Uri.parse('${AppConstants.baseUrl}/chat/process'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode(body),
    );
    if (response.statusCode == 200) {
      final json = jsonDecode(response.body);
      return ProcessResponse.fromJson(json);
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['message'] ?? 'Failed to send message');
    }
  }

  Future<void> deleteSession(String token, String sessionId) async {
    final response = await http.delete(
      Uri.parse('${AppConstants.baseUrl}/chat/sessions/$sessionId'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode != 200) {
      final error = jsonDecode(response.body);
      throw Exception(error['message'] ?? 'Failed to delete session');
    }
  }
}

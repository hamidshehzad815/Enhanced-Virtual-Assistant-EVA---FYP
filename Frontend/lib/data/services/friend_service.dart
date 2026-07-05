// lib/data/services/friends_service.dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../../core/constants/api_constants.dart';
import '../models/friend_model.dart';

class FriendsService {
Future<FriendListResponse> getFriends(String token) async {
  final response = await http.get(
    Uri.parse('${AppConstants.baseUrl}/friends'),
    headers: {'Authorization': 'Bearer $token'},
  );
  if (response.statusCode == 200) {
    final json = jsonDecode(response.body);
    return FriendListResponse.fromJson(json);
  } else {
    throw Exception('Failed to load friends: ${response.statusCode}');
  }
}

  Future<List<Friendship>> getFriendRequests(
    String token, {
    String type = 'incoming',
  }) async {
    final response = await http.get(
      Uri.parse('${AppConstants.baseUrl}/friends/requests?type=$type'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode == 200) {
      final json = jsonDecode(response.body);
      final list = json['data']?['requests'] as List? ?? [];
      return list.map((f) => Friendship.fromJson(f)).toList();
    } else {
      throw Exception('Failed to load friend requests: ${response.statusCode}');
    }
  }

  Future<List<SearchUserResult>> searchUsers(
    String token,
    String query, {
    int limit = 10,
  }) async {
    final response = await http.get(
      Uri.parse('${AppConstants.baseUrl}/friends/search?q=$query&limit=$limit'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode == 200) {
      final json = jsonDecode(response.body);
      final list = json['data']?['users'] as List? ?? [];
      return list.map((u) => SearchUserResult.fromJson(u)).toList();
    } else {
      throw Exception('Failed to search users: ${response.statusCode}');
    }
  }

  Future<Friendship> sendFriendRequest(
    String token, {
    String? username,
    String? email,
  }) async {
    final body = <String, String>{};
    if (username != null) body['username'] = username;
    if (email != null) body['email'] = email;

    final response = await http.post(
      Uri.parse('${AppConstants.baseUrl}/friends/request'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode(body),
    );
    if (response.statusCode == 200 || response.statusCode == 201) {
      final json = jsonDecode(response.body);
      return Friendship.fromJson(json['data']?['friendship'] ?? {});
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['message'] ?? 'Failed to send friend request');
    }
  }

  Future<Friendship> respondFriendRequest(
    String token,
    String friendshipId,
    String action, // 'accept' or 'reject'
  ) async {
    final response = await http.patch(
      Uri.parse('${AppConstants.baseUrl}/friends/$friendshipId/respond'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({'action': action}),
    );
    if (response.statusCode == 200) {
      final json = jsonDecode(response.body);
      return Friendship.fromJson(json['data']?['friendship'] ?? {});
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['message'] ?? 'Failed to respond to friend request');
    }
  }

  Future<void> unfriend(String token, String friendshipId) async {
    final response = await http.delete(
      Uri.parse('${AppConstants.baseUrl}/friends/$friendshipId'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode != 200) {
      final error = jsonDecode(response.body);
      throw Exception(error['message'] ?? 'Failed to unfriend');
    }
  }
}
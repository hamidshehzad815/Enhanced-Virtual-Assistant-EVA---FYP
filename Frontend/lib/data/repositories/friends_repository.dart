// lib/data/repositories/friends_repository.dart
import '../models/friend_model.dart';
import '../services/friend_service.dart';
import '../services/storage_service.dart';

class FriendsRepository {
  final FriendsService _service;

  FriendsRepository(this._service);

  Future<String> _getToken() async {
    final token = await StorageService.getAccessToken();
    if (token == null) throw Exception('No access token');
    return token;
  }

Future<FriendListResponse> getFriends() async {
  final token = await _getToken();
  return await _service.getFriends(token);
}

  Future<List<Friendship>> getFriendRequests({String type = 'incoming'}) async {
    final token = await _getToken();
    return await _service.getFriendRequests(token, type: type);
  }

  Future<List<SearchUserResult>> searchUsers(String query, {int limit = 10}) async {
    final token = await _getToken();
    return await _service.searchUsers(token, query, limit: limit);
  }

  Future<Friendship> sendFriendRequest({String? username, String? email}) async {
    final token = await _getToken();
    return await _service.sendFriendRequest(token, username: username, email: email);
  }

  Future<Friendship> respondFriendRequest(String friendshipId, String action) async {
    final token = await _getToken();
    return await _service.respondFriendRequest(token, friendshipId, action);
  }

  Future<void> unfriend(String friendshipId) async {
    final token = await _getToken();
    return await _service.unfriend(token, friendshipId);
  }
}
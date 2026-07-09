// lib/presentation/providers/friends_viewmodel.dart
import 'package:flutter/material.dart';
import '../../data/models/friend_model.dart';
import '../../data/repositories/friends_repository.dart';

class FriendsViewModel extends ChangeNotifier {
  final FriendsRepository _repository;

  List<Friendship> _friends = [];
  List<Friendship> _pendingRequests = [];
  List<SearchUserResult> _searchResults = [];
  bool _isLoading = false;
  bool _isSearching = false;
  String? _error;

  Quote? _dailyQuote;
  Quote? get dailyQuote => _dailyQuote;

  FriendsViewModel(this._repository);

  List<Friendship> get friends => _friends;
  List<Friendship> get pendingRequests => _pendingRequests;
  List<SearchUserResult> get searchResults => _searchResults;
  bool get isLoading => _isLoading;
  bool get isSearching => _isSearching;
  String? get error => _error;

  // ─── Load friends ──────────────────────────────────────────────────────
  Future<void> loadFriends() async {
    _setLoading(true);
    try {
      final response = await _repository.getFriends();
      _friends = response.friends;
      _dailyQuote = response.quote;
      _error = null;
    } catch (e) {
      _error = e.toString();
      _friends = [];
      _dailyQuote = null;
    } finally {
      _setLoading(false);
    }
  }

  // ─── Load pending requests ──────────────────────────────────────────
  Future<void> loadPendingRequests({String type = 'incoming'}) async {
    try {
      _pendingRequests = await _repository.getFriendRequests(type: type);
      _error = null;
    } catch (e) {
      _error = e.toString();
      _pendingRequests = [];
    }
    notifyListeners();
  }

  // ─── Search users ────────────────────────────────────────────────────
  Future<void> searchUsers(String query, {int limit = 10}) async {
    if (query.length < 2) {
      _searchResults = [];
      _isSearching = false;
      notifyListeners();
      return;
    }
    _isSearching = true;
    notifyListeners();
    try {
      _searchResults = await _repository.searchUsers(query, limit: limit);
      _error = null;
    } catch (e) {
      _error = e.toString();
      _searchResults = [];
    } finally {
      _isSearching = false;
      notifyListeners();
    }
  }

  // ─── Send friend request ─────────────────────────────────────────────
  Future<void> sendFriendRequest({String? username, String? email}) async {
    try {
      await _repository.sendFriendRequest(username: username, email: email);
      // Refresh pending requests
      await loadPendingRequests(type: 'all');
      _error = null;
    } catch (e) {
      _error = e.toString();
      rethrow;
    }
    notifyListeners();
  }

  // ─── Respond to friend request ──────────────────────────────────────
  Future<void> respondFriendRequest(String friendshipId, String action) async {
    try {
      await _repository.respondFriendRequest(friendshipId, action);
      // Refresh lists
      await loadFriends();
      await loadPendingRequests(type: 'all');
      _error = null;
    } catch (e) {
      _error = e.toString();
      rethrow;
    }
    notifyListeners();
  }

  // ─── Unfriend ────────────────────────────────────────────────────────
  Future<void> unfriend(String friendshipId) async {
    try {
      await _repository.unfriend(friendshipId);
      await loadFriends();
      _error = null;
    } catch (e) {
      _error = e.toString();
      rethrow;
    }
    notifyListeners();
  }

  // ─── Helper to get friend user from friendship ──────────────────────
  FriendUser getFriend(Friendship friendship) {
    return friendship.friend ??
        (friendship.direction == 'outgoing'
            ? friendship.recipient
            : friendship.requester)!;
  }

  void _setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }
}

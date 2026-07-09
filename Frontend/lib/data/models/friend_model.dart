// lib/data/models/friend_model.dart
class FriendUser {
  final String id;
  final String name;
  final String username;
  final String email;
  final String? profilePicture;

  FriendUser({
    required this.id,
    required this.name,
    required this.username,
    required this.email,
    this.profilePicture,
  });

  factory FriendUser.fromJson(Map<String, dynamic> json) {
    return FriendUser(
      id: json['_id'] ?? json['id'] ?? '',
      name: json['name'] ?? '',
      username: json['username'] ?? '',
      email: json['email'] ?? '',
      profilePicture: json['profile_picture'],
    );
  }
}

class Friendship {
  final String id;
  final String status; // pending, accepted, rejected
  final DateTime? respondedAt;
  final DateTime createdAt;
  final DateTime updatedAt;
  final FriendUser? requester;
  final FriendUser? recipient;
  final String? direction; // outgoing, incoming
  final FriendUser? friend;
  final DateTime? since;

  Friendship({
    required this.id,
    required this.status,
    this.respondedAt,
    required this.createdAt,
    required this.updatedAt,
    this.requester,
    this.recipient,
    this.direction,
    this.friend,
    this.since,
  });

  factory Friendship.fromJson(Map<String, dynamic> json) {
    return Friendship(
      id: json['_id'] ?? json['id'] ?? '',
      status: json['status'] ?? 'pending',
      respondedAt: json['responded_at'] != null
          ? DateTime.parse(json['responded_at'])
          : null,
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
      requester: json['requester'] != null
          ? FriendUser.fromJson(json['requester'])
          : null,
      recipient: json['recipient'] != null
          ? FriendUser.fromJson(json['recipient'])
          : null,
      direction: json['direction'],
      friend: json['friend'] != null
          ? FriendUser.fromJson(json['friend'])
          : null,
      since: json['since'] != null ? DateTime.parse(json['since']) : null,
    );
  }
}

class Quote {
  final String text;
  final String author;

  Quote({required this.text, required this.author});

  factory Quote.fromJson(Map<String, dynamic> json) {
    return Quote(
      text: json['text'] ?? '',
      author: json['author'] ?? '',
    );
  }
}

class FriendListResponse {
  final List<Friendship> friends;
  final Quote? quote;

  FriendListResponse({required this.friends, this.quote});

  factory FriendListResponse.fromJson(Map<String, dynamic> json) {
    final list = json['data']?['friends'] as List? ?? [];
    final quoteJson = json['data']?['quote'];
    Quote? quote;
    if (quoteJson != null) {
      quote = Quote.fromJson(quoteJson);
    }
    return FriendListResponse(
      friends: list.map((f) => Friendship.fromJson(f)).toList(),
      quote: quote,
    );
  }
}

class FriendRequestResponse {
  final List<Friendship> requests;

  FriendRequestResponse({required this.requests});

  factory FriendRequestResponse.fromJson(Map<String, dynamic> json) {
    final list = json['data']?['requests'] as List? ?? [];
    return FriendRequestResponse(
      requests: list.map((f) => Friendship.fromJson(f)).toList(),
    );
  }
}

class SearchUserResult {
  final String id;
  final String name;
  final String username;
  final String email;
  final String? profilePicture;
  final String relationshipStatus; // none, pending, accepted, rejected

  SearchUserResult({
    required this.id,
    required this.name,
    required this.username,
    required this.email,
    this.profilePicture,
    required this.relationshipStatus,
  });

  factory SearchUserResult.fromJson(Map<String, dynamic> json) {
    return SearchUserResult(
      id: json['_id'] ?? '',
      name: json['name'] ?? '',
      username: json['username'] ?? '',
      email: json['email'] ?? '',
      profilePicture: json['profile_picture'],
      relationshipStatus: json['relationship_status'] ?? 'none',
    );
  }
}

class SearchUserResponse {
  final List<SearchUserResult> users;

  SearchUserResponse({required this.users});

  factory SearchUserResponse.fromJson(Map<String, dynamic> json) {
    final list = json['data']?['users'] as List? ?? [];
    return SearchUserResponse(
      users: list.map((u) => SearchUserResult.fromJson(u)).toList(),
    );
  }
}

class SendFriendRequestResponse {
  final Friendship friendship;

  SendFriendRequestResponse({required this.friendship});

  factory SendFriendRequestResponse.fromJson(Map<String, dynamic> json) {
    return SendFriendRequestResponse(
      friendship: Friendship.fromJson(json['data']?['friendship'] ?? {}),
    );
  }
}

class RespondFriendRequestResponse {
  final Friendship friendship;

  RespondFriendRequestResponse({required this.friendship});

  factory RespondFriendRequestResponse.fromJson(Map<String, dynamic> json) {
    return RespondFriendRequestResponse(
      friendship: Friendship.fromJson(json['data']?['friendship'] ?? {}),
    );
  }
}
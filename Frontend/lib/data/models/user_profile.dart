class UserProfile {
  final String name;
  final String? profilePicture;
  final String username;
  final String email;
  final String timezone;
  final bool isVerified;

  UserProfile({
    required this.name,
    this.profilePicture,
    required this.username,
    required this.email,
    required this.timezone,
    this.isVerified = false,
  });

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      name: json['name'] ?? '',
      profilePicture: json['profile_picture'],
      username: json['username'] ?? '',
      email: json['email'] ?? '',
      timezone: json['timezone'] ?? 'UTC',
      isVerified: json['is_verified'] ?? false,
    );
  }

  String get initial {
    if (name.isEmpty) return '?';
    return name.trim().split(' ').first[0].toUpperCase();
  }

  UserProfile copyWith({
    String? name,
    String? profilePicture,
    String? username,
    String? email,
    String? timezone,
    bool? isVerified,
  }) {
    return UserProfile(
      name: name ?? this.name,
      profilePicture: profilePicture ?? this.profilePicture,
      username: username ?? this.username,
      email: email ?? this.email,
      timezone: timezone ?? this.timezone,
      isVerified: isVerified ?? this.isVerified,
    );
  }
}
class UserProfile {
  final String name;
  final String? profilePicture;

  UserProfile({
    required this.name,
    this.profilePicture,
  });

  factory UserProfile.fromJson(
    Map<String, dynamic> json,
  ) {
    return UserProfile(
      name: json['name'] ?? '',
      profilePicture: json['profile_picture'],
    );
  }

  String get initial {
    if (name.isEmpty) return '?';

    return name
        .trim()
        .split(' ')
        .first[0]
        .toUpperCase();
  }
}
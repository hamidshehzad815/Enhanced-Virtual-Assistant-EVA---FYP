/// User profile data model - ready for API integration
class UserProfile {
  final String name;
  final String userInitial;
  final double dailyProgress; // 0.0 to 1.0

  UserProfile({
    required this.name,
    required this.userInitial,
    required this.dailyProgress,
  });

  /// Convert to JSON for API calls
  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'userInitial': userInitial,
      'dailyProgress': dailyProgress,
    };
  }

  /// Create from JSON API response
  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      name: json['name'] as String,
      userInitial: json['userInitial'] as String,
      dailyProgress: (json['dailyProgress'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

import 'package:flutter/material.dart';
import '../../data/services/storage_service.dart';
import '../../data/models/user_profile.dart';
import '../../data/repositories/profile_repository.dart';
import 'package:cross_file/cross_file.dart';

class ProfileViewModel extends ChangeNotifier {
  final ProfileRepository _repository = ProfileRepository();
  UserProfile? _profile;
  bool _isLoading = false;
  String? _error;

  UserProfile? get profile => _profile;
  bool get isLoading => _isLoading;
  String? get error => _error;

  Future<void> loadProfile() async {
    try {
      _isLoading = true;
      notifyListeners();
      final token = await StorageService.getAccessToken();
      if (token == null) throw Exception('No token');
      final response = await _repository.getProfile(token);
      final userData = response['data']['user'];
      _profile = UserProfile.fromJson(userData);
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _error = e.toString();
      _isLoading = false;
      notifyListeners();
    }
  }

  // Update name, username, timezone
  Future<void> updateProfile({
    String? name,
    String? username,
    String? timezone,
  }) async {
    if (_profile == null) return;
    final oldProfile = _profile!;

    // Optimistic update
    _profile = UserProfile(
      name: name ?? oldProfile.name,
      profilePicture: oldProfile.profilePicture,
      username: username ?? oldProfile.username,
      email: oldProfile.email,
      timezone: timezone ?? oldProfile.timezone,
      isVerified: oldProfile.isVerified,
    );
    notifyListeners();

    try {
      final token = await StorageService.getAccessToken();
      if (token == null) throw Exception('No token');
      final body = <String, dynamic>{};
      if (name != null) body['name'] = name;
      if (username != null) body['username'] = username;
      if (timezone != null) body['timezone'] = timezone;
      final response = await _repository.updateProfile(token, body);
      final updatedUser = response['data']['user'];
      _profile = UserProfile.fromJson(updatedUser);
      notifyListeners();
    } catch (e) {
      _profile = oldProfile;
      _error = e.toString();
      notifyListeners();
      rethrow;
    }
  }

  // Upload avatar
  Future<void> uploadAvatar(XFile imageFile) async {
    if (_profile == null) return;
    final oldPicture = _profile!.profilePicture;
    try {
      final token = await StorageService.getAccessToken();
      if (token == null) throw Exception('No token');
      final response = await _repository.uploadAvatar(token, imageFile);
      final updatedUser = response['data']['user'];
      _profile = UserProfile.fromJson(updatedUser);
      notifyListeners();
    } catch (e) {
      // Rollback picture
      _profile = UserProfile(
        name: _profile!.name,
        profilePicture: oldPicture,
        username: _profile!.username,
        email: _profile!.email,
        timezone: _profile!.timezone,
        isVerified: _profile!.isVerified,
      );
      _error = e.toString();
      notifyListeners();
      rethrow;
    }
  }

  Future<void> deleteAvatar() async {
    if (_profile == null) return;
    final oldPicture = _profile!.profilePicture;
    final oldName = _profile!.name;
    final oldUsername = _profile!.username;
    final oldEmail = _profile!.email;
    final oldTimezone = _profile!.timezone;
    final oldVerified = _profile!.isVerified;

    // Optimistic update – set picture to null immediately
    _profile = UserProfile(
      name: oldName,
      profilePicture: null, // 👈 Clear picture
      username: oldUsername,
      email: oldEmail,
      timezone: oldTimezone,
      isVerified: oldVerified,
    );
    notifyListeners();

    try {
      final token = await StorageService.getAccessToken();
      if (token == null) throw Exception('No token');
      final response = await _repository.deleteAvatar(token);
      final updatedUser = response['data']['user'];
      _profile = UserProfile.fromJson(updatedUser);
      notifyListeners();
    } catch (e) {
      // Rollback on error
      _profile = UserProfile(
        name: oldName,
        profilePicture: oldPicture,
        username: oldUsername,
        email: oldEmail,
        timezone: oldTimezone,
        isVerified: oldVerified,
      );
      _error = e.toString();
      notifyListeners();
      rethrow;
    }
  }
}

import '../services/profile_service.dart';
import 'package:cross_file/cross_file.dart';

class ProfileRepository {
  final ProfileService _service = ProfileService();

  Future<Map<String, dynamic>> getProfile(String token) {
    return _service.getProfile(token);
  }

  Future<Map<String, dynamic>> updateProfile(
    String token,
    Map<String, dynamic> body,
  ) {
    return _service.updateProfile(token, body);
  }

  Future<Map<String, dynamic>> uploadAvatar(String token, XFile imageFile) {
    return _service.uploadAvatar(token, imageFile);
  }

  Future<Map<String, dynamic>> deleteAvatar(String token) {
    return _service.deleteAvatar(token);
  }
}

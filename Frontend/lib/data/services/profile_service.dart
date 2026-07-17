import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:cross_file/cross_file.dart';
import 'package:http_parser/http_parser.dart';
import '../../core/constants/api_constants.dart';
import 'api_client.dart';

class ProfileService {
  Future<Map<String, dynamic>> getProfile(String token) async {
    final response = await ApiClient.get(
      Uri.parse('${AppConstants.baseUrl}/profile'),
    );
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception('Failed to load profile');
  }

  Future<Map<String, dynamic>> updateProfile(
    String token,
    Map<String, dynamic> body,
  ) async {
    final response = await http.patch(
      Uri.parse('${AppConstants.baseUrl}/profile'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode(body),
    );
    if (response.statusCode == 200) return jsonDecode(response.body);
    final error = jsonDecode(response.body);
    throw Exception(error['message'] ?? 'Update failed');
  }

  Future<Map<String, dynamic>> uploadAvatar(
    String token,
    XFile imageFile,
  ) async {
    // Validate file size
    final size = await imageFile.length();
    if (size > 2 * 1024 * 1024) throw Exception('File exceeds 2MB');

    // Read bytes
    final bytes = await imageFile.readAsBytes();
    if (bytes.isEmpty) throw Exception('File is empty');

    // Determine MIME type
    final fileName = imageFile.name.isNotEmpty ? imageFile.name : 'avatar.jpg';
    final extension = fileName.split('.').last.toLowerCase();
    final mimeType = _getMimeType(extension);
    if (mimeType == null) {
      throw Exception(
        'Unsupported file type: $extension. Allowed: jpg, jpeg, png, webp',
      );
    }

    final request = http.MultipartRequest(
      'POST',
      Uri.parse('${AppConstants.baseUrl}/profile/avatar'),
    );
    request.headers['Authorization'] = 'Bearer $token';
    request.files.add(
      http.MultipartFile.fromBytes(
        'avatar', // must be exactly this
        bytes,
        filename: fileName,
        contentType: MediaType.parse(mimeType),
      ),
    );

    final streamedResponse = await request.send();
    final responseBody = await streamedResponse.stream.bytesToString();

    // --- Log full response for debugging ---
    print('Avatar upload response status: ${streamedResponse.statusCode}');
    print('Avatar upload response body: $responseBody');

    if (streamedResponse.statusCode == 200) {
      return jsonDecode(responseBody);
    } else {
      String errorMsg = 'Upload failed (${streamedResponse.statusCode})';
      try {
        final errorJson = jsonDecode(responseBody);
        errorMsg = errorJson['message'] ?? errorMsg;
      } catch (_) {}
      throw Exception(errorMsg);
    }
  }

  String? _getMimeType(String extension) {
    switch (extension) {
      case 'jpg':
      case 'jpeg':
        return 'image/jpeg';
      case 'png':
        return 'image/png';
      case 'webp':
        return 'image/webp';
      default:
        return null;
    }
  }

  Future<Map<String, dynamic>> deleteAvatar(String token) async {
    final response = await http.delete(
      Uri.parse('${AppConstants.baseUrl}/profile/avatar'),
      headers: {
        'Authorization': 'Bearer $token',
      },
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      try {
        final error = jsonDecode(response.body);
        throw Exception(error['message'] ?? 'Failed to delete avatar');
      } catch (_) {
        throw Exception('Failed to delete avatar: ${response.statusCode}');
      }
    }
  }
}

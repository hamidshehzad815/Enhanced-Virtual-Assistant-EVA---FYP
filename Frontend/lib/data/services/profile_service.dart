import 'dart:convert';
import 'package:http/http.dart' as http;
import '../../core/constants/api_constants.dart';

class ProfileService {
  Future<Map<String, dynamic>> getProfile(
    String token,
  ) async {
    final response = await http.get(
      Uri.parse('${AppConstants.baseUrl}/profile'),
      headers: {
        'Authorization': 'Bearer $token',
      },
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }

    throw Exception(
      'Failed to load profile',
    );
  }
}
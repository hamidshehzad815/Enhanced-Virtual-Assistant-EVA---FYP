import 'dart:convert';
import 'package:http/http.dart' as http;
import '../../core/constants/api_constants.dart';
import '../models/user_model.dart';
import 'package:google_sign_in/google_sign_in.dart';

class AuthService {
  /// Login API
  static Future<Map<String, dynamic>> loginUser(
    String email,
    String password,
  ) async {
    final url = Uri.parse("${AppConstants.baseUrl}/auth/login");

    try {
      final response = await http
          .post(
            url,
            headers: {"Content-Type": "application/json"},
            body: jsonEncode({"email": email, "password": password}),
          )
          .timeout(const Duration(seconds: 15));

      final data = response.body.isNotEmpty ? jsonDecode(response.body) : {};

      if (response.statusCode == 200) {
        return {
          "success": true, // ✅ added for UI check
          ...data,
        };
      }
      return {
        "success": false,
        "field": data["field"], // keep if backend sends field-specific error
        "msg": data["message"] ?? data["msg"] ?? "Login failed",
      };
    } catch (e) {
      return {"success": false, "msg": "Server not reachable: $e"};
    }
  }

  /// Signup API
  static Future<Map<String, dynamic>> signupUser(UserModel user) async {
    final url = Uri.parse("${AppConstants.baseUrl}/auth/register");

    try {
      final response = await http
          .post(
            url,
            headers: {"Content-Type": "application/json"},
            body: jsonEncode(user.toJson()),
          )
          .timeout(const Duration(seconds: 15));

      final data = response.body.isNotEmpty ? jsonDecode(response.body) : {};

      // SUCCESS – backend returns status 200 or 201
      if (response.statusCode == 200 || response.statusCode == 201) {
        return {"success": true, ...data};
      }
      // ERROR RESPONSE
      return {
        "success": false,
        "field": data["field"],
        "msg": data["message"] ?? data["msg"] ?? "Signup failed",
      };
    } catch (e) {
      return {"success": false, "msg": "Server not reachable: $e"};
    }
  }

  //logout user

  static Future<Map<String, dynamic>> logoutUser(String token) async {
    final url = Uri.parse("${AppConstants.baseUrl}/auth/logout");

    try {
      final response = await http
          .post(url, headers: {"Authorization": "Bearer $token"})
          .timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        return {"success": true, "msg": "Logged out successfully"};
      }
      return {"success": false, "msg": "Logout failed"};
    } catch (e) {
      return {"success": false, "msg": "Server not reachable: $e"};
    }
  }

  // Google Sign-In API
  static Future<Map<String, dynamic>> signInWithGoogle({
    String? timezone,
  }) async {
    final url = Uri.parse("${AppConstants.baseUrl}/auth/google");

    try {
      await GoogleSignIn.instance.initialize(
        serverClientId:
            '424904983644-1r590marhlk27lgab1pja3ufcirtfkqb.apps.googleusercontent.com', 
      );
      final GoogleSignInAccount? googleUser = await GoogleSignIn.instance
          .authenticate(scopeHint: ['email', 'profile']);

      if (googleUser == null) {
        return {"success": false, "msg": "Sign-in cancelled by user"};
      }

      final GoogleSignInAuthentication googleAuth =
          await googleUser.authentication;
      final String? idToken = googleAuth.idToken;

      if (idToken == null) {
        return {"success": false, "msg": "Failed to obtain ID token"};
      }

      final response = await http
          .post(
            url,
            headers: {"Content-Type": "application/json"},
            body: jsonEncode({
              "id_token": idToken,
              if (timezone != null) "timezone": timezone,
            }),
          )
          .timeout(const Duration(seconds: 15));

      final data = response.body.isNotEmpty ? jsonDecode(response.body) : {};

      if (response.statusCode == 200 || response.statusCode == 201) {
        return {
          "success": true,
          "data": data['data'],
          "isNewUser": data['data']?['is_new_user'] ?? false,
        };
      }
      return {
        "success": false,
        "msg": data['message'] ?? data['msg'] ?? "Google sign-in failed",
      };
    } catch (e) {
      return {"success": false, "msg": "Server not reachable: $e"};
    }
  }
}

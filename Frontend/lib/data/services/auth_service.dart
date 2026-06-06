import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/user_model.dart';

class AuthService {
  /// Login API
  static Future<Map<String, dynamic>> loginUser(
    String email,
    String password,
  ) async {
    final url = Uri.parse("http://192.168.100.7:4500/api/auth/login");

    try {
      final response = await http
          .post(
            url,
            headers: {"Content-Type": "application/json"},
            body: jsonEncode({"email": email, "password": password}),
          )
          .timeout(const Duration(seconds: 15));

      final data = response.body.isNotEmpty ? jsonDecode(response.body) : {};

      // SUCCESS – backend returns { "status": "success", ... }
      if (response.statusCode == 200) {
        return {
          "success": true, // ✅ added for UI check
          ...data,
        };
      }
      // ERROR RESPONSE – backend may send { "status": "fail", "message": ... }
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
    final url = Uri.parse("http://192.168.100.7:4500/api/auth/register");

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
}

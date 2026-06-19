import 'package:flutter/foundation.dart';
import '../../data/models/user_model.dart';
import '../../data/services/auth_service.dart';
import '../../data/services/storage_service.dart';
import '../../data/services/push_notification_service.dart';

class AuthResult {
  final bool success;
  final bool? isVerified;
  final String? field;
  final String message;

  AuthResult({
    required this.success,
    this.isVerified,
    this.field,
    required this.message,
  });

  factory AuthResult.fromMap(Map<String, dynamic> data) {
    return AuthResult(
      success: data['success'] == true,
      isVerified: data['data']?['user']?['is_verified'] == true,
      field: data['field'] as String?,
      message: data['msg'] ?? data['message'] ?? '',
    );
  }
}

class AuthViewModel extends ChangeNotifier {
  bool _isLoading = false;
  String? _emailError;
  String? _passwordError;
  String? _nameError;
  String? _userNameError;
  String? _generalError;
  AuthResult? _lastResult;

  bool get isLoading => _isLoading;
  String? get emailError => _emailError;
  String? get passwordError => _passwordError;
  String? get nameError => _nameError;
  String? get userNameError => _userNameError;
  String? get generalError => _generalError;
  AuthResult? get lastResult => _lastResult;

  Future<AuthResult> login(String email, String password) async {
    _clearErrors();
    _setLoading(true);

    try {
      final response = await AuthService.loginUser(email, password);

      if (response['success'] == true) {
        final accessToken = response['data']?['tokens']?['access_token'];
        final refreshToken = response['data']?['tokens']?['refresh_token'];

        if (accessToken == null) {
          throw Exception('Access token missing in login response');
        }

        await StorageService.saveAccessToken(accessToken);
        await StorageService.saveRefreshToken(refreshToken);

        // Push setup – best effort; don't fail login if it fails
        try {
          await PushNotificationService.init();
        } catch (pushError) {
          // Log but don't rethrow – login is still successful
          print('Push notification setup failed: $pushError');
          // Optionally, you could set a flag to show a user-friendly message later.
        }
      }

      final result = AuthResult.fromMap(response);
      _lastResult = result;

      if (!result.success) {
        _applyFieldError(result);
      }

      return result;
    } catch (e) {
      _generalError = e.toString();
      notifyListeners();
      return AuthResult(success: false, message: "Something went wrong");
    } finally {
      _setLoading(false);
    }
  }

  Future<AuthResult> signup(UserModel user) async {
    _clearErrors();
    _setLoading(true);

    final response = await AuthService.signupUser(user);
    final result = AuthResult.fromMap(response);
    _lastResult = result;

    if (!result.success) {
      _applyFieldError(result);
    }

    _setLoading(false);
    return result;
  }

  void clearErrors() {
    _clearErrors();
    notifyListeners();
  }

  void _applyFieldError(AuthResult result) {
    if (result.field == 'email') {
      _emailError = result.message;
    } else if (result.field == 'password') {
      _passwordError = result.message;
    } else if (result.field == 'name') {
      _nameError = result.message;
    } else if (result.field == 'userName' || result.field == 'username') {
      _userNameError = result.message;
    } else {
      _generalError = result.message;
    }
  }

  void _setLoading(bool value) {
    _isLoading = value;
    notifyListeners();
  }

  void _clearErrors() {
    _emailError = null;
    _passwordError = null;
    _nameError = null;
    _userNameError = null;
    _generalError = null;
  }
}

import 'dart:convert';

/// Client-side auth validation. Mirrors
/// Eva_Backend_Server/utils/authValidation.js (the backend is authoritative) so
/// users get instant feedback and anything accepted here is accepted by the
/// server. Keep the two in sync.
///
/// Password rule (same as most real sites, and compatible with the passwords
/// Google Password Manager / Chrome / Safari / 1Password generate):
///   8–64 characters, at least one letter, at least one number or symbol,
///   not a commonly used password, not a trivial pattern.
///
/// Every validator returns `null` when the value is valid, otherwise the
/// message to show under the field (the signature Flutter form fields expect).
class AuthValidators {
  AuthValidators._();

  static const int passwordMin = 8;
  static const int passwordMax = 64;
  static const int _passwordMaxBytes = 72; // bcrypt ignores everything after this

  static final RegExp _nameAllowed = RegExp(
    r"^[\p{L}\p{M}][\p{L}\p{M} .'’-]*$",
    unicode: true,
  );
  static final RegExp _letter = RegExp(r'\p{L}', unicode: true);
  static final RegExp _numberOrSymbol = RegExp(
    r'[\p{N}\p{S}\p{P}]',
    unicode: true,
  );
  static final RegExp _usernameAllowed = RegExp(r'^[a-z][a-z0-9._]*$');
  static final RegExp _email = RegExp(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*\.[A-Za-z]{2,}$",
  );

  static const Set<String> _reservedUsernames = {
    'admin', 'administrator', 'root', 'support', 'help', 'system',
    'moderator', 'staff', 'official', 'security', 'api', 'null',
    'undefined', 'eva', 'evaapp', 'evasupport', 'evaadmin',
  };

  static const Set<String> _commonPasswords = {
    'password', 'password1', 'password12', 'password123', 'password1234',
    'passw0rd', 'p@ssw0rd', 'p@ssword', r'pa$$w0rd', '123456789',
    '1234567890', '12345678', '123123123', '11111111', '00000000',
    '1q2w3e4r', '1q2w3e4r5t', '1qaz2wsx', 'qwerty123', 'qwertyui',
    'qwertyuiop', 'qwerty12345', 'asdfghjk', 'asdfghjkl', 'zxcvbnm1',
    'iloveyou', 'iloveyou1', 'letmein1', 'welcome1', 'welcome123',
    'admin123', 'admin1234', 'administrator', 'abc12345', 'abcd1234',
    'abcd12345', 'monkey123', 'dragon123', 'football1', 'baseball1',
    'superman1', 'trustno1', 'sunshine1', 'princess1', 'changeme',
    'changeme1', 'master123', 'login123', 'pakistan1', 'pakistan123',
    'eva12345', 'eva123456', 'evaapp123', 'student123', 'university1',
  };

  // ── Field validators ────────────────────────────────────────────────────

  static String? name(String? value) {
    final name = (value ?? '').trim().replaceAll(RegExp(r'\s+'), ' ');
    if (name.isEmpty) return 'Full name is required';
    if (name.length < 2) return 'Name must be at least 2 characters';
    if (name.length > 100) return 'Name cannot exceed 100 characters';
    if (!_nameAllowed.hasMatch(name) ||
        _letter.allMatches(name).length < 2) {
      return 'Name can only contain letters, spaces, apostrophes, hyphens and periods';
    }
    return null;
  }

  static String? username(String? value) {
    final username = (value ?? '').trim().toLowerCase();
    if (username.isEmpty) return 'Username is required';
    if (username.length < 3) return 'Username must be at least 3 characters';
    if (username.length > 30) return 'Username cannot exceed 30 characters';
    if (!RegExp(r'^[a-z]').hasMatch(username)) {
      return 'Username must start with a letter';
    }
    if (!_usernameAllowed.hasMatch(username)) {
      return 'Username can only contain letters, numbers, periods and underscores';
    }
    if (RegExp(r'[._]{2}').hasMatch(username)) {
      return 'Username cannot have two periods or underscores in a row';
    }
    if (RegExp(r'[._]$').hasMatch(username)) {
      return 'Username cannot end with a period or underscore';
    }
    if (_reservedUsernames.contains(username)) {
      return 'This username is not available. Please choose another one';
    }
    return null;
  }

  static String? email(String? value) {
    final email = (value ?? '').trim();
    if (email.isEmpty) return 'Email is required';
    if (email.length > 254) return 'Email address is too long';
    final local = email.split('@').first;
    if (!_email.hasMatch(email) ||
        local.length > 64 ||
        local.startsWith('.') ||
        local.endsWith('.') ||
        email.contains('..')) {
      return 'Please enter a valid email address';
    }
    return null;
  }

  /// Login only checks that a password was typed — never its strength, so
  /// people with older/simpler passwords can still sign in.
  static String? loginPassword(String? value) {
    if (value == null || value.isEmpty) return 'Password is required';
    return null;
  }

  /// Validate a NEW password (sign-up / reset).
  /// [email] and [username] are the user's own details the password must not
  /// contain.
  static String? password(String? value, {String? email, String? username}) {
    final password = value ?? '';
    if (password.isEmpty) return 'Password is required';
    if (password.length < passwordMin) {
      return 'Password must be at least $passwordMin characters';
    }
    if (password.length > passwordMax ||
        utf8.encode(password).length > _passwordMaxBytes) {
      return 'Password cannot be longer than $passwordMax characters';
    }
    if (password.trim().isEmpty) return 'Password cannot be only spaces';
    if (!_letter.hasMatch(password)) {
      return 'Password must include at least one letter';
    }
    if (!_numberOrSymbol.hasMatch(password)) {
      return 'Password must include at least one number or symbol';
    }

    final lower = password.toLowerCase();
    if (_commonPasswords.contains(lower) || _isTrivialPattern(password)) {
      return 'This password is too common. Please choose a stronger one';
    }

    final emailName = (email ?? '').trim().split('@').first.toLowerCase();
    if (emailName.length >= 4 && lower.contains(emailName)) {
      return 'Password cannot contain your email address';
    }
    final user = (username ?? '').trim().toLowerCase();
    if (user.length >= 4 && lower.contains(user)) {
      return 'Password cannot contain your username';
    }
    return null;
  }

  static String? confirmPassword(String? password, String? confirm) {
    if (confirm == null || confirm.isEmpty) {
      return 'Please confirm your new password';
    }
    if (password != confirm) return 'Passwords do not match';
    return null;
  }

  // ── Password feedback (strength meter + checklist) ──────────────────────

  static bool hasValidLength(String password) =>
      password.length >= passwordMin && password.length <= passwordMax;

  static bool hasLetter(String password) => _letter.hasMatch(password);

  static bool hasNumberOrSymbol(String password) =>
      _numberOrSymbol.hasMatch(password);

  /// 0 = empty, 1 = weak (fails a rule), 2 = good, 3 = strong.
  static int passwordStrength(
    String password, {
    String? email,
    String? username,
  }) {
    if (password.isEmpty) return 0;
    if (AuthValidators.password(password, email: email, username: username) !=
        null) {
      return 1;
    }
    var score = 0;
    if (password.length >= 12) score++;
    if (password.length >= 16) score++;
    if (RegExp(r'\p{Ll}', unicode: true).hasMatch(password) &&
        RegExp(r'\p{Lu}', unicode: true).hasMatch(password)) {
      score++;
    }
    if (RegExp(r'\p{N}', unicode: true).hasMatch(password) &&
        RegExp(r'[\p{S}\p{P}]', unicode: true).hasMatch(password)) {
      score++;
    }
    return score >= 3 ? 3 : 2;
  }

  // ── Helpers ─────────────────────────────────────────────────────────────

  /// Same character, or only two distinct characters (aaaaaaaa, abababab), or
  /// a straight run (12345678, abcdefgh).
  static bool _isTrivialPattern(String password) {
    if (password.runes.toSet().length <= 2) return true;
    final lower = password.toLowerCase();
    if (lower.length < 6) return false;
    var ascending = true;
    var descending = true;
    for (var i = 1; i < lower.length; i++) {
      final diff = lower.codeUnitAt(i) - lower.codeUnitAt(i - 1);
      if (diff != 1) ascending = false;
      if (diff != -1) descending = false;
    }
    return ascending || descending;
  }
}

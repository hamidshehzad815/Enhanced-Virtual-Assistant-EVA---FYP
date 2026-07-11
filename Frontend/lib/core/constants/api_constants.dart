class AppConstants {
  /// Backend API base URL (includes the trailing `/api`).
  ///
  /// Set at compile time via `--dart-define=API_BASE_URL=...`, most easily
  /// through the config files:
  ///   flutter run   --dart-define-from-file=config/dev.json
  ///   flutter build --dart-define-from-file=config/prod.json
  ///
  /// If no define is passed, it falls back to the local LAN backend below.
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://192.168.100.7:4500/api',
  );
}

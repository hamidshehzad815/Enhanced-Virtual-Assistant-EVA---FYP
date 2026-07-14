import 'package:google_sign_in/google_sign_in.dart';
import '../../core/constants/google_calendar_constants.dart';

class GoogleCalendarAuthTokens {
  final String accessToken;
  final String? serverAuthCode;

  const GoogleCalendarAuthTokens({
    required this.accessToken,
    this.serverAuthCode,
  });
}

class GoogleCalendarAuthService {
  static const String _webClientId = String.fromEnvironment(
    'GOOGLE_WEB_CLIENT_ID',
  );

  static Future<GoogleCalendarAuthTokens> authorizeForCalendar() async {
    if (_webClientId.isEmpty) {
      throw Exception(
        'Google Calendar is not configured. Set GOOGLE_WEB_CLIENT_ID in config/dev.json or config/prod.json.',
      );
    }

    await GoogleSignIn.instance.initialize(serverClientId: _webClientId);

    final GoogleSignInAccount? account = await GoogleSignIn.instance.authenticate(
      scopeHint: [
        'email',
        GoogleCalendarConstants.calendarEventsScope,
      ],
    );

    if (account == null) {
      throw Exception('Google authorization cancelled');
    }

    final GoogleSignInClientAuthorization clientAuth =
        await account.authorizationClient.authorizeScopes([
      GoogleCalendarConstants.calendarEventsScope,
    ]);

    final GoogleSignInServerAuthorization? serverAuth =
        await account.authorizationClient.authorizeServer([
      GoogleCalendarConstants.calendarEventsScope,
    ]);

    return GoogleCalendarAuthTokens(
      accessToken: clientAuth.accessToken,
      serverAuthCode: serverAuth?.serverAuthCode,
    );
  }
}

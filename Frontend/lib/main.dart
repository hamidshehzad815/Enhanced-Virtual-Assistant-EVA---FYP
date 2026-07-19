import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'core/theme/app_colours.dart';
import 'router/app_router.dart';
import 'presentation/providers/chat_viewmodel.dart';
import 'presentation/providers/home_screen_viewmodel.dart';
import 'package:provider/provider.dart';
import 'presentation/providers/auth_viewmodel.dart';
import 'presentation/providers/calendar_viewmodel.dart';
import 'presentation/providers/roadmap_viewmodel.dart';
import 'presentation/providers/settings_viewmodel.dart';
import 'presentation/providers/theme_provider.dart';
import 'presentation/providers/profile_viewmodel.dart';
import 'presentation/providers/analytics_viewmodel.dart';
import 'presentation/providers/friends_viewmodel.dart';
import 'package:firebase_core/firebase_core.dart';
import '../../data/services/push_notification_service.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import '../../data/services/calendar_service.dart';
import '../../data/services/chat_service.dart';
import '../../data/repositories/calendar_screen_repository.dart';
import 'firebase_options.dart';
import '../../data/services/analytics_service.dart';
import '../../data/services/roadmap_service.dart';
import '../../data/repositories/roadmap_repository.dart';
import '../../data/repositories/chat_repository.dart';
import '../../data/repositories/analytics_repository.dart';
import 'data/services/friend_service.dart';
import '../../data/repositories/friends_repository.dart';
import 'data/services/notification_service.dart';
import '../../data/repositories/notification_repository.dart';
import 'presentation/providers/notification_viewmodel.dart';
import 'presentation/providers/task_refresh_notifier.dart';
import '../../core/constants/app_keys.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);

  // print('🔥 Checking Firebase apps count: ${Firebase.apps.length}');
  try {
    await Firebase.initializeApp(
      options: DefaultFirebaseOptions.currentPlatform,
    );
  } catch (e) {
    if (e.toString().contains('duplicate-app')) {
      // print('🔥 Firebase already initialized (duplicate-app ignored).');
    } else {
      // print('🔥 Firebase init error: $e');
      rethrow;
    }
  }

  FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);
  await PushNotificationService.setup();
  final themeProvider = ThemeProvider();
  await themeProvider.loadTheme();
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => HomeScreenViewModel()),
        ChangeNotifierProvider(create: (_) => ProfileViewModel()),
        Provider<ChatService>(create: (_) => ChatService()),
        Provider<ChatRepository>(
          create: (context) => ChatRepository(context.read<ChatService>()),
        ),
        ChangeNotifierProvider(
          create: (context) => ChatViewModel(context.read<ChatRepository>()),
        ),
        ChangeNotifierProvider(create: (_) => TaskRefreshNotifier()),
        ChangeNotifierProvider(
          create: (_) {
            final service = CalendarService();
            final repository = CalendarRepository(service);
            return CalendarViewModel(repository);
          },
        ),
        ChangeNotifierProvider(create: (_) => AuthViewModel()),
        ChangeNotifierProvider(create: (_) => SettingsViewModel()),
        ChangeNotifierProvider.value(value: themeProvider),
        Provider<RoadmapService>(create: (_) => RoadmapService()),
        Provider<RoadmapRepository>(
          create: (context) =>
              RoadmapRepository(service: context.read<RoadmapService>()),
        ),
        ChangeNotifierProvider(
          create: (context) =>
              RoadmapViewmodel(context.read<RoadmapRepository>()),
        ),
        Provider<AnalyticsService>(create: (_) => AnalyticsService()),
        Provider<AnalyticsRepository>(
          create: (context) =>
              AnalyticsRepository(context.read<AnalyticsService>()),
        ),
        ChangeNotifierProvider(
          create: (context) =>
              AnalyticsViewModel(context.read<AnalyticsRepository>()),
        ),
        Provider<FriendsService>(create: (_) => FriendsService()),
        Provider<FriendsRepository>(
          create: (context) =>
              FriendsRepository(context.read<FriendsService>()),
        ),
        ChangeNotifierProvider(
          create: (context) =>
              FriendsViewModel(context.read<FriendsRepository>()),
        ),
        Provider<NotificationService>(create: (_) => NotificationService()),
        Provider<NotificationRepository>(
          create: (context) =>
              NotificationRepository(context.read<NotificationService>()),
        ),
        ChangeNotifierProvider(
          create: (context) =>
              NotificationViewModel(context.read<NotificationRepository>()),
        ),
      ],

      child: const MyApp(),
    ),
  );
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      debugShowCheckedModeBanner: false,
      title: 'EVA',
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: context.watch<ThemeProvider>().themeMode,
      scaffoldMessengerKey: AppKeys.scaffoldMessengerKey,
      routerConfig: appRouter,
      builder: (context, child) {
        return GradientBackground(child: child ?? const SizedBox());
      },
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  GRADIENT BACKGROUND — dark mode only
// ─────────────────────────────────────────────────────────────────────────────
class GradientBackground extends StatelessWidget {
  final Widget child;
  const GradientBackground({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    if (!isDark) return child;
    return Container(
      decoration: const BoxDecoration(
        gradient: AppColors.darkBackgroundGradient,
      ),
      child: child,
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  THEME
// ─────────────────────────────────────────────────────────────────────────────
class AppTheme {
  static ThemeData lightTheme = ThemeData(
    brightness: Brightness.light,
    scaffoldBackgroundColor: AppColors.scaffoldColorLight,
    cardColor: AppColors.cardLight,
    shadowColor: const Color(0xFF453F3F),
    dividerColor: AppColors.borderLight,
    dividerTheme: const DividerThemeData(color: AppColors.borderLight),
    colorScheme: const ColorScheme.light(
      primary: AppColors.primary,
      secondary: AppColors.primary,
      surface: AppColors.cardLight,
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        padding: const EdgeInsets.symmetric(vertical: 16),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.primary,
        side: const BorderSide(color: AppColors.primary),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
        padding: const EdgeInsets.symmetric(vertical: 16),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(foregroundColor: AppColors.primary),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.cardLight,
      hintStyle: GoogleFonts.inter(
        fontSize: 14,
        color: AppColors.secondaryTextLight,
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppColors.borderLight),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppColors.primary, width: 1.5),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    ),
    textTheme: TextTheme(
      bodyLarge: GoogleFonts.inter(
        fontSize: 16,
        color: AppColors.primaryTextLight,
      ),
      bodyMedium: GoogleFonts.inter(
        fontSize: 14,
        color: AppColors.primaryTextLight,
      ),
      bodySmall: GoogleFonts.inter(
        fontSize: 12,
        color: AppColors.secondaryTextLight,
      ),
      displayLarge: GoogleFonts.instrumentSerif(
        color: AppColors.primaryTextLight,
      ),
      displayMedium: GoogleFonts.instrumentSerif(
        color: AppColors.primaryTextLight,
      ),
      displaySmall: GoogleFonts.instrumentSerif(
        color: AppColors.primaryTextLight,
      ),
      titleLarge: GoogleFonts.libreBaskerville(
        fontSize: 24,
        fontWeight: FontWeight.bold,
        color: AppColors.primaryTextLight,
      ),
      titleMedium: GoogleFonts.inter(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        color: AppColors.primaryTextLight,
      ),
      titleSmall: GoogleFonts.inter(
        fontSize: 13,
        fontWeight: FontWeight.w600,
        color: AppColors.primaryTextLight,
      ),
      labelLarge: GoogleFonts.inter(
        fontSize: 10,
        letterSpacing: 1.2,
        color: AppColors.secondaryTextLight,
      ),
    ),
    primaryTextTheme: const TextTheme(
      bodyMedium: TextStyle(color: AppColors.primaryTextLight),
      bodySmall: TextStyle(color: AppColors.secondaryTextLight),
    ),
    checkboxTheme: CheckboxThemeData(
      fillColor: WidgetStateProperty.resolveWith(
        (s) => s.contains(WidgetState.selected)
            ? AppColors.primary
            : Colors.transparent,
      ),
      checkColor: WidgetStateProperty.all(Colors.white),
      side: const BorderSide(color: AppColors.borderLight),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
    ),
  );

  static ThemeData darkTheme = ThemeData(
    brightness: Brightness.dark,
    scaffoldBackgroundColor: Colors.transparent,
    cardColor: AppColors.cardDark,
    shadowColor: Colors.black,
    dividerColor: AppColors.borderDark,
    dividerTheme: const DividerThemeData(color: AppColors.borderDark),
    colorScheme: const ColorScheme.dark(
      primary: AppColors.primary,
      secondary: AppColors.primary,
      surface: AppColors.cardDark,
      onSurface: AppColors.primaryTextDark,
      primaryContainer: AppColors.primary,
      onPrimaryContainer: Colors.white,
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        padding: const EdgeInsets.symmetric(vertical: 16),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.primary,
        side: const BorderSide(color: AppColors.primary),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
        padding: const EdgeInsets.symmetric(vertical: 16),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(foregroundColor: AppColors.primary),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.inputFillDark,
      hintStyle: GoogleFonts.inter(fontSize: 14, color: AppColors.hintDark),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppColors.borderDark),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppColors.primary, width: 1.5),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    ),
    textTheme: TextTheme(
      bodyLarge: GoogleFonts.inter(
        fontSize: 16,
        color: AppColors.primaryTextDark,
      ),
      bodyMedium: GoogleFonts.inter(
        fontSize: 14,
        color: AppColors.primaryTextDark,
      ),
      bodySmall: GoogleFonts.inter(
        fontSize: 12,
        color: AppColors.secondaryTextDark,
      ),
      displayLarge: GoogleFonts.instrumentSerif(
        color: AppColors.primaryTextDark,
      ),
      displayMedium: GoogleFonts.instrumentSerif(
        color: AppColors.primaryTextDark,
      ),
      displaySmall: GoogleFonts.instrumentSerif(
        color: AppColors.primaryTextDark,
      ),
      titleLarge: GoogleFonts.libreBaskerville(
        fontSize: 24,
        fontWeight: FontWeight.bold,
        color: AppColors.primaryTextDark,
      ),
      titleMedium: GoogleFonts.inter(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        color: AppColors.primaryTextDark,
      ),
      titleSmall: GoogleFonts.inter(
        fontSize: 13,
        fontWeight: FontWeight.w600,
        color: AppColors.primaryTextDark,
      ),
      labelLarge: GoogleFonts.inter(
        fontSize: 10,
        letterSpacing: 1.2,
        color: AppColors.secondaryTextDark,
      ),
    ),
    primaryTextTheme: const TextTheme(
      bodyMedium: TextStyle(color: AppColors.primaryTextDark),
      bodySmall: TextStyle(color: AppColors.secondaryTextDark),
    ),
    checkboxTheme: CheckboxThemeData(
      fillColor: WidgetStateProperty.resolveWith(
        (s) => s.contains(WidgetState.selected)
            ? AppColors.primary
            : Colors.transparent,
      ),
      checkColor: WidgetStateProperty.all(Colors.white),
      side: const BorderSide(color: AppColors.borderDark),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
    ),
  );
}

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../presentation/screens/welcome_screen.dart';
import '../presentation/screens/features_screen.dart';
import '../presentation/screens/get_started_screen.dart';
import '../presentation/screens/auth_screen.dart';
import '../presentation/screens/home_screen.dart';
import '../presentation/screens/chat_screen.dart';
import '../presentation/screens/calendar_screen.dart';
import '../presentation/screens/roadmap_session_screen.dart';
import '../presentation/screens/settings_screen.dart';
import '../presentation/widgets/app_shell.dart';
import '../presentation/screens/analytics_screen.dart';
import '../presentation/screens/collaboration_screen.dart';
import '../presentation/screens/splash_screen.dart';
import '../presentation/screens/edit_profile_screen.dart';
import '../presentation/providers/profile_viewmodel.dart';
import '../presentation/screens/roadmap_screen.dart';

// ── Route path constants ──────────────────────────────────────────────────────
class AppRoutes {
  // Pre-auth (no shell, no nav bar)
  static const welcome = '/welcome';
  static const features = '/features';
  static const getStarted = '/get-started';
  static const auth = '/auth';

  // Main app (inside shell — show nav bar)
  static const splash = '/splash';
  static const home = '/';
  static const calendar = '/calendar';
  static const roadmap = '/roadmap';
  static const settings = '/settings';
  static const analytics = '/analytics';
  static const collaboration = '/collaboration';
  static const editProfile = '/edit-profile';
  static const roadmapSession = '/roadmap-detail';

  // Chat is PUSHED on top of the shell (no nav bar on chat)
  static const chat = '/chat';
}

final appRouter = GoRouter(
  // Start at splash for first launch
  // Change to AppRoutes.home after you wire up auth persistence
  initialLocation: AppRoutes.splash,

  routes: [
    // ── Pre-auth screens (standalone, no shell) ───────────────────────────────
    GoRoute(
      path: AppRoutes.splash,
      pageBuilder: (context, state) => MaterialPage(child: SplashScreen()),
    ),
    GoRoute(
      path: AppRoutes.welcome,
      pageBuilder: (context, state) => MaterialPage(child: WelcomeScreen()),
    ),
    GoRoute(
      path: AppRoutes.features,
      pageBuilder: (context, state) => MaterialPage(child: FeaturesScreen()),
    ),
    GoRoute(
      path: AppRoutes.getStarted,
      pageBuilder: (context, state) => MaterialPage(child: GetStartedScreen()),
    ),
    GoRoute(
      path: AppRoutes.auth,
      builder: (context, state) {
        final extra = state.extra as Map<String, dynamic>?;
        final index = extra?['initialIndex'] as int? ?? 0;
        return AuthScreen(initialIndex: index);
      },
    ),

    // ── Chat: pushed full-screen on top of shell, no nav bar ─────────────────
    GoRoute(
      path: AppRoutes.chat,
      pageBuilder: (context, state) => MaterialPage(child: ChatScreen()),
    ),
    GoRoute(
      path: AppRoutes.editProfile,
      pageBuilder: (context, state) => MaterialPage(
        child: EditProfileScreen(viewModel: context.read<ProfileViewModel>()),
      ),
    ),
GoRoute(
  name: 'roadmap-detail', 
  path: '/roadmap-detail/:goalId',
  pageBuilder: (context, state) {
    final goalId = state.pathParameters['goalId']!;
    return MaterialPage(child: RoadmapSessionScreen(goalId: goalId));
  },
),


    // ── Main shell (shows bottom nav bar) ─────────────────────────────────────
    ShellRoute(
      builder: (context, state, child) =>
          AppShell(location: state.uri.toString(), child: child),
      routes: [
        GoRoute(
          path: AppRoutes.home,
          pageBuilder: (context, state) => MaterialPage(child: HomeScreen()),
        ),
        GoRoute(
          path: AppRoutes.calendar,
          builder: (context, state) {
            final extra = state.extra as Map<String, dynamic>?;
            return CalendarScreen(
              initialTaskId: extra?['taskId'] as String?,
              initialDate: extra?['date'] as DateTime?,
            );
          },
        ),
        GoRoute(
          path: AppRoutes.roadmap, // define constant '/plans'
          pageBuilder: (context, state) =>
              MaterialPage(child: const RoadmapScreen()),
        ),
        GoRoute(
          path: AppRoutes.settings,
          pageBuilder: (context, state) =>
              MaterialPage(child: SettingsScreen()),
        ),
        GoRoute(
          path: AppRoutes.analytics,
          pageBuilder: (context, state) =>
              MaterialPage(child: AnalyticsScreen()),
        ),
        GoRoute(
          path: AppRoutes.collaboration,
          pageBuilder: (context, state) =>
              MaterialPage(child: CollaborationScreen()),
        ),
      ],
    ),
  ],
);

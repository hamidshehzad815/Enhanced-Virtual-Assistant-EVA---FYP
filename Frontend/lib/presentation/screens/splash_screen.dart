import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colours.dart';
import '../../data/services/storage_service.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../data/services/push_notification_service.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _checkRoute();
  }

  Future<void> _checkRoute() async {
    await Future.delayed(const Duration(seconds: 2));

    final prefs = await SharedPreferences.getInstance();
    final onboardingDone = prefs.getBool('onboarding_completed') ?? false;

    final token = await StorageService.getAccessToken();

    if (!mounted) return;

    if (!onboardingDone) {
      context.go('/welcome');
    } else if (token == null) {
      context.go('/auth', extra: {'initialIndex': 0});
    } else {
      context.go('/');
    }
    await PushNotificationService.requestPermission();
    await PushNotificationService.registerToken();
    PushNotificationService.listenTokenRefresh();
    PushNotificationService.handleForegroundMessages();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: Center(
        child: Text(
          'EVA',
          style: TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.bold,
            color: AppColors.primary,
          ),
        ),
      ),
    );
  }
}

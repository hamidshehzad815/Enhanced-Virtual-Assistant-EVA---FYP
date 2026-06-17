import 'package:flutter/material.dart';
import 'package:flutter_social_button/flutter_social_button.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_text_style.dart';
import '../../core/theme/app_colours.dart';
import '../providers/auth_viewmodel.dart';
import 'login_screen.dart';
import 'signup_screen.dart';

class AuthScreen extends StatefulWidget {
  final int initialIndex; // 0 = Log In, 1 = Sign Up

  const AuthScreen({super.key, this.initialIndex = 0});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(
      length: 2,
      vsync: this,
      initialIndex: widget.initialIndex,
    );
    _tabController.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Widget _buildSocialButtons(bool isDark) {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: Divider(
                color: isDark ? AppColors.borderDark : AppColors.borderLight,
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Text(
                'Or continue with',
                style: AppTextStyles.info.copyWith(
                  color: Theme.of(context).textTheme.bodySmall!.color,
                ),
              ),
            ),
            Expanded(
              child: Divider(
                color: isDark ? AppColors.borderDark : AppColors.borderLight,
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        Center(
          child: FlutterSocialButton(
            buttonType: ButtonType.google,
            onTap: () {},
            mini: true,
            title: '',
            iconSize: 26,
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final isLogin = _tabController.index == 0;

    // Card background
    final cardBg = isDark ? AppColors.cardDark : AppColors.cardLight;
    // Inner tab strip background
    final tabStripBg = isDark
        ? AppColors.cardElevatedDark
        : AppColors.scaffoldColorLight;

    return ChangeNotifierProvider<AuthViewModel>(
      create: (_) => AuthViewModel(),
      child: Scaffold(
        backgroundColor: Theme.of(context).scaffoldBackgroundColor,
        body: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 48),
            child: Container(
              constraints: const BoxConstraints(maxWidth: 420),
              decoration: BoxDecoration(
                color: cardBg,
                borderRadius: BorderRadius.circular(28),
                border: isDark ? Border.all(color: AppColors.borderDark) : null,
                boxShadow: [
                  BoxShadow(
                    color: isDark
                        ? Colors.black.withOpacity(0.5)
                        : Colors.black.withOpacity(0.08),
                    blurRadius: 40,
                    offset: const Offset(0, 16),
                  ),
                ],
              ),
              padding: const EdgeInsets.fromLTRB(28, 36, 28, 32),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // ── LOGO ──────────────────────────────────────────────────
                  Center(
                    child: Text(
                      ' Eva',
                      style: AppTextStyles.logo.copyWith(
                        color: Theme.of(context).textTheme.bodyMedium!.color,
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // ── TITLE ─────────────────────────────────────────────────
                  Text(
                    isLogin ? 'Welcome back' : 'Create Account',
                    textAlign: TextAlign.center,
                    style: AppTextStyles.titleMedium.copyWith(
                      color: Theme.of(context).textTheme.bodyMedium!.color,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    isLogin
                        ? 'Log in to continue your progress.'
                        : 'Join Eva to supercharge your studies.',
                    textAlign: TextAlign.center,
                    style: AppTextStyles.subtitleSmall.copyWith(
                      color: Theme.of(context).textTheme.bodySmall!.color,
                    ),
                  ),
                  const SizedBox(height: 24),

                  // ── TAB TOGGLE ────────────────────────────────────────────
                  Container(
                    decoration: BoxDecoration(
                      color: tabStripBg,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                        color: isDark
                            ? AppColors.borderDark
                            : AppColors.borderLight,
                      ),
                    ),
                    padding: const EdgeInsets.all(4),
                    child: TabBar(
                      controller: _tabController,
                      indicator: BoxDecoration(
                        color: cardBg,
                        borderRadius: BorderRadius.circular(10),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.07),
                            blurRadius: 6,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      indicatorSize: TabBarIndicatorSize.tab,
                      dividerColor: Colors.transparent,
                      labelColor: Theme.of(context).textTheme.bodyMedium!.color,
                      unselectedLabelColor: Theme.of(
                        context,
                      ).textTheme.bodySmall!.color,
                      labelStyle: AppTextStyles.button.copyWith(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                      ),
                      unselectedLabelStyle: AppTextStyles.body.copyWith(
                        fontSize: 14,
                        fontWeight: FontWeight.w400,
                      ),
                      tabs: const [
                        Tab(text: 'Log In'),
                        Tab(text: 'Sign Up'),
                      ],
                    ),
                  ),
                  const SizedBox(height: 28),

                  // ── TAB CONTENT ───────────────────────────────────────────
                  AnimatedSwitcher(
                    duration: const Duration(milliseconds: 220),
                    transitionBuilder: (child, animation) =>
                        FadeTransition(opacity: animation, child: child),
                    child: isLogin
                        ? const LoginScreen(key: ValueKey('login'))
                        : const SignupScreen(key: ValueKey('signup')),
                  ),

                  const SizedBox(height: 20),

                  // ── SOCIAL BUTTONS ────────────────────────────────────────
                  _buildSocialButtons(isDark),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class GoogleLogo extends StatelessWidget {
  final double size;

  const GoogleLogo({super.key, this.size = 24});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(painter: _GoogleLogoPainter()),
    );
  }
}

class _GoogleLogoPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final strokeWidth = size.width * 0.18;
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width * 0.35;
    final rect = Rect.fromCircle(center: center, radius: radius);

    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    paint.color = const Color(0xFF4285F4);
    canvas.drawArc(rect, -1.15, 1.25, false, paint);

    paint.color = const Color(0xFF34A853);
    canvas.drawArc(rect, 0.30, 1.0, false, paint);

    paint.color = const Color(0xFFFBBC05);
    canvas.drawArc(rect, 1.40, 0.45, false, paint);

    paint.color = const Color(0xFFEA4335);
    final redRect = Rect.fromLTWH(
      center.dx + radius * 0.35,
      center.dy - strokeWidth * 0.2,
      radius * 0.5,
      strokeWidth,
    );
    canvas.drawRRect(
      RRect.fromRectAndRadius(redRect, Radius.circular(strokeWidth / 2)),
      paint..style = PaintingStyle.fill,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

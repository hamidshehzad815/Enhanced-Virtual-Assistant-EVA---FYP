import 'package:flutter/material.dart';
import '../../core/theme/app_text_style.dart';
import '../../core/theme/app_colours.dart';
import '../widgets/demo_chat_bubble.dart';
import '../widgets/fade_slide_in.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';

class GetStartedScreen extends StatefulWidget {
  const GetStartedScreen({super.key});

  @override
  State<GetStartedScreen> createState() => _GetStartedScreenState();
}

class _GetStartedScreenState extends State<GetStartedScreen>
    with TickerProviderStateMixin {
  final String _fullText = 'Meet Your Personal Digital Secretary';
  String _displayedText = '';
  int _charIndex = 0;

  // ── STAGGERED REVEAL STATE ────────────────────────────────────────────────
  // Screen reveals top-to-bottom: logo → headline block → chat bubbles
  // (one by one) → buttons. Each stage uses FadeSlideIn for a consistent
  // fade + slide-up feel across the whole screen.
  bool _logoVisible = false;
  bool _headlineBlockVisible = false;

  final List<bool> _bubbleVisible = [false, false, false, false, false];
  bool _buttonsVisible = false;

  final List<Map<String, dynamic>> _messages = [
    {'text': 'Hey Areej! What do you need today?', 'isEva': true},
    {'text': 'Add NLP Mid exam at Monday 5pm high priority', 'isEva': false},
    {
      'text': 'Done! "NLP Mid exam" added for Monday at 5pm. Anything else?',
      'isEva': true,
      'boldPart': 'NLP Mid exam',
    },
    {'text': 'Make Python Roadmap for 2 weeks', 'isEva': false},
    {
      'text': 'Learning plan ready — 5 topics, all scheduled. Let\'s go!',
      'isEva': true,
    },
  ];

  @override
  void initState() {
    super.initState();
    _startReveal();
    _markOnboardingDone();
  }

  Future<void> _markOnboardingDone() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('onboarding_completed', true);
  }

  void _startReveal() async {
    // ── Stage 1: logo ──────────────────────────────────────────────────────
    await Future.delayed(const Duration(milliseconds: 150));
    if (!mounted) return;
    setState(() => _logoVisible = true);

    // ── Stage 2: headline block (typewriter starts once it's in place) ─────
    await Future.delayed(const Duration(milliseconds: 250));
    if (!mounted) return;
    setState(() => _headlineBlockVisible = true);

    await Future.delayed(const Duration(milliseconds: 250));
    await _runTypewriter();

    // ── Stage 3: chat bubbles, one by one ────────────────────────────────
    await Future.delayed(const Duration(milliseconds: 300));
    for (int i = 0; i < _messages.length; i++) {
      await Future.delayed(const Duration(milliseconds: 400));
      if (!mounted) return;
      setState(() => _bubbleVisible[i] = true);
    }

    // ── Stage 4: buttons ─────────────────────────────────────────────────
    await Future.delayed(const Duration(milliseconds: 500));
    if (!mounted) return;
    setState(() => _buttonsVisible = true);
  }

  Future<void> _runTypewriter() async {
    for (int i = 0; i < _fullText.length; i++) {
      await Future.delayed(const Duration(milliseconds: 35));
      if (!mounted) return;
      setState(() {
        _displayedText = _fullText.substring(0, i + 1);
        _charIndex = i + 1;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final primaryText = Theme.of(context).textTheme.bodyMedium!.color!;
    final secondaryText = Theme.of(context).textTheme.bodySmall!.color!;

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(24, 24, 24, 32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ── LOGO ──────────────────────────────────────────────────────
              FadeSlideIn(
                visible: _logoVisible,
                child: Text(
                  'EVA',
                  style: AppTextStyles.logo.copyWith(color: primaryText),
                ),
              ),

              const SizedBox(height: 28),

              // ── HEADLINE (typewriter) + SUBTITLE ────────────────────────────
              FadeSlideIn(
                visible: _headlineBlockVisible,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    RichText(
                      text: TextSpan(
                        children: [
                          TextSpan(
                            text: _displayedText.replaceAll(
                              'Digital Secretary',
                              '',
                            ),
                            style: AppTextStyles.headline.copyWith(
                              fontSize: 28,
                              letterSpacing: -0.5,
                              color: primaryText,
                            ),
                          ),
                          TextSpan(
                            text: _displayedText.contains('Digital Secretary')
                                ? 'Digital Secretary'
                                : '',
                            style: AppTextStyles.headlineWithYellow.copyWith(
                              fontSize: 30,
                              color: AppColors.primary,
                            ),
                          ),
                          if (_charIndex < _fullText.length)
                            TextSpan(
                              text: '|',
                              style: TextStyle(
                                fontSize: 30,
                                color: AppColors.primary.withOpacity(0.7),
                              ),
                            ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 12),

                    Text(
                      "Enhanced Virtual Assistant",
                      style: AppTextStyles.info.copyWith(
                        fontSize: 14,
                        color: secondaryText,
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 28),

              // ── CHAT CARD ─────────────────────────────────────────────────
              _buildChatCard(isDark),

              const SizedBox(height: 36),

              // ── BUTTONS ───────────────────────────────────────────────────
              FadeSlideIn(
                visible: _buttonsVisible,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 10),
                  child: Column(
                    children: [
                      // SIGN UP
                      Container(
                        width: double.infinity,
                        height: 60,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(40),
                          gradient: LinearGradient(
                            colors: [
                              AppColors.primary,
                              AppColors.primary.withOpacity(0.8),
                            ],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: AppColors.primary.withOpacity(0.35),
                              blurRadius: 25,
                              offset: const Offset(0, 12),
                            ),
                          ],
                        ),
                        child: ElevatedButton(
                          onPressed: () {
                            context.go('/auth', extra: {'initialIndex': 1});
                          },
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.transparent,
                            shadowColor: Colors.transparent,
                            overlayColor: Colors.white.withOpacity(0.1),
                            foregroundColor: Colors.white,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(40),
                            ),
                          ),
                          child: Text(
                            'Sign Up',
                            style: AppTextStyles.button.copyWith(fontSize: 20),
                          ),
                        ),
                      ),

                      const SizedBox(height: 20),

                      // SIGN IN (ghost)
                      TextButton(
                        onPressed: () {
                          context.go('/auth', extra: {'initialIndex': 0});
                        },
                        style: TextButton.styleFrom(
                          minimumSize: const Size(double.infinity, 50),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(40),
                          ),
                        ),
                        child: RichText(
                          text: TextSpan(
                            style: AppTextStyles.subtitleSmall.copyWith(
                              fontSize: 16,
                              color: secondaryText,
                            ),
                            children: [
                              const TextSpan(text: "Already have an account? "),
                              TextSpan(
                                text: "Sign In",
                                style: AppTextStyles.subtitleSmall.copyWith(
                                  fontSize: 16,
                                  color: AppColors.primary,
                                  fontWeight: FontWeight.bold,
                                  decoration: TextDecoration.underline,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildChatCard(bool isDark) {
    final cardBg = isDark ? AppColors.cardDark : Colors.white;
    final cardBorder = isDark
        ? AppColors.borderDark
        : Colors.black.withOpacity(0.04);
    final headerBg = isDark
        ? AppColors.cardElevatedDark
        : const Color(0xFF1A1A1A);

    return Container(
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: cardBorder),
        boxShadow: [
          BoxShadow(
            color: isDark
                ? Colors.black.withOpacity(0.4)
                : Colors.black.withOpacity(0.06),
            blurRadius: 30,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: Column(
          children: [
            // ── HEADER BAR ──────────────────────────────────────────────────
            Container(
              color: headerBg,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              child: Row(
                children: [
                  Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: AppColors.primary,
                      shape: BoxShape.circle,
                    ),
                    child: const Center(
                      child: Text(
                        'E',
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                          fontStyle: FontStyle.italic,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: const [
                      Text(
                        'EVA',
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        'Online — ready to help',
                        style: TextStyle(
                          color: Color(0xFF4CAF50),
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            // ── MESSAGES ──────────────────────────────────────────────────
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: List.generate(_messages.length, (i) {
                  return FadeSlideIn(
                    visible: _bubbleVisible[i],
                    duration: const Duration(milliseconds: 400),
                    slideOffset: 0.2,
                    child: Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: DemoChatBubble(
                        text: _messages[i]['text'] as String,
                        isEva: _messages[i]['isEva'] as bool,
                        boldPart: _messages[i]['boldPart'] as String?,
                      ),
                    ),
                  );
                }),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
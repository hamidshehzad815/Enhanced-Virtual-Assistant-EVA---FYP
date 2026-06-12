import 'package:flutter/material.dart';
import '../../core/theme/app_text_style.dart';
import '../../core/theme/app_colours.dart';
import 'package:go_router/go_router.dart';

class FeaturesScreen extends StatefulWidget {
  const FeaturesScreen({super.key});

  @override
  State<FeaturesScreen> createState() => _FeaturesScreenState();
}

class _FeaturesScreenState extends State<FeaturesScreen> {
  final PageController _pageController = PageController(viewportFraction: 0.72);

  double _currentPage = 0;

  final List<Map<String, dynamic>> features = [
    {
      "number": "01",
      "emoji": "📅",
      "title": "Smart Schedule",
      "description":
          "EVA project priority calendar — say \"add FYP meeting Friday 3pm\" and she parses it instantly.",
    },
    {
      "number": "02",
      "emoji": "🧠",
      "title": "Learning Roadmaps",
      "description":
          "Tell EVA what you want to learn and for how long. She generates a full study plan and schedules every topic for you.",
    },
    {
      "number": "03",
      "emoji": "📊",
      "title": "Behaviour Learning",
      "description":
          "EVA tracks when you work best and suggests your most productive slots based on your real habits over time.",
    },
    {
      "number": "04",
      "emoji": "⏰",
      "title": "Auto Reminders",
      "description":
          "30-minute deadline alerts, overdue task nudges, and daily digest notifications — all running silently for you.",
    },
    {
      "number": "05",
      "emoji": "⛓️",
      "title": "Chained Commands",
      "description":
          "\"Add exam revision before exam\" — EVA understands dependencies and schedules everything.",
    },
    {
      "number": "06",
      "emoji": "🤝",
      "title": "Collaboration",
      "description":
          "Share tasks with friends, accept deadlines all through one EVA project.",
    },
  ];

  @override
  Widget build(BuildContext context) {
    // final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,

      // ── FLOATING CIRCLE BUTTON ──────────────────────────────────────────────
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
      floatingActionButton: Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: GestureDetector(
          onTap: () {
            if (_currentPage < features.length - 1) {
              _pageController.animateToPage(
                _currentPage.toInt() + 1,
                duration: const Duration(milliseconds: 400),
                curve: Curves.easeInOut,
              );
            } else {
              context.go('/get-started');
            }
          },
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 300),
            width: 100,
            height: 100,
            decoration: BoxDecoration(
              // cardElevatedDark in dark mode so circle is visible against gradient
              color: Colors.white.withOpacity(0.9),
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: AppColors.primary.withOpacity(0.4),
                  blurRadius: 20,
                  offset: const Offset(0, 10),
                ),
              ],
            ),
            child: Center(
              child: Text(
                _currentPage == features.length - 1 ? "Get\nStarted" : "Next",
                textAlign: TextAlign.center,
                style: AppTextStyles.button.copyWith(
                  fontSize: 16,
                  color: AppColors.primary,
                ),
              ),
            ),
          ),
        ),
      ),

      body: SafeArea(
        child: Column(
          children: [
            // ── HEADER ────────────────────────────────────────────────────────
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 20, 24, 0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'EVA',
                        style: AppTextStyles.logo.copyWith(
                          color: Theme.of(context).textTheme.bodyMedium!.color,
                        ),
                      ),
                      TextButton(
                        onPressed: () {
                          context.go('/get-started');
                        },
                        child: Text(
                          "Skip",
                          style: TextStyle(
                            color: Theme.of(context).textTheme.bodySmall!.color,
                            fontSize: 16,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  Text(
                    "WHAT EVA CAN DO",
                    style: AppTextStyles.info.copyWith(
                      letterSpacing: 1.2,
                      color: Theme.of(context).textTheme.bodySmall!.color,
                    ),
                  ),
                  const SizedBox(height: 8),
                  RichText(
                    text: TextSpan(
                      children: [
                        TextSpan(
                          text: 'Everything a student needs, ',
                          style: AppTextStyles.headline.copyWith(
                            fontSize: 28,
                            color: Theme.of(
                              context,
                            ).textTheme.bodyMedium!.color,
                          ),
                        ),
                        TextSpan(
                          text: 'understood naturally.',
                          style: AppTextStyles.headlineWithYellow.copyWith(
                            fontSize: 28,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 20),

            // ── CARDS ──────────────────────────────────────────────────────────
            Expanded(
              child: Padding(
                padding: const EdgeInsets.only(bottom: 70),
                child: PageView.builder(
                  controller: _pageController,
                  itemCount: features.length,
                  onPageChanged: (index) {
                    setState(() {
                      _currentPage = index.toDouble();
                    });
                  },
                  itemBuilder: (context, index) {
                    double diff = (_currentPage - index).abs();
                    double scale = (1 - (diff * 0.15)).clamp(0.85, 1.0);

                    return Transform(
                      alignment: Alignment.center,
                      transform: Matrix4.identity()
                        ..translate(0.0, diff * 20)
                        ..scale(scale)
                        ..rotateZ((_currentPage - index) * 0.05),
                      child: _buildCard(
                        features[index],
                        isActive: index == _currentPage.toInt(),
                      ),
                    );
                  },
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCard(Map<String, dynamic> feature, {bool isActive = false}) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    // ── Color logic ──────────────────────────────────────────────────────────
    // Active card background
    final activeBg = Theme.of(context).colorScheme.primary; // amber
    // Inactive card background
    final inactiveBg = Theme.of(context).cardColor;

    // NUMBER label color
    final numberColor = isActive
        ? Colors.black.withOpacity(0.7)
        : Theme.of(context).textTheme.bodySmall!.color;

    // TITLE color: white when active (both modes), theme primary text when not
    final titleColor = isActive
        ? Colors.white
        : Theme.of(context).textTheme.bodyMedium!.color;

    // DESCRIPTION color:
    //  • Active  → black87 in BOTH modes (as requested — don't change body text)
    //  • Inactive → theme secondary text
    final descColor = isActive
        ? Colors.black87
        : Theme.of(context).textTheme.bodySmall!.color;

    return Container(
      // ── Reduced height: was unconstrained, now we give a tighter padding ──
      width: MediaQuery.of(context).size.width * 0.62,
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 18),
      decoration: BoxDecoration(
        color: isActive ? activeBg : inactiveBg,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: isDark
              ? (isActive ? Colors.transparent : AppColors.borderDark)
              : Theme.of(context).dividerColor.withOpacity(0.2),
        ),
        boxShadow: [
          BoxShadow(
            color: isActive
                ? Theme.of(context).primaryColor.withOpacity(0.3)
                : (isDark
                      ? Colors.black.withOpacity(0.4)
                      : Colors.black.withOpacity(0.08)),
            blurRadius: isActive ? 30 : 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min, // shrink-wrap height
        children: [
          // Number label
          Text(
            feature["number"],
            style: AppTextStyles.info.copyWith(
              fontSize: 13,
              color: numberColor,
            ),
          ),
          const SizedBox(height: 10),

          // Emoji
          Text(feature["emoji"], style: const TextStyle(fontSize: 40)),
          const SizedBox(height: 12),

          // Title — white on active, theme color on inactive
          Text(
            feature["title"],
            style: AppTextStyles.logo.copyWith(fontSize: 20, color: titleColor),
          ),
          const SizedBox(height: 8),

          // Description — always black87 on active, secondary text on inactive
          Text(
            feature["description"],
            style: AppTextStyles.body.copyWith(
              fontSize: 13.5,
              color: descColor,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }
}

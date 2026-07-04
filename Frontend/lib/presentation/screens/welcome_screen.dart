import 'package:flutter/material.dart';
import 'package:lottie/lottie.dart';
import '../../core/theme/app_text_style.dart';
import 'package:go_router/go_router.dart';

class WelcomeScreen extends StatelessWidget {
  const WelcomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final textColor = Theme.of(context).textTheme.bodyMedium!.color!;

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 40),

              // Logo
              Text("EVA", style: AppTextStyles.logo.copyWith(color: textColor)),
              const SizedBox(height: 140),
              Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  SizedBox(
                    width: MediaQuery.of(context).size.width * 0.5,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Your',
                          style: AppTextStyles.headline.copyWith(
                            color: textColor,
                          ),
                        ),
                        Text(
                          'Academic',
                          style: AppTextStyles.headlineWithYellow,
                        ),
                        Text(
                          'Assistant',
                          style: AppTextStyles.headline.copyWith(
                            color: textColor,
                          ),
                        ),
                      ],
                    ),
                  ),

                  const Spacer(),

                  SizedBox(
                    height: 149,
                    width: 148,
                    child: Lottie.asset(
                      'assets/lottie/message.json',
                      fit: BoxFit.contain,
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 20),

              Text(
                'EVA understands plain English to manage your tasks, deadlines, and study plans — all through one simple conversation powered by AI trained just for students.',
                style: AppTextStyles.body.copyWith(
                  color: Theme.of(context).textTheme.bodySmall!.color,
                ),
              ),

              const SizedBox(height: 30),

              Center(
                child: Column(
                  children: [
                    SizedBox(
                      width: 260,
                      child: ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Theme.of(
                            context,
                          ).colorScheme.primary,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 16),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(30),
                          ),
                        ),
                        onPressed: () {
                          context.go('/get-started');
                        },
                        child: Text('Get Started', style: AppTextStyles.button),
                      ),
                    ),

                    const SizedBox(height: 12),

                    SizedBox(
                      width: 260,
                      child: OutlinedButton(
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 16),
                          side: BorderSide(
                            color: Theme.of(context).colorScheme.primary,
                          ),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(30),
                          ),
                        ),
                        onPressed: () {
                          context.go('/features');
                        },
                        child: Text(
                          'See Features',
                          style: TextStyle(
                            color: Theme.of(context).colorScheme.primary,
                            fontWeight: FontWeight.w600,
                            fontSize: 16,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 25),

              Center(
                child: Text(
                  "AI-POWERED • FOR STUDENTS",
                  style: AppTextStyles.info.copyWith(
                    color: Theme.of(context).textTheme.bodySmall!.color,
                  ),
                ),
              ),

              const SizedBox(height: 10),
            ],
          ),
        ),
      ),
    );
  }
}
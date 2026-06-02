import 'package:flutter/material.dart';
import '../../core/theme/app_text_style.dart';

class AnalyticsScreen extends StatelessWidget {
  const AnalyticsScreen({super.key});
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Text('Analytics & Behavior Insights', style: AppTextStyles.body),
      ),
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
    );
  }
}

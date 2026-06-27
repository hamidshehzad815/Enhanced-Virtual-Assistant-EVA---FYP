import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/roadmap_viewmodel.dart';
import '../widgets/plan_card.dart';
import 'package:go_router/go_router.dart';
import 'roadmap_data.dart';
import '../../core/theme/app_text_style.dart';
import 'package:lottie/lottie.dart';

class RoadmapScreen extends StatefulWidget {
  const RoadmapScreen({super.key});

  @override
  State<RoadmapScreen> createState() => _RoadmapScreenState();
}

class _RoadmapScreenState extends State<RoadmapScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<RoadmapViewmodel>().loadPlans();
    });
  }

  void _showInfoSheet() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      builder: (_) => _InfoSheet(roadmaps: kAllRoadmaps),
    );
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<RoadmapViewmodel>();
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: AppBar(
        title: const Text('My Learning Plans'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.info_outline_rounded),
            onPressed: _showInfoSheet,
          ),
        ],
      ),
      body: vm.isLoading
          ? const Center(child: CircularProgressIndicator())
          : vm.error != null
          ? Center(child: Text('Error: ${vm.error}', style: AppTextStyles.body))
          : vm.plans.isEmpty
          ? Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  SizedBox(
                    width: 300,
                    height: 300,
                    child: Lottie.asset(
                      'assets/lottie/no_plan.json',
                      fit: BoxFit.contain,
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'No learning plans yet',
                    style: AppTextStyles.headline.copyWith(
                      fontSize: 20,
                      fontWeight: FontWeight.w600,
                      color: isDark ? Colors.white70 : Colors.black54,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Create your first plan in the chat!',
                    style: AppTextStyles.body.copyWith(
                      color: isDark ? Colors.white38 : Colors.black38,
                    ),
                  ),
                ],
              ),
            )
          : ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              itemCount: vm.plans.length,
              itemBuilder: (context, index) {
                final plan = vm.plans[index];
                return PlanCard(
                  plan: plan,
                  isDark: isDark,
                  onTap: () async {
                    await context.pushNamed(
                      'roadmap-detail',
                      pathParameters: {'goalId': plan.id},
                    );
                    if (context.mounted) {
                      context.read<RoadmapViewmodel>().loadPlans();
                    }
                  },
                );
              },
            ),
    );
  }
}

// ── Info Sheet (same as previous LangSheet but uses RoadmapInfo) ──
class _InfoSheet extends StatelessWidget {
  final List<RoadmapInfo> roadmaps;
  const _InfoSheet({required this.roadmaps});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bg = isDark ? const Color(0xFF1C1C1E) : const Color(0xFFFFFBF0);
    final titleClr = isDark ? Colors.white : const Color(0xFF3A2E00);
    final subClr = isDark ? Colors.white70 : const Color(0xFF7A6830);
    final divClr = isDark ? Colors.white24 : const Color(0xFFE8DDB0);

    return Container(
      decoration: BoxDecoration(
        color: bg,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
      ),
      constraints: BoxConstraints(
        maxHeight: MediaQuery.of(context).size.height * 0.78,
      ),
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 14, 20, 0),
            child: Column(
              children: [
                Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: isDark ? Colors.white38 : const Color(0xFFD4C9A0),
                    borderRadius: BorderRadius.circular(99),
                  ),
                ),
                const SizedBox(height: 16),
                Align(
                  alignment: Alignment.centerLeft,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Available Roadmaps',
                        style: AppTextStyles.titleMedium.copyWith(
                          fontSize: 17,
                          fontWeight: FontWeight.w600,
                          color: titleClr,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        'Languages & tracks you can learn',
                        style: AppTextStyles.subtitleSmall.copyWith(
                          fontSize: 12,
                          color: subClr,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 14),
                Divider(height: 1, thickness: 0.5, color: divClr),
              ],
            ),
          ),
          Expanded(
            child: ListView.separated(
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 32),
              itemCount: roadmaps.length,
              separatorBuilder: (_, __) =>
                  Divider(height: 1, thickness: 0.5, color: divClr),
              itemBuilder: (_, i) {
                final r = roadmaps[i];
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 13),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        width: 40,
                        height: 40,
                        decoration: BoxDecoration(
                          color: r.bg,
                          borderRadius: BorderRadius.circular(11),
                        ),
                        child: Icon(r.icon, size: 20, color: r.color),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              r.name,
                              style: AppTextStyles.body.copyWith(
                                fontSize: 14,
                                fontWeight: FontWeight.w500,
                                color: titleClr,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              r.category,
                              style: AppTextStyles.body.copyWith(
                                fontSize: 11,
                                color: subClr,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              r.desc,
                              style: AppTextStyles.body.copyWith(
                                fontSize: 11,
                                color: isDark
                                    ? Colors.white60
                                    : const Color(0xFF5A4A10),
                                height: 1.4,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

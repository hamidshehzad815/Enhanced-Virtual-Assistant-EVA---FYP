import 'package:flutter/material.dart';
import '../../core/theme/app_text_style.dart';
import '../../data/models/roadmap_model.dart';
import '../../core/theme/app_colours.dart';
import 'package:intl/intl.dart';
import '../../presentation/screens/roadmap_data.dart';

class PlanCard extends StatelessWidget {
  final PlanSummary plan;
  final bool isDark;
  final VoidCallback onTap;

  const PlanCard({
    super.key,
    required this.plan,
    required this.isDark,
    required this.onTap,
  });

  Color _getStatusColor(String status) {
    switch (status) {
      case 'active':
        return Colors.green;
      case 'paused':
        return Colors.orange;
      case 'completed':
        return Colors.green;
      case 'cancelled':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  String _formatDate(DateTime dt) {
    return DateFormat('MMM d, y').format(dt);
  }

  @override
  Widget build(BuildContext context) {
    final cardBg = isDark ? const Color(0xFF1C1C1E) : Colors.white;
    final borderClr = isDark ? const Color(0xFF2C2C2E) : Colors.grey;
    final textClr = isDark ? Colors.white : const Color(0xFF1C1C1E);
    final subClr = isDark ? Colors.white70 : Colors.black54;

    // ─── Ensure start date is before end date ──────────────────────
    DateTime start = plan.startDate;
    DateTime end = plan.endDate;
    if (start.isAfter(end)) {
      final temp = start;
      start = end;
      end = temp;
    }

    final statusColor = _getStatusColor(plan.status);
    final langIcon = getLanguageIconByKey(plan.languageKey) ?? Icons.code;
    final langColor =
        getLanguageColorByKey(plan.languageKey) ?? AppColors.primary;

    // ─── Progress data from session summary ──────────────────────────
    final total = plan.totalTopics;
    final completed = plan.summary.completed;
    final skipped = plan.summary.skipped;
    final done = completed + skipped;
    final remaining = total - done;

    // ─── Text: "completed+skipped / total topics" ────────────────────
    final progressText = '$done / $total topics';
    final progressPercent = total > 0 ? (done / total * 100) : 0.0;

    return Card(
      elevation: 4,
      color: cardBg,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: borderClr, width: 0.5),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ─── Top row: Language icon + Title + Status ────────────────
              Row(
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: langColor.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(langIcon, size: 22, color: langColor),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      plan.title,
                      style: AppTextStyles.headline.copyWith(
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                        color: textClr,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: statusColor.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: statusColor.withOpacity(0.3)),
                    ),
                    child: Text(
                      plan.status.toUpperCase(),
                      style: AppTextStyles.body.copyWith(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        color: statusColor,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // ─── Date range and session count ────────────────────────────
              Row(
                children: [
                  Row(
                    children: [
                      Icon(
                        Icons.calendar_today_rounded,
                        size: 14,
                        color: subClr,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        '${_formatDate(start)} → ${_formatDate(end)}',
                        style: AppTextStyles.body.copyWith(
                          fontSize: 12,
                          color: subClr,
                        ),
                      ),
                    ],
                  ),
                  const Spacer(),
                  Row(
                    children: [
                      Icon(Icons.school_rounded, size: 14, color: subClr),
                      const SizedBox(width: 4),
                      Text(
                        '${plan.sessionCount} sessions',
                        style: AppTextStyles.body.copyWith(
                          fontSize: 12,
                          color: subClr,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // ─── Progress text ─────────────────────────────────────────────
              Row(
                children: [
                  Text(
                    progressText,
                    style: AppTextStyles.body.copyWith(
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                      color: textClr,
                    ),
                  ),
                  const Spacer(),
                  Text(
                    '${progressPercent.toStringAsFixed(0)}%',
                    style: AppTextStyles.body.copyWith(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: AppColors.primary,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),

              // ─── Multi‑coloured progress bar ──────────────────────────────
              ClipRRect(
                borderRadius: BorderRadius.circular(6),
                child: Row(
                  children: [
                    if (completed > 0)
                      Expanded(
                        flex: completed,
                        child: Container(height: 8, color: AppColors.primary),
                      ),
                    // Skipped (green)
                    if (skipped > 0)
                      Expanded(
                        flex: skipped,
                        child: Container(height: 8, color: Colors.green),
                      ),
                    if (remaining > 0)
                      Expanded(
                        flex: remaining,
                        child: Container(
                          height: 8,
                          color: isDark ? Colors.white12 : Colors.grey.shade200,
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

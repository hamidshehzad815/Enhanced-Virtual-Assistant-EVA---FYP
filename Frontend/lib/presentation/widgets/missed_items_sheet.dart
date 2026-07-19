import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_colours.dart';
import '../../data/models/calendar_task_model.dart';
import '../../data/models/roadmap_model.dart';
import '../../data/repositories/roadmap_repository.dart';
import '../providers/calendar_viewmodel.dart';
import 'task_edit_sheet.dart';

/// Bottom sheet shown on app open when the user has overdue roadmap
/// sessions and/or overdue tasks — nothing gets auto-completed; the user
/// explicitly chooses Complete or Reschedule for each item.
Future<void> showMissedItemsSheet(
  BuildContext context, {
  required List<OverdueSessionItem> overdueSessions,
  required List<CalendarTask> overdueTasks,
}) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (sheetContext) => _MissedItemsSheet(
      initialSessions: overdueSessions,
      initialTasks: overdueTasks,
    ),
  );
}

class _MissedItemsSheet extends StatefulWidget {
  final List<OverdueSessionItem> initialSessions;
  final List<CalendarTask> initialTasks;

  const _MissedItemsSheet({
    required this.initialSessions,
    required this.initialTasks,
  });

  @override
  State<_MissedItemsSheet> createState() => _MissedItemsSheetState();
}

class _MissedItemsSheetState extends State<_MissedItemsSheet> {
  late List<OverdueSessionItem> _sessions;
  late List<CalendarTask> _tasks;
  final Set<String> _busyIds = {};

  @override
  void initState() {
    super.initState();
    _sessions = List.of(widget.initialSessions);
    _tasks = List.of(widget.initialTasks);
  }

  bool get _isEmpty => _sessions.isEmpty && _tasks.isEmpty;

  Future<void> _completeSession(OverdueSessionItem item) async {
    setState(() => _busyIds.add(item.session.id));
    try {
      await context.read<RoadmapRepository>().updateSession(
            goalId: item.goalId,
            sessionId: item.session.id,
            status: 'completed',
          );
      if (!mounted) return;
      await context.read<CalendarViewModel>().loadTasks();
      if (!mounted) return;
      setState(() {
        _sessions.removeWhere((s) => s.session.id == item.session.id);
        _busyIds.remove(item.session.id);
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _busyIds.remove(item.session.id));
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to complete session: $e')),
      );
    }
  }

  void _rescheduleSession(OverdueSessionItem item) {
    setState(() => _sessions.removeWhere((s) => s.session.id == item.session.id));
    Navigator.of(context).pop();
    context.push('/roadmap-detail/${item.goalId}');
  }

  Future<void> _completeTask(CalendarTask task) async {
    setState(() => _busyIds.add(task.id));
    try {
      await context.read<CalendarViewModel>().toggleTask(task);
      if (!mounted) return;
      setState(() {
        _tasks.removeWhere((t) => t.id == task.id);
        _busyIds.remove(task.id);
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _busyIds.remove(task.id));
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to complete task: $e')),
      );
    }
  }

  void _rescheduleTask(CalendarTask task) {
    final calendarVm = context.read<CalendarViewModel>();
    setState(() => _tasks.removeWhere((t) => t.id == task.id));
    showTaskEditSheet(
      context,
      viewModel: calendarVm,
      task: task,
      onSaved: () => calendarVm.loadTasks(),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textColor = isDark ? AppColors.primaryTextDark : AppColors.primaryTextLight;
    final subTextColor =
        isDark ? AppColors.secondaryTextDark : AppColors.secondaryTextLight;
    final cardColor = isDark ? AppColors.cardDark : AppColors.cardLight;

    return SafeArea(
      child: Container(
        margin: const EdgeInsets.only(top: 60),
        decoration: BoxDecoration(
          color: cardColor,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: subTextColor.withOpacity(0.3),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              Text(
                _isEmpty ? "You're all caught up" : 'You missed some items',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: textColor,
                ),
              ),
              const SizedBox(height: 4),
              if (!_isEmpty)
                Text(
                  'Mark them complete or reschedule — nothing is auto-completed for you.',
                  style: TextStyle(fontSize: 13, color: subTextColor),
                ),
              const SizedBox(height: 16),
              Flexible(
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      ..._sessions.map(
                        (item) => _MissedSessionTile(
                          item: item,
                          busy: _busyIds.contains(item.session.id),
                          onComplete: () => _completeSession(item),
                          onReschedule: () => _rescheduleSession(item),
                        ),
                      ),
                      ..._tasks.map(
                        (task) => _MissedTaskTile(
                          task: task,
                          busy: _busyIds.contains(task.id),
                          onComplete: () => _completeTask(task),
                          onReschedule: () => _rescheduleTask(task),
                        ),
                      ),
                      if (_isEmpty)
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 24),
                          child: Center(
                            child: Icon(
                              Icons.check_circle_rounded,
                              color: AppColors.primary,
                              size: 40,
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: Text(_isEmpty ? 'Close' : "I'll do this later"),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MissedItemCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final String timeLabel;
  final bool busy;
  final VoidCallback onComplete;
  final VoidCallback onReschedule;

  const _MissedItemCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.timeLabel,
    required this.busy,
    required this.onComplete,
    required this.onReschedule,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textColor = isDark ? AppColors.primaryTextDark : AppColors.primaryTextLight;
    final subTextColor =
        isDark ? AppColors.secondaryTextDark : AppColors.secondaryTextLight;
    final borderColor = isDark ? AppColors.borderDark : AppColors.borderLight;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        border: Border.all(color: borderColor),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: Colors.redAccent, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                        color: textColor,
                      ),
                    ),
                    if (subtitle.isNotEmpty)
                      Text(
                        subtitle,
                        style: TextStyle(fontSize: 12, color: subTextColor),
                      ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Padding(
            padding: const EdgeInsets.only(left: 28),
            child: Text(
              'Overdue since $timeLabel',
              style: const TextStyle(
                fontSize: 12,
                color: Colors.redAccent,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: busy ? null : onReschedule,
                  child: const Text('Reschedule'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: ElevatedButton(
                  onPressed: busy ? null : onComplete,
                  child: busy
                      ? const SizedBox(
                          height: 16,
                          width: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Text('Complete'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _MissedSessionTile extends StatelessWidget {
  final OverdueSessionItem item;
  final bool busy;
  final VoidCallback onComplete;
  final VoidCallback onReschedule;

  const _MissedSessionTile({
    required this.item,
    required this.busy,
    required this.onComplete,
    required this.onReschedule,
  });

  @override
  Widget build(BuildContext context) {
    final scheduled = item.session.scheduledDate;
    final timeLabel = scheduled != null
        ? DateFormat('MMM d, h:mm a').format(scheduled.toLocal())
        : '';
    return _MissedItemCard(
      icon: Icons.school_rounded,
      title: item.session.title,
      subtitle: item.goalTitle,
      timeLabel: timeLabel,
      busy: busy,
      onComplete: onComplete,
      onReschedule: onReschedule,
    );
  }
}

class _MissedTaskTile extends StatelessWidget {
  final CalendarTask task;
  final bool busy;
  final VoidCallback onComplete;
  final VoidCallback onReschedule;

  const _MissedTaskTile({
    required this.task,
    required this.busy,
    required this.onComplete,
    required this.onReschedule,
  });

  @override
  Widget build(BuildContext context) {
    final timeLabel = DateFormat('MMM d, h:mm a').format(task.dueDateTime);
    return _MissedItemCard(
      icon: Icons.task_alt_rounded,
      title: task.title,
      subtitle: '',
      timeLabel: timeLabel,
      busy: busy,
      onComplete: onComplete,
      onReschedule: onReschedule,
    );
  }
}

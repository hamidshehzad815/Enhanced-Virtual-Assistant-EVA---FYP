import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/roadmap_session_viewmodel.dart';
import '../widgets/winding_trail.dart';
import '../widgets/session_popup.dart';
import '../widgets/collaborator_avatars.dart';
import '../../core/theme/app_colours.dart';
import '../../core/theme/app_text_style.dart';
import '../../data/repositories/roadmap_repository.dart';
import 'package:lottie/lottie.dart';
import 'roadmap_data.dart';
import '../../data/models/roadmap_model.dart';

class RoadmapSessionScreen extends StatefulWidget {
  final String goalId;
  const RoadmapSessionScreen({super.key, required this.goalId});

  @override
  State<RoadmapSessionScreen> createState() => _RoadmapSessionScreenState();
}

class _RoadmapSessionScreenState extends State<RoadmapSessionScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {});
  }

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (context) => RoadmapSessionViewmodel(
        context.read<RoadmapRepository>(),
        widget.goalId,
      ),
      child: const _RoadmapSessionScreenContent(),
    );
  }
}

class _RoadmapSessionScreenContent extends StatefulWidget {
  const _RoadmapSessionScreenContent();

  @override
  State<_RoadmapSessionScreenContent> createState() =>
      _RoadmapSessionScreenContentState();
}

class _RoadmapSessionScreenContentState
    extends State<_RoadmapSessionScreenContent> {
  bool _initialized = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_initialized) {
      _initialized = true;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        context.read<RoadmapSessionViewmodel>().loadRoadmap();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<RoadmapSessionViewmodel>();
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final roadmap = vm.roadmap;
    final sessions = roadmap?.sessions ?? [];

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: SafeArea(
        child: Column(
          children: [
            _buildCustomHeader(vm, roadmap, isDark),
            if (roadmap != null && roadmap.collaborators.isNotEmpty)
              _buildCollaboratorsBar(roadmap, isDark),
            Expanded(
              child: vm.isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : vm.error != null
                  ? Center(
                      child: Text(
                        'Error: ${vm.error}',
                        style: AppTextStyles.body,
                      ),
                    )
                  : roadmap == null
                  ? const Center(child: Text('Plan not found'))
                  : roadmap.status == 'paused'
                  ? _buildPausedOverlay(roadmap, isDark)
                  : WindingTrail(
                      sessions: sessions,
                      isDark: isDark,
                      languageIcon:
                          getLanguageIconByKey(roadmap.languageKey) ??
                          Icons.code,
                      languageColor:
                          getLanguageColorByKey(roadmap.languageKey) ??
                          AppColors.primary,
                      onSessionTap: (session) {
                        _showSessionPopup(context, vm, session, isDark);
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }

  // ─── Custom Header ─────────────────────────────────────────────────────
  Widget _buildCustomHeader(
    RoadmapSessionViewmodel vm,
    RoadmapDetail? roadmap,
    bool isDark,
  ) {
    final cardBg = isDark ? const Color(0xFF1C1C1E) : Colors.white;
    final borderClr = isDark ? const Color(0xFF2C2C2E) : Colors.grey;
    final textClr = isDark ? Colors.white : const Color(0xFF1C1C1E);

    return Container(
      margin: const EdgeInsets.fromLTRB(16, 12, 16, 8),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: borderClr),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(isDark ? 0.18 : 0.06),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          // ─── Back button ──────────────────────────────────────────────
          GestureDetector(
            onTap: () => Navigator.pop(context),
            child: Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: isDark ? Colors.white12 : Colors.grey.shade100,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(
                Icons.arrow_back_ios_new_rounded,
                size: 18,
                color: textClr,
              ),
            ),
          ),
          const SizedBox(width: 8),
          // ─── Title ──────────────────────────────────────────────────────
          Expanded(
            child: Text(
              roadmap != null ? '${roadmap.title} Sessions' : 'Sessions',
              style: AppTextStyles.headline.copyWith(
                fontSize: 16,
                fontWeight: FontWeight.w700,
                color: textClr,
              ),
            ),
          ),
          SizedBox(width: 4),
          // ─── Status Dropdown ──────────────────────────────────────────
          if (roadmap != null) _buildStatusDropdown(vm, roadmap, isDark),
        ],
      ),
    );
  }

  // ─── Status Dropdown (menu only shows actions) ──────────────────────
  Widget _buildStatusDropdown(
    RoadmapSessionViewmodel vm,
    RoadmapDetail roadmap,
    bool isDark,
  ) {
    final currentStatus = roadmap.status;
    final statusColor = _getStatusColor(currentStatus);

    // Determine actions based on current status
    final actions = <String, String>{};
    if (currentStatus == 'active') {
      actions['pause'] = 'Pause';
    } else if (currentStatus == 'paused') {
      actions['resume'] = 'Resume';
    }
    actions['cancel'] = 'Cancel';

    return PopupMenuButton<String>(
      offset: const Offset(0, 40),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      color: isDark ? const Color(0xFF2C2C2E) : Colors.white,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: statusColor.withOpacity(0.10),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: statusColor.withOpacity(0.2)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              currentStatus.toUpperCase(),
              style: AppTextStyles.body.copyWith(
                fontSize: 10,
                fontWeight: FontWeight.w700,
                color: statusColor,
                letterSpacing: 0.5,
              ),
            ),
            const SizedBox(width: 4),
            Icon(Icons.arrow_drop_down_rounded, size: 18, color: statusColor),
          ],
        ),
      ),
      onSelected: (value) async {
        if (value == 'cancel') {
          final confirm = await showDialog<bool>(
            context: context,
            builder: (context) => AlertDialog(
              title: const Text('Cancel Plan?'),
              content: const Text(
                'Are you sure you want to cancel this learning plan? This cannot be undone.',
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context, false),
                  child: const Text('No'),
                ),
                TextButton(
                  onPressed: () => Navigator.pop(context, true),
                  child: const Text('Yes', style: TextStyle(color: Colors.red)),
                ),
              ],
            ),
          );
          if (confirm == true) {
            await vm.updatePlanStatus('cancelled');
            if (context.mounted) Navigator.pop(context);
          }
        } else if (value == 'pause') {
          await vm.updatePlanStatus('paused');
        } else if (value == 'resume') {
          await vm.updatePlanStatus('active');
        }
      },
      itemBuilder: (context) {
        return actions.entries.map((entry) {
          final key = entry.key;
          final label = entry.value;
          IconData icon;
          Color color;
          if (key == 'pause') {
            icon = Icons.pause_rounded;
            color = Colors.orange;
          } else if (key == 'resume') {
            icon = Icons.play_arrow_rounded;
            color = Colors.green;
          } else {
            icon = Icons.delete_outline_rounded;
            color = Colors.red;
          }
          return PopupMenuItem<String>(
            value: key,
            child: Row(
              children: [
                Icon(icon, size: 16, color: color),
                const SizedBox(width: 8),
                Text(label, style: TextStyle(color: color)),
              ],
            ),
          );
        }).toList();
      },
    );
  }

  // ─── Collaborators bar (tap to view progress) ────────────────────────
  Widget _buildCollaboratorsBar(RoadmapDetail roadmap, bool isDark) {
    final collaborators = roadmap.collaborators;
    final cardBg = isDark ? const Color(0xFF1C1C1E) : Colors.white;
    final borderClr = isDark ? const Color(0xFF2C2C2E) : Colors.grey.shade200;
    final textClr = isDark ? Colors.white : const Color(0xFF1C1C1E);

    // One-line summary: for a single accepted collaborator show where they are;
    // otherwise a simple count.
    String summary;
    final accepted = collaborators.where((c) => c.isAccepted).toList();
    if (collaborators.length == 1) {
      final c = collaborators.first;
      final name = c.user.name.isNotEmpty ? c.user.name : '@${c.user.username}';
      if (c.isPending) {
        summary = '$name · invited';
      } else if (c.progress?.isFinished == true) {
        summary = '$name finished the roadmap 🎉';
      } else if (c.progress?.currentOrder != null) {
        summary =
            '$name · on session ${c.progress!.currentOrder} of ${roadmap.sessionCount}';
      } else {
        summary = '$name is collaborating';
      }
    } else {
      final invited = collaborators.length - accepted.length;
      summary = invited > 0
          ? '${collaborators.length} collaborators · $invited invited'
          : '${collaborators.length} learning with you';
    }

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
      child: Material(
        color: cardBg,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: () => _showCollaboratorsSheet(roadmap, isDark),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: borderClr),
            ),
            child: Row(
              children: [
                CollaboratorAvatarStack(collaborators: collaborators, radius: 14),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    summary,
                    style: TextStyle(
                      fontSize: 12.5,
                      fontWeight: FontWeight.w600,
                      color: textClr,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                Icon(
                  Icons.chevron_right_rounded,
                  size: 20,
                  color: Theme.of(context).hintColor,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  void _showCollaboratorsSheet(RoadmapDetail roadmap, bool isDark) {
    showModalBottomSheet(
      context: context,
      // Dark theme's scaffoldBackgroundColor is transparent (gradient is drawn
      // separately), so use an explicit opaque surface for the sheet.
      backgroundColor: isDark ? const Color(0xFF1C1C1E) : Colors.white,
      barrierColor: Colors.black54,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey.shade400,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Icon(Icons.groups_rounded, color: AppColors.primary, size: 20),
                const SizedBox(width: 8),
                Text(
                  'Collaborators',
                  style: AppTextStyles.headline.copyWith(fontSize: 17),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              'How everyone is progressing on this roadmap',
              style: TextStyle(
                fontSize: 12,
                color: Theme.of(context).hintColor,
              ),
            ),
            const SizedBox(height: 8),
            for (final c in roadmap.collaborators)
              CollaboratorProgressTile(
                collaborator: c,
                totalSessions: roadmap.sessionCount,
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildPausedOverlay(RoadmapDetail roadmap, bool isDark) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          SizedBox(
            width: 300,
            height: 300,
            child: Lottie.asset(
              'assets/lottie/girl_with_books.json',
              fit: BoxFit.contain,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            'Plan is paused',
            style: AppTextStyles.headline.copyWith(
              fontSize: 22,
              color: isDark ? Colors.white : Colors.black87,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Resume the plan to continue your sessions.',
            style: AppTextStyles.body.copyWith(
              color: isDark ? Colors.white54 : Colors.black38,
            ),
          ),
        ],
      ),
    );
  }

  void _showSessionPopup(
    BuildContext context,
    RoadmapSessionViewmodel vm,
    Session session,
    bool isDark,
  ) {
    showDialog(
      context: context,
      builder: (context) {
        return SessionPopup(
          session: session,
          isDark: isDark,
          collaborators: vm.roadmap?.collaborators ?? const [],
          fetchLatestSession: (sessionId) async {
            return await vm.getSessionDetail(sessionId);
          },
          fetchScheduleDates: () => vm.getScheduleDates(),
          onUpdate: (updatedSession) async {
            await vm.loadRoadmap();
          },
          onReschedule: (sessionId, date) async {
            await vm.updateSession(sessionId: sessionId, scheduledDate: date);
            if (context.mounted) Navigator.pop(context);
          },
          onComplete: (sessionId) async {
            await vm.updateSession(sessionId: sessionId, status: 'completed');
            if (context.mounted) Navigator.pop(context);
          },
          onSkip: (sessionId) async {
            await vm.updateSession(sessionId: sessionId, status: 'skipped');
            if (context.mounted) Navigator.pop(context);
          },
        );
      },
    );
  }

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
}

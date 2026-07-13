import 'dart:math';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../core/theme/app_colours.dart';
import '../../core/theme/app_text_style.dart';
import '../../data/models/roadmap_model.dart';

class WindingTrail extends StatelessWidget {
  final List<Session> sessions;
  final bool isDark;
  final IconData languageIcon;
  final Color languageColor;
  final void Function(Session) onSessionTap;

  const WindingTrail({
    super.key,
    required this.sessions,
    required this.isDark,
    required this.languageIcon,
    required this.languageColor,
    required this.onSessionTap,
  });

  List<double> _xPositions(double availableWidth, int count) {
    const pillW = 240.0;
    const margin = 20.0;
    final leftX = margin;
    final rightX = availableWidth - margin - pillW;
    return List.generate(count, (i) => i.isEven ? leftX : rightX);
  }

  @override
  Widget build(BuildContext context) {
    final nodes = sessions;
    const pillWidth = 240.0;
    const pillHeight = 70.0;
    const nodeSpacing = 190.0;
    const topPadding = 20.0;
    const bottomPadding = 16.0;
    final totalHeight = max(nodes.length * nodeSpacing + 10.0, 700.0);

    return LayoutBuilder(
      builder: (ctx, constraints) {
        final width = constraints.maxWidth;
        final xList = _xPositions(width, nodes.length);

        final centres = List.generate(nodes.length, (i) {
          final y = totalHeight - 120 - i * nodeSpacing;
          final x = xList[i] + pillWidth / 2;
          return Offset(x, y);
        });

        return SingleChildScrollView(
          physics: const BouncingScrollPhysics(),
          reverse: true,
          padding: EdgeInsets.only(top: topPadding, bottom: bottomPadding),
          child: SizedBox(
            width: width,
            height: totalHeight,
            child: Stack(
              clipBehavior: Clip.none,
              children: [
                CustomPaint(
                  size: Size(width, totalHeight),
                  painter: _TrailPainter(centres: centres, isDark: isDark),
                ),
                ...List.generate(nodes.length, (i) {
                  final session = nodes[i];
                  final centre = centres[i];
                  final pillLeft = xList[i];
                  final pillTop = centre.dy - pillHeight / 2;

                  final isUpcoming =
                      session.sessionState == 'upcoming' ||
                      (!session.isCurrent && session.status == 'pending');

                  return Positioned(
                    left: pillLeft,
                    top: pillTop,
                    child: Opacity(
                      opacity: isUpcoming ? 0.5 : 1.0,
                      child: _SessionPill(
                        session: session,
                        isDark: isDark,
                        languageIcon: languageIcon,
                        languageColor: languageColor,
                        showUpcoming: isUpcoming,
                        onTap: () {
                          // ─── All non‑upcoming sessions open the dialog ───
                          if (!isUpcoming) {
                            onSessionTap(session);
                          }
                        },
                      ),
                    ),
                  );
                }),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _SessionPill extends StatelessWidget {
  final Session session;
  final bool isDark;
  final IconData languageIcon;
  final Color languageColor;
  final bool showUpcoming;
  final VoidCallback onTap;

  const _SessionPill({
    required this.session,
    required this.isDark,
    required this.languageIcon,
    required this.languageColor,
    required this.showUpcoming,
    required this.onTap,
  });

  IconData _getStatusIcon() {
    if (session.status == 'completed') return Icons.check_rounded;
    if (session.status == 'skipped') return Icons.skip_next_rounded;
    if (session.isCurrent) return Icons.play_arrow_rounded;
    return Icons.circle_rounded;
  }

  Color _getStatusColor() {
    if (session.status == 'completed') return Colors.green;
    if (session.status == 'skipped') return Colors.grey.shade500;
    if (session.isCurrent) return const Color(0xFF22C55E);
    return Colors.transparent;
  }

  String _getStatusLabel() {
    if (session.status == 'completed') return 'COMPLETED';
    if (session.status == 'skipped') return 'SKIPPED';
    if (session.isCurrent) return 'CURRENT';
    return '';
  }

  @override
  Widget build(BuildContext context) {
    final pillBg = isDark ? const Color(0xFF1C1C1E) : Colors.white;
    final borderClr = isDark
        ? const Color(0xFF2C2C2E)
        : const Color(0xFFE5E5EA);
    final primTxt = isDark ? Colors.white : const Color(0xFF1C1C1E);
    final schedule = session.scheduledDate != null
        ? DateFormat('MMM d, y').format(session.scheduledDate!.toLocal())
        : 'Not scheduled';
    final duration = '${session.estimatedDuration} min';
    final time = session.scheduledDate != null
        ? DateFormat('h:mm a').format(session.scheduledDate!.toLocal())
        : 'TBD';

    final isLocked = session.sessionState == 'locked';
    final statusIcon = _getStatusIcon();
    final statusColor = _getStatusColor();
    final statusLabel = _getStatusLabel();
    final showStatusPill = statusLabel.isNotEmpty && !showUpcoming;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(35),
        child: Container(
          width: 250,
          height: 120,
          decoration: BoxDecoration(
            color: pillBg,
            borderRadius: BorderRadius.circular(35),
            border: Border.all(color: borderClr),
            boxShadow: [
              BoxShadow(
                color: AppColors.primary.withOpacity(0.30),
                blurRadius: 14,
                offset: const Offset(0, 5),
              ),
            ],
          ),
          child: Stack(
            clipBehavior: Clip.none,
            children: [
              // ─── Main row ──────────────────────────────────────────────
              Row(
                children: [
                  const SizedBox(width: 5),
                  SizedBox(
                    width: 62,
                    height: 62,
                    child: Stack(
                      alignment: Alignment.center,
                      children: [
                        Container(
                          width: 62,
                          height: 62,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: languageColor.withOpacity(0.15),
                            border: Border.all(
                              color: languageColor.withOpacity(0.35),
                              width: 2,
                            ),
                          ),
                        ),
                        Container(
                          width: 50,
                          height: 50,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: languageColor,
                            boxShadow: [
                              BoxShadow(
                                color: languageColor.withOpacity(0.4),
                                blurRadius: 8,
                                offset: const Offset(0, 4),
                              ),
                            ],
                          ),
                          child: Icon(
                            languageIcon,
                            size: 22,
                            color: Colors.white,
                          ),
                        ),
                        if (!showUpcoming && statusIcon != Icons.circle_rounded)
                          Positioned(
                            bottom: 0,
                            right: 0,
                            child: Container(
                              width: 24,
                              height: 24,
                              decoration: BoxDecoration(
                                color: statusColor,
                                shape: BoxShape.circle,
                                border: Border.all(
                                  color: Colors.white,
                                  width: 2,
                                ),
                              ),
                              child: Icon(
                                statusIcon,
                                size: 14,
                                color: Colors.white,
                              ),
                            ),
                          ),
                        if (isLocked && !showUpcoming)
                          Positioned(
                            top: 0,
                            right: 0,
                            child: Container(
                              width: 22,
                              height: 22,
                              decoration: BoxDecoration(
                                color: Colors.grey.shade800,
                                shape: BoxShape.circle,
                              ),
                              child: Icon(
                                Icons.lock_rounded,
                                size: 14,
                                color: Colors.white,
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          session.title,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: AppTextStyles.body.copyWith(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: primTxt,
                          ),
                        ),
                        const SizedBox(height: 3),
                        Text(
                          '$schedule · $duration',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: AppTextStyles.info.copyWith(
                            fontSize: 10,
                            color: const Color(0xFF8A84E0),
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Timing: $time',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: AppTextStyles.info.copyWith(
                            fontSize: 10,
                            color: const Color.fromARGB(255, 224, 213, 132),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 14),
                ],
              ),
              // ─── Status pill (smaller, constrained) ──────────────────
              if (showStatusPill)
                Positioned(
                  top: 14,
                  right: 10,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 3,
                      vertical: 1,
                    ),
                    constraints: const BoxConstraints(maxWidth: 80),
                    decoration: BoxDecoration(
                      color: statusColor.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: statusColor.withOpacity(0.3)),
                    ),
                    child: Text(
                      statusLabel,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 7,
                        fontWeight: FontWeight.w700,
                        color: statusColor,
                        letterSpacing: 0.3,
                      ),
                    ),
                  ),
                ),
              // ─── Upcoming overlay ──────────────────────────────────────
              if (showUpcoming)
                Positioned.fill(
                  child: Container(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(35),
                      color: Colors.black.withOpacity(0.15),
                    ),
                    child: Center(
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 14,
                          vertical: 6,
                        ),
                        decoration: BoxDecoration(
                          color: Colors.grey.shade800.withOpacity(0.85),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: const Text(
                          'UPCOMING',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: Colors.white,
                            letterSpacing: 1.2,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _TrailPainter extends CustomPainter {
  final List<Offset> centres;
  final bool isDark;

  const _TrailPainter({required this.centres, required this.isDark});

  @override
  void paint(Canvas canvas, Size size) {
    if (centres.length < 2) return;

    final paint = Paint()
      ..color = const Color(0xFF8A84E0).withOpacity(0.45)
      ..strokeWidth = 2.5
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    for (int i = 0; i < centres.length - 1; i++) {
      final from = centres[i];
      final to = centres[i + 1];

      final path = Path();
      path.moveTo(from.dx, from.dy);

      final cp1 = Offset(from.dx, from.dy - (from.dy - to.dy) * 0.4);
      final cp2 = Offset(to.dx, to.dy + (from.dy - to.dy) * 0.4);
      path.cubicTo(cp1.dx, cp1.dy, cp2.dx, cp2.dy, to.dx, to.dy);

      _drawDashedPath(canvas, path, paint);
    }
  }

  void _drawDashedPath(Canvas canvas, Path path, Paint paint) {
    const dashLength = 8.0;
    const gapLength = 5.0;

    final metrics = path.computeMetrics();
    for (final metric in metrics) {
      double distance = 0.0;
      bool draw = true;
      while (distance < metric.length) {
        final len = draw ? dashLength : gapLength;
        if (draw) {
          canvas.drawPath(metric.extractPath(distance, distance + len), paint);
        }
        distance += len;
        draw = !draw;
      }
    }
  }

  @override
  bool shouldRepaint(_TrailPainter old) =>
      old.centres != centres || old.isDark != isDark;
}

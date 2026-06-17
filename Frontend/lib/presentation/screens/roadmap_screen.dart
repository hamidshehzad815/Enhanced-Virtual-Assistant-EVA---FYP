import 'dart:math';
import 'package:Eva/core/theme/app_colours.dart';
import 'package:flutter/material.dart';
// Fonts centralized in AppTextStyles
import 'package:url_launcher/url_launcher.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import '../../data/models/roadmap_model.dart';
import '../../core/theme/app_text_style.dart';
import 'roadmap_data.dart';

// ---------- MAIN SCREEN ----------
class RoadmapScreen extends StatefulWidget {
  const RoadmapScreen({super.key});

  @override
  State<RoadmapScreen> createState() => _RoadmapScreenState();
}

class _RoadmapScreenState extends State<RoadmapScreen> {
  String _selectedId = '1';

  List<RoadmapData> get _enrolled => kUserRoadmaps;
  RoadmapData get _current => _enrolled.firstWhere((r) => r.id == _selectedId);

  void _switchRoadmap(String id) => setState(() => _selectedId = id);

  void _showInfoSheet() => showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (_) => LangSheet(roadmaps: kAllRoadmaps),
  );

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final nodes = _current.nodes;
    final cardBg = isDark ? const Color(0xFF1C1C1E) : Colors.white;
    final secondTxt = isDark
        ? const Color(0xFF8E8E93)
        : const Color(0xFF6C6C70);

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: SafeArea(
        child: Column(
          children: [
            // ── Header card (FIXED: dropdown + info icon in one row) ──
            Container(
              margin: const EdgeInsets.fromLTRB(16, 10, 16, 8),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              decoration: BoxDecoration(
                color: cardBg,
                borderRadius: BorderRadius.circular(24),
                border: Border.all(
                  color: isDark
                      ? const Color(0xFF2C2C2E)
                      : const Color(0xFFE6E6EA),
                ),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(isDark ? 0.18 : 0.06),
                    blurRadius: 16,
                    offset: const Offset(0, 6),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Title row
                  Row(
                    children: [
                      Expanded(
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Ace your',
                              style: AppTextStyles.headline.copyWith(
                                color: isDark
                                    ? Colors.white
                                    : const Color(0xFF1C1C1E),
                                fontSize: 24,
                              ),
                            ),
                            const SizedBox(width: 6),
                            Text(
                              'Learning Journey',
                              style: AppTextStyles.headlineWithYellow.copyWith(
                                fontSize: 24,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  // Controls row: dropdown + info icon side-by-side
                  Row(
                    children: [
                      Expanded(
                        child: Container(
                          height: 40,
                          padding: const EdgeInsets.symmetric(horizontal: 12),
                          decoration: BoxDecoration(
                            color: isDark
                                ? const Color(0xFF2C2C2E)
                                : const Color(0xFFF2F2F7),
                            borderRadius: BorderRadius.circular(14),
                          ),
                          child: DropdownButtonHideUnderline(
                            child: DropdownButton<String>(
                              value: _selectedId,
                              isExpanded: true,
                              icon: Icon(
                                Icons.keyboard_arrow_down_rounded,
                                size: 18,
                                color: secondTxt,
                              ),
                              style: AppTextStyles.subtitleSmall.copyWith(
                                fontSize: 13,
                                fontWeight: FontWeight.w500,
                                color: isDark
                                    ? Colors.white
                                    : const Color(0xFF1C1C1E),
                              ),
                              dropdownColor: cardBg,
                              borderRadius: BorderRadius.circular(12),
                              items: _enrolled
                                  .map(
                                    (r) => DropdownMenuItem(
                                      value: r.id,
                                      child: Text(
                                        r.name,
                                        overflow: TextOverflow.ellipsis,
                                        style: AppTextStyles.subtitleSmall
                                            .copyWith(fontSize: 13),
                                      ),
                                    ),
                                  )
                                  .toList(),
                              onChanged: (v) {
                                if (v != null) _switchRoadmap(v);
                              },
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      GestureDetector(
                        onTap: _showInfoSheet,
                        child: Container(
                          width: 40,
                          height: 40,
                          decoration: BoxDecoration(
                            color: isDark
                                ? const Color(0xFF2C2C2E)
                                : const Color(0xFFF2F2F7),
                            borderRadius: BorderRadius.circular(14),
                          ),
                          child: Icon(
                            Icons.info_outline_rounded,
                            size: 20,
                            color: secondTxt,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            // ── Winding Trail (with top padding to avoid header overlap) ──
            Expanded(
              child: nodes.isEmpty
                  ? Center(
                      child: Text(
                        'No topics available',
                        style: AppTextStyles.body.copyWith(color: secondTxt),
                      ),
                    )
                  : WindingTrailView(
                      nodes: nodes,
                      isDark: isDark,
                      languageIcon: _current.icon, // 👈 pass language icon
                      languageColor: _current.color, // 👈 pass language colour
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------- WINDING TRAIL (with top padding) ----------
class WindingTrailView extends StatelessWidget {
  final List<RoadmapNode> nodes;
  final bool isDark;
  final IconData languageIcon; // 👈 language icon for this roadmap
  final Color languageColor; // 👈 language colour for this roadmap

  const WindingTrailView({
    super.key,
    required this.nodes,
    required this.isDark,
    required this.languageIcon,
    required this.languageColor,
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
    final reversed = nodes.reversed.toList();

    const pillWidth = 240.0;
    const pillHeight = 70.0;
    const nodeSpacing = 200.0;
    const topPadding = 80.0; // 👈 extra space to avoid header
    final totalHeight = max(
      reversed.length * nodeSpacing + topPadding + 200.0,
      760.0,
    );

    return LayoutBuilder(
      builder: (ctx, constraints) {
        final width = constraints.maxWidth;
        final xList = _xPositions(width, reversed.length);

        // Centers of each pill for drawing connectors
        final centres = List.generate(reversed.length, (i) {
          final y = totalHeight - 120 - i * nodeSpacing;
          final x = xList[i] + pillWidth / 2;
          return Offset(x, y);
        });

        return SingleChildScrollView(
          physics: const BouncingScrollPhysics(),
          reverse: true,
          padding: EdgeInsets.only(top: topPadding), // 👈 shift content down
          child: SizedBox(
            width: width,
            height: totalHeight,
            child: Stack(
              clipBehavior: Clip.none,
              children: [
                // Connector lines
                CustomPaint(
                  size: Size(width, totalHeight),
                  painter: _TrailPainter(centres: centres, isDark: isDark),
                ),
                // Pill nodes
                ...List.generate(reversed.length, (i) {
                  final node = reversed[i];
                  final centre = centres[i];
                  final pillLeft = xList[i];
                  final pillTop = centre.dy - pillHeight / 2;

                  return Positioned(
                    left: pillLeft,
                    top: pillTop,
                    child: NodePill(
                      node: node,
                      isDark: isDark,
                      languageIcon: languageIcon,
                      languageColor: languageColor,
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

// ---------- TRAIL PAINTER (unchanged) ----------
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

// ---------- NODE PILL (uses language icon & colour, not node's own) ----------
class NodePill extends StatelessWidget {
  final RoadmapNode node;
  final bool isDark;
  final IconData languageIcon;
  final Color languageColor;

  const NodePill({
    super.key,
    required this.node,
    required this.isDark,
    required this.languageIcon,
    required this.languageColor,
  });

  @override
  Widget build(BuildContext context) {
    final pillBg = isDark ? const Color(0xFF1C1C1E) : Colors.white;
    final borderClr = isDark
        ? const Color(0xFF2C2C2E)
        : const Color(0xFFE5E5EA);
    final primTxt = isDark ? Colors.white : const Color(0xFF1C1C1E);
    final secTxt = isDark ? const Color(0xFF8E8E93) : const Color(0xFF6C6C70);

    void _launchUrl(String url) async {
      final Uri uri = Uri.parse(url);
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      } else {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('Cannot open this link')));
      }
    }

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () => _launchUrl(node.ytUrl),
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
          child: Row(
            children: [
              const SizedBox(width: 5),
              // ── Icon circle with outer ring (uses languageIcon & languageColor) ──
              SizedBox(
                width: 62,
                height: 62,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    // Outer ring
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
                    // Inner filled circle
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
                      child: Icon(languageIcon, size: 22, color: Colors.white),
                    ),
                    // Important indicator (if any)
                    if (node.important && node.status != NodeStatus.completed)
                      const Positioned(
                        top: 1,
                        left: 1,
                        child: CircleAvatar(
                          radius: 9,
                          backgroundColor: Color(0xFFBA7517),
                          child: Icon(
                            Icons.priority_high_rounded,
                            size: 9,
                            color: Colors.white,
                          ),
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              // ── Text details (unchanged) ──
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      node.label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: AppTextStyles.body.copyWith(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: primTxt,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      node.sub,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: AppTextStyles.body.copyWith(
                        fontSize: 11,
                        color: secTxt,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      '${node.schedule} · ${node.duration}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: AppTextStyles.info.copyWith(
                        fontSize: 10,
                        color: const Color(0xFF8A84E0),
                      ),
                    ),
                    SizedBox(height: 4),
                    Text(
                      'Timing: ${node.time}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: AppTextStyles.info.copyWith(
                        fontSize: 10,
                        color: const Color.fromARGB(255, 224, 213, 132),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Text(
                          'Watch here: ',
                          style: AppTextStyles.info.copyWith(
                            fontSize: 10,
                            color: secTxt,
                          ),
                        ),
                        FaIcon(
                          FontAwesomeIcons.youtube,
                          size: 20,
                          color: Colors.red,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 14),
            ],
          ),
        ),
      ),
    );
  }
}

// ---------- BOTTOM SHEET (unchanged) ----------
class LangSheet extends StatelessWidget {
  final List<RoadmapData> roadmaps;
  const LangSheet({super.key, required this.roadmaps});

  @override
  Widget build(BuildContext context) {
    const sheetBg = Color(0xFFFFFBF0);
    const titleClr = Color(0xFF3A2E00);
    const subClr = Color(0xFF7A6830);
    const divClr = Color(0xFFE8DDB0);

    return Container(
      decoration: const BoxDecoration(
        color: sheetBg,
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
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
                    color: const Color(0xFFD4C9A0),
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
                const Divider(height: 1, thickness: 0.5, color: divClr),
              ],
            ),
          ),
          Expanded(
            child: ListView.separated(
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 32),
              itemCount: roadmaps.length,
              separatorBuilder: (_, __) =>
                  const Divider(height: 1, thickness: 0.5, color: divClr),
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
                                color: const Color(0xFF5A4A10),
                                height: 1.4,
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 8),
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

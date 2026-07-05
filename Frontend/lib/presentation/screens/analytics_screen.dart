import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:lottie/lottie.dart';
import '../providers/analytics_viewmodel.dart';
import '../../core/theme/app_colours.dart';
import '../../core/theme/app_text_style.dart';
import '../../data/models/analytics_model.dart';

class AnalyticsScreen extends StatefulWidget {
  const AnalyticsScreen({super.key});

  @override
  State<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends State<AnalyticsScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _slideController;
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;

  @override
  void initState() {
    super.initState();
    _slideController = AnimationController(
      duration: const Duration(milliseconds: 700),
      vsync: this,
    );
    _fadeAnimation = CurvedAnimation(
      parent: _slideController,
      curve: Curves.easeOut,
    );
    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, 0.05),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _slideController, curve: Curves.easeOut));
    _slideController.forward();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<AnalyticsViewModel>().loadDashboard();
    });
  }

  @override
  void dispose() {
    _slideController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<AnalyticsViewModel>();
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final dashboard = vm.dashboard;

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: SafeArea(
        child: vm.isLoading
            ? const Center(child: CircularProgressIndicator())
            : vm.error != null
            ? _buildErrorState(vm, isDark)
            : dashboard == null
            ? _buildEmptyState(isDark)
            : FadeTransition(
                opacity: _fadeAnimation,
                child: SlideTransition(
                  position: _slideAnimation,
                  child: SingleChildScrollView(
                    physics: const BouncingScrollPhysics(),
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // ─── 1. Header ───────────────────────────────────
                        _buildHeader(vm, isDark, dashboard),
                        const SizedBox(height: 12),

                        // ─── 2. Snapshot Stats (horizontal scroll) ──────
                        _buildSnapshotStats(dashboard, isDark),
                        const SizedBox(height: 14),

                        // ─── 3. Smart Insights ──────────────────────────
                        if (dashboard.insights.isNotEmpty) ...[
                          _buildInsights(dashboard, isDark),
                          const SizedBox(height: 14),
                        ],

                        // ─── Behavioral ──────────────────────────────────────────────────────
                        _buildBehavioral(dashboard, isDark),
                        const SizedBox(height: 14),

                        // ─── 4. Productivity Score ──────────────────────
                        _buildProductivityScore(dashboard, isDark),
                        const SizedBox(height: 14),

                        // ─── 5. Daily Activity ──────────────────────────
                        _buildDailyActivity(dashboard, isDark),
                        const SizedBox(height: 14),

                        // ─── 6. Heatmap ──────────────────────────────────
                        _buildHeatmap(dashboard, isDark),
                        const SizedBox(height: 14),

                        // ─── 7. Work Patterns ──────────────────────────
                        _buildWorkPatterns(dashboard, isDark),
                        const SizedBox(height: 14),

                        // ─── 8. Needs Attention ─────────────────────────
                        _buildNeedsAttention(dashboard, isDark),
                        const SizedBox(height: 20),
                      ],
                    ),
                  ),
                ),
              ),
      ),
    );
  }

  // ─── ERROR / EMPTY STATES ──────────────────────────────────────────────
  Widget _buildErrorState(AnalyticsViewModel vm, bool isDark) {
    final subClr = isDark ? Colors.white60 : Colors.black45;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.cloud_off_rounded, size: 40, color: subClr),
            const SizedBox(height: 12),
            Text(
              'Couldn\'t load your analytics',
              style: AppTextStyles.subtitleMedium.copyWith(
                fontSize: 15,
                fontWeight: FontWeight.w700,
                color: isDark ? Colors.white : const Color(0xFF1C1C1E),
              ),
            ),
            const SizedBox(height: 6),
            Text(
              '${vm.error}',
              textAlign: TextAlign.center,
              style: AppTextStyles.body.copyWith(fontSize: 12, color: subClr),
            ),
            const SizedBox(height: 16),
            TextButton.icon(
              onPressed: () => vm.loadDashboard(),
              icon: const Icon(Icons.refresh_rounded, size: 16),
              label: const Text('Try again'),
              style: TextButton.styleFrom(foregroundColor: AppColors.primary),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState(bool isDark) {
    final subClr = isDark ? Colors.white60 : Colors.black45;
    return Center(
      child: Text(
        'No data available',
        style: AppTextStyles.body.copyWith(color: subClr),
      ),
    );
  }

  // ─── SHARED CARD DECORATION ─────────────────────────────────────────────
  BoxDecoration _cardDecoration(bool isDark, {Color? accentBorder}) {
    return BoxDecoration(
      color: isDark ? const Color(0xFF1C1C1E) : Colors.white,
      borderRadius: BorderRadius.circular(16),
      border: Border.all(
        color:
            accentBorder ??
            (isDark ? const Color(0xFF2C2C2E) : Colors.grey.shade200),
        width: accentBorder != null ? 1.2 : 1,
      ),
      boxShadow: [
        BoxShadow(
          color: Colors.black.withOpacity(isDark ? 0.10 : 0.04),
          blurRadius: 10,
          offset: const Offset(0, 2),
        ),
      ],
    );
  }

  Widget _sectionTitle(String text, bool isDark, {IconData? icon}) {
    final subClr = isDark ? Colors.white70 : Colors.black54;
    return Row(
      children: [
        if (icon != null) ...[
          Icon(icon, size: 14, color: AppColors.primary),
          const SizedBox(width: 6),
        ],
        Text(
          text,
          style: AppTextStyles.subtitleMedium.copyWith(
            fontSize: 13,
            fontWeight: FontWeight.w700,
            color: subClr,
            letterSpacing: 0.5,
          ),
        ),
      ],
    );
  }

  // ─── HEADER (unchanged) ─────────────────────────────────────────────────
  Widget _buildHeader(
    AnalyticsViewModel vm,
    bool isDark,
    AnalyticsDashboard dashboard,
  ) {
    final cardBg = isDark ? const Color(0xFF1C1C1E) : Colors.white;
    final borderClr = isDark ? const Color(0xFF2C2C2E) : Colors.grey.shade200;
    final textClr = isDark ? Colors.white : const Color(0xFF1C1C1E);
    final subClr = isDark ? Colors.white70 : Colors.black54;

    final generatedDate = DateTime.parse(dashboard.generatedAt).toLocal();

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: cardBg,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: borderClr),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(isDark ? 0.18 : 0.06),
              blurRadius: 14,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Analytics',
                    style: AppTextStyles.headline.copyWith(
                      fontSize: 22,
                      fontWeight: FontWeight.w700,
                      color: textClr,
                    ),
                  ),
                ),
                _buildDaysDropdown(vm, isDark),
              ],
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                Icon(Icons.refresh_rounded, size: 12, color: subClr),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    'Generated ${DateFormat('d MMM y, h:mm a').format(generatedDate)} · ${dashboard.timezone}',
                    style: AppTextStyles.body.copyWith(
                      fontSize: 10,
                      color: subClr,
                    ),
                    overflow: TextOverflow.ellipsis,
                    maxLines: 1,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDaysDropdown(AnalyticsViewModel vm, bool isDark) {
    final days = [7, 30, 90];
    final labels = ['7d', '30d', '90d'];

    return DropdownButton<int>(
      value: vm.selectedDays,
      underline: const SizedBox(),
      icon: Icon(
        Icons.arrow_drop_down_rounded,
        color: isDark ? Colors.white70 : Colors.black54,
      ),
      dropdownColor: isDark ? const Color(0xFF2C2C2E) : Colors.white,
      style: TextStyle(
        fontSize: 13,
        fontWeight: FontWeight.w600,
        color: isDark ? Colors.white : Colors.black87,
      ),
      borderRadius: BorderRadius.circular(10),
      items: List.generate(days.length, (i) {
        return DropdownMenuItem<int>(value: days[i], child: Text(labels[i]));
      }),
      onChanged: (value) {
        if (value != null) vm.setDays(value);
      },
    );
  }

  // ─── PRODUCTIVITY SCORE ──────────────────────────────────────────────
  Widget _buildProductivityScore(AnalyticsDashboard dashboard, bool isDark) {
    final ps = dashboard.snapshot.productivityScore;
    final textClr = isDark ? Colors.white : const Color(0xFF1C1C1E);
    final subClr = isDark ? Colors.white70 : Colors.black54;

    // Meta gating – if not enough data, show placeholder
    if (!dashboard.meta.hasEnoughData) {
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14),
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: _cardDecoration(isDark),
          child: Center(
            child: Column(
              children: [
                Lottie.asset(
                  'assets/lottie/insights.json',
                  width: 100,
                  height: 100,
                  fit: BoxFit.contain,
                ),
                const SizedBox(height: 8),
                Text(
                  'Complete ${dashboard.meta.tasksRemaining} more tasks to unlock your productivity score',
                  style: AppTextStyles.body.copyWith(
                    fontSize: 14,
                    color: subClr,
                  ),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
      );
    }
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: _cardDecoration(isDark),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            _ScoreGauge(score: ps.score, rating: ps.rating, isDark: isDark),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    ps.caption,
                    style: AppTextStyles.body.copyWith(
                      fontSize: 13,
                      height: 1.4,
                      color: textClr,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: [
                      _scoreBadge(
                        Icons.timer_rounded,
                        '${dashboard.snapshot.onTimeRate.toStringAsFixed(0)}% on time',
                        AppColors.primary,
                        isDark,
                      ),
                      _scoreBadge(
                        Icons.local_fire_department_rounded,
                        '${dashboard.snapshot.currentStreak} day streak',
                        const Color(0xFFEF6C4D),
                        isDark,
                      ),
                      _scoreBadge(
                        dashboard.snapshot.completed.changePercent >= 0
                            ? Icons.trending_up_rounded
                            : Icons.trending_down_rounded,
                        dashboard.snapshot.completed.changePercent >= 0
                            ? '↑ ${dashboard.snapshot.completed.changePercent.toStringAsFixed(1)}% vs last period'
                            : '↓ ${dashboard.snapshot.completed.changePercent.abs().toStringAsFixed(1)}% vs last period',
                        dashboard.snapshot.completed.changePercent >= 0
                            ? const Color(0xFF22C55E)
                            : const Color(0xFFEF4444),
                        isDark,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _scoreBadge(IconData icon, String label, Color color, bool isDark) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(isDark ? 0.16 : 0.10),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: color),
          const SizedBox(width: 4),
          Text(
            label,
            style: TextStyle(
              fontSize: 10,
              color: color,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  // ─── SNAPSHOT STATS (Hero cards) ────────────────────────────────────
  Widget _buildSnapshotStats(AnalyticsDashboard dashboard, bool isDark) {
    final snap = dashboard.snapshot;
    final items = [
      _StatCard(
        value: '${snap.completed.period}',
        label: 'Completed',
        change: snap.completed.changePercent,
        icon: Icons.check_circle_rounded,
        color: const Color(0xFF22C55E),
        isDark: isDark,
      ),
      _StatCard(
        value: '${snap.onTimeRate.toStringAsFixed(0)}%',
        label: 'On time',
        icon: Icons.timer_rounded,
        color: AppColors.primary,
        isDark: isDark,
      ),
      _StatCard(
        value: '${snap.currentStreak}',
        label: 'Day streak',
        icon: Icons.local_fire_department_rounded,
        color: const Color(0xFFBA7517),
        isDark: isDark,
      ),
      _StatCard(
        value: '${snap.completed.previous}',
        label: 'Previous period',
        icon: Icons.history_rounded,
        color: Colors.blue,
        isDark: isDark,
      ),
    ];

    return SizedBox(
      height: 92,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        physics: const BouncingScrollPhysics(),
        padding: const EdgeInsets.symmetric(horizontal: 14),
        itemCount: items.length,
        separatorBuilder: (_, __) => const SizedBox(width: 10),
        itemBuilder: (_, i) => items[i],
      ),
    );
  }

  // ─── INSIGHTS ─────────────────────────────────────────────────────────
  Widget _buildInsights(AnalyticsDashboard dashboard, bool isDark) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14),
          child: _sectionTitle(
            'Smart Insights',
            isDark,
            icon: Icons.auto_awesome_rounded,
          ),
        ),
        const SizedBox(height: 8),
        SizedBox(
          height: 116,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            physics: const BouncingScrollPhysics(),
            padding: const EdgeInsets.symmetric(horizontal: 14),
            itemCount: dashboard.insights.length,
            separatorBuilder: (_, __) => const SizedBox(width: 10),
            itemBuilder: (context, i) =>
                _InsightCard(insight: dashboard.insights[i], isDark: isDark),
          ),
        ),
      ],
    );
  }

  // ─── DAILY ACTIVITY (line chart) ─────────────────────────────────────
  Widget _buildDailyActivity(AnalyticsDashboard dashboard, bool isDark) {
    final activity = dashboard.activity;
    final subClr = isDark ? Colors.white70 : Colors.black54;

    final series = activity.series;
    final spots = <FlSpot>[
      for (var i = 0; i < series.length; i++)
        FlSpot(i.toDouble(), series[i].count.toDouble()),
    ];
    final maxCount = series.fold<int>(0, (m, p) => p.count > m ? p.count : m);
    final maxY = (maxCount < 4 ? 4 : maxCount + 1).toDouble();
    final lineColor = AppColors.primary;

    final xInterval = math.max(1, (series.length / 5).ceil());
    final leftInterval = math.max(1, (maxY / 4).ceil()).toDouble();

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: _cardDecoration(isDark),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _sectionTitle('Daily Activity', isDark),
            const SizedBox(height: 4),
            Text(
              '${dashboard.rangeDays} days · ${activity.activeDays} active days · ${activity.avgPerActiveDay.toStringAsFixed(1)} avg / active day',
              style: AppTextStyles.body.copyWith(fontSize: 11, color: subClr),
            ),
            const SizedBox(height: 12),
            SizedBox(
              height: 130,
              child: LineChart(
                LineChartData(
                  minX: 0,
                  maxX: (series.length - 1).toDouble(),
                  minY: 0,
                  maxY: maxY,
                  lineTouchData: LineTouchData(
                    enabled: true,
                    touchTooltipData: LineTouchTooltipData(
                      getTooltipColor: (_) =>
                          isDark ? const Color(0xFF2C2C2E) : Colors.white,
                      tooltipBorder: BorderSide(
                        color: lineColor.withOpacity(0.3),
                      ),
                      getTooltipItems: (spots) => spots.map((s) {
                        final i = s.x.toInt();
                        final d = DateTime.tryParse(series[i].date);
                        final label = d != null
                            ? DateFormat('d MMM').format(d)
                            : '';
                        return LineTooltipItem(
                          '$label\n${s.y.toInt()} tasks',
                          TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: isDark ? Colors.white : Colors.black87,
                          ),
                        );
                      }).toList(),
                    ),
                  ),
                  gridData: FlGridData(
                    show: true,
                    drawVerticalLine: false,
                    horizontalInterval: leftInterval,
                    getDrawingHorizontalLine: (value) => FlLine(
                      color: isDark ? Colors.white12 : Colors.grey.shade200,
                      strokeWidth: 1,
                    ),
                  ),
                  borderData: FlBorderData(show: false),
                  titlesData: FlTitlesData(
                    topTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false),
                    ),
                    rightTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false),
                    ),
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        interval: leftInterval,
                        reservedSize: 24,
                        getTitlesWidget: (value, meta) => Text(
                          value.toInt().toString(),
                          style: TextStyle(fontSize: 9, color: subClr),
                        ),
                      ),
                    ),
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        interval: xInterval.toDouble(),
                        reservedSize: 20,
                        getTitlesWidget: (value, meta) {
                          final i = value.round();
                          if (i < 0 || i >= series.length) {
                            return const SizedBox.shrink();
                          }
                          final d = DateTime.tryParse(series[i].date);
                          final label = d != null
                              ? DateFormat('d MMM').format(d)
                              : '';
                          return Padding(
                            padding: const EdgeInsets.only(top: 4),
                            child: Text(
                              label,
                              style: TextStyle(fontSize: 8, color: subClr),
                            ),
                          );
                        },
                      ),
                    ),
                  ),
                  lineBarsData: [
                    LineChartBarData(
                      spots: spots,
                      isCurved: true,
                      curveSmoothness: 0.25,
                      color: lineColor,
                      barWidth: 2.5,
                      dotData: FlDotData(
                        show: series.length <= 31,
                        getDotPainter: (spot, percent, bar, index) {
                          final isLast = index == spots.length - 1;
                          return FlDotCirclePainter(
                            radius: isLast ? 4 : 2.5,
                            color: lineColor,
                            strokeWidth: isLast ? 2 : 0,
                            strokeColor: lineColor.withOpacity(0.3),
                          );
                        },
                      ),
                      belowBarData: BarAreaData(
                        show: true,
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          colors: [
                            lineColor.withOpacity(0.25),
                            lineColor.withOpacity(0.0),
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
    );
  }

  // ─── HEATMAP ──────────────────────────────────────────────────────────
  Widget _buildHeatmap(AnalyticsDashboard dashboard, bool isDark) {
    final heatmap = dashboard.heatmap; // 👈 changed from productivityMap
    final textClr = isDark ? Colors.white : const Color(0xFF1C1C1E);
    final subClr = isDark ? Colors.white70 : Colors.black54;

    final maxIntensity = heatmap.cells.isNotEmpty
        ? heatmap.cells.map((c) => c.count).reduce((a, b) => a > b ? a : b)
        : 1;

    final dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    final hourLabels = [
      '6A',
      '7A',
      '8A',
      '9A',
      '10A',
      '11A',
      '12P',
      '1P',
      '2P',
      '3P',
      '4P',
      '5P',
      '6P',
      '7P',
      '8P',
      '9P',
      '10P',
      '11P',
    ];

    Map<String, HeatmapCell> cellMap = {};
    for (var cell in heatmap.cells) {
      cellMap['${cell.day}-${cell.hour}'] = cell;
    }

    final trackClr = isDark
        ? Colors.white.withOpacity(0.05)
        : Colors.grey.shade100;

    Color cellColor(int count) {
      if (count == 0) return trackClr;
      final t = (count / maxIntensity).clamp(0.0, 1.0);
      return Color.lerp(
        AppColors.primary.withOpacity(0.18),
        AppColors.primary,
        t,
      )!;
    }

    final peak = heatmap.cells.isEmpty
        ? null
        : heatmap.cells.reduce((a, b) => a.count > b.count ? a : b);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: _cardDecoration(isDark),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _sectionTitle('Heatmap', isDark),
            const SizedBox(height: 4),
            Text(
              '${dashboard.rangeDays} days · ${heatmap.hourRange.startDisplay}–${heatmap.hourRange.endDisplay}',
              style: AppTextStyles.body.copyWith(fontSize: 11, color: subClr),
            ),
            const SizedBox(height: 10),

            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const SizedBox(width: 32),
                      ...hourLabels.map(
                        (label) => SizedBox(
                          width: 18,
                          child: Text(
                            label,
                            style: TextStyle(fontSize: 7, color: subClr),
                            textAlign: TextAlign.center,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 2),
                  ...List.generate(7, (dayIndex) {
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 1),
                      child: Row(
                        children: [
                          SizedBox(
                            width: 32,
                            child: Text(
                              dayNames[dayIndex],
                              style: TextStyle(fontSize: 9, color: subClr),
                              textAlign: TextAlign.right,
                            ),
                          ),
                          ...List.generate(18, (hourIndex) {
                            final hour = hourIndex + 6;
                            final cell = cellMap['$dayIndex-$hour'];
                            final count = cell?.count ?? 0;
                            final isPeak =
                                peak != null &&
                                cell != null &&
                                peak.day == cell.day &&
                                peak.hour == cell.hour;

                            return Container(
                              width: 18,
                              height: 15,
                              margin: const EdgeInsets.all(0.5),
                              decoration: BoxDecoration(
                                color: cellColor(count),
                                borderRadius: BorderRadius.circular(3),
                                border: isPeak
                                    ? Border.all(
                                        color: AppColors.primary,
                                        width: 1.2,
                                      )
                                    : null,
                              ),
                              child: Center(
                                child: count > 0
                                    ? Text(
                                        count.toString(),
                                        style: TextStyle(
                                          fontSize: 6,
                                          color: count > maxIntensity * 0.6
                                              ? Colors.white
                                              : textClr,
                                          fontWeight: FontWeight.w600,
                                        ),
                                      )
                                    : null,
                              ),
                            );
                          }),
                        ],
                      ),
                    );
                  }),
                ],
              ),
            ),
            const SizedBox(height: 10),
            _buildHeatmapLegend(isDark, trackClr),
            if (peak != null) ...[
              const SizedBox(height: 10),
              Text(
                'Peak: ${peak.dayName} ${peak.hourDisplay} · ${peak.count} completions · ${peak.onTimeRate.toStringAsFixed(1)}% on time',
                style: AppTextStyles.body.copyWith(fontSize: 11, color: subClr),
              ),
            ],
            // Remove bestSlots and unreliableDays – they are now in behavioral
          ],
        ),
      ),
    );
  }

  Widget _buildHeatmapLegend(bool isDark, Color trackClr) {
    final subClr = isDark ? Colors.white54 : Colors.black38;
    return Row(
      children: [
        Text('Less', style: TextStyle(fontSize: 9, color: subClr)),
        const SizedBox(width: 6),
        ...List.generate(5, (i) {
          final t = i / 4;
          return Container(
            width: 12,
            height: 8,
            margin: const EdgeInsets.symmetric(horizontal: 1.5),
            decoration: BoxDecoration(
              color: i == 0
                  ? trackClr
                  : Color.lerp(
                      AppColors.primary.withOpacity(0.18),
                      AppColors.primary,
                      t,
                    ),
              borderRadius: BorderRadius.circular(2),
            ),
          );
        }),
        const SizedBox(width: 6),
        Text('More', style: TextStyle(fontSize: 9, color: subClr)),
      ],
    );
  }

  // ─── WORK PATTERNS ────────────────────────────────────────────────────
  Widget _buildWorkPatterns(AnalyticsDashboard dashboard, bool isDark) {
    final patterns = dashboard.workPatterns;
    final subClr = isDark ? Colors.white70 : Colors.black54;

    final totalCount = patterns.timeOfDay.fold<int>(0, (s, b) => s + b.count);

    if (totalCount == 0) {
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14),
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: _cardDecoration(isDark),
          child: Center(
            child: Text(
              'No completion data yet.',
              style: AppTextStyles.body.copyWith(color: subClr),
            ),
          ),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: _cardDecoration(isDark),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _sectionTitle('When & How You Work', isDark),
            const SizedBox(height: 14),

            // ─── Time of day ──────────────────────────────────────────────
            Text(
              'Time of day',
              style: AppTextStyles.body.copyWith(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: subClr,
              ),
            ),
            const SizedBox(height: 8),
            ...patterns.timeOfDay.map((bucket) {
              final color = _bucketColor(bucket.key);
              return Padding(
                padding: const EdgeInsets.only(bottom: 7),
                child: Row(
                  children: [
                    Container(
                      width: 7,
                      height: 7,
                      decoration: BoxDecoration(
                        color: color,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 7),
                    SizedBox(
                      width: 62,
                      child: Text(
                        bucket.label,
                        style: TextStyle(fontSize: 11, color: color),
                      ),
                    ),
                    Expanded(
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: (bucket.count / totalCount).clamp(0.0, 1.0),
                          minHeight: 6,
                          backgroundColor: isDark
                              ? Colors.white10
                              : Colors.grey.shade200,
                          valueColor: AlwaysStoppedAnimation<Color>(color),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      '${bucket.count} (${bucket.percent.toStringAsFixed(0)}%)',
                      style: TextStyle(fontSize: 10, color: subClr),
                    ),
                  ],
                ),
              );
            }),
            const SizedBox(height: 12),

            // ─── Priority performance ─────────────────────────────────────
            Text(
              'By priority',
              style: AppTextStyles.body.copyWith(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: subClr,
              ),
            ),
            const SizedBox(height: 8),
            ...patterns.byPriority.map((row) {
              final color = _priorityColor(row.priority);
              return Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  children: [
                    Container(
                      width: 7,
                      height: 7,
                      decoration: BoxDecoration(
                        color: color,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 7),
                    SizedBox(
                      width: 46,
                      child: Text(
                        row.label,
                        style: TextStyle(fontSize: 11, color: color),
                      ),
                    ),
                    Expanded(
                      child: row.completed > 0
                          ? ClipRRect(
                              borderRadius: BorderRadius.circular(4),
                              child: LinearProgressIndicator(
                                value: (row.onTimeRate / 100).clamp(0.0, 1.0),
                                minHeight: 6,
                                backgroundColor: isDark
                                    ? Colors.white10
                                    : Colors.grey.shade200,
                                valueColor: AlwaysStoppedAnimation<Color>(
                                  color,
                                ),
                              ),
                            )
                          : Container(),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      row.completed > 0
                          ? '${row.onTimeRate.toStringAsFixed(0)}% · ${row.completed}'
                          : '—',
                      style: TextStyle(fontSize: 10, color: subClr),
                    ),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }

  Color _bucketColor(String key) {
    switch (key) {
      case 'morning':
        return AppColors.primary;
      case 'afternoon':
        return const Color(0xFF3B82F6);
      case 'evening':
        return const Color(0xFF8B5CF6);
      default:
        return const Color(0xFF6366F1);
    }
  }

  Color _priorityColor(String priority) {
    switch (priority) {
      case 'high':
        return const Color(0xFFEF4444);
      case 'medium':
        return AppColors.primary;
      default:
        return const Color(0xFF22C55E);
    }
  }

  // ─── BEHAVIORAL SECTION ────────────────────────────────────────────────
  Widget _buildBehavioral(AnalyticsDashboard dashboard, bool isDark) {
    final behavioral = dashboard.behavioral;
    final textClr = isDark ? Colors.white : const Color(0xFF1C1C1E);
    final subClr = isDark ? Colors.white70 : Colors.black54;

    // If no top days, show empty state
    if (behavioral.topDays.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14),
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: _cardDecoration(isDark),
          child: Center(
            child: Text(
              'Not enough data yet. Complete more tasks to see your productive patterns.',
              style: AppTextStyles.body.copyWith(fontSize: 13, color: subClr),
              textAlign: TextAlign.center,
            ),
          ),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: _cardDecoration(isDark),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                _sectionTitle(
                  'Behavioral Insights',
                  isDark,
                  icon: Icons.insights_rounded,
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 2,
                  ),
                  decoration: BoxDecoration(
                    color: isDark ? Colors.white12 : Colors.grey.shade200,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    behavioral.source.toUpperCase(),
                    style: TextStyle(
                      fontSize: 8,
                      fontWeight: FontWeight.w600,
                      color: behavioral.source == 'ai'
                          ? AppColors.primary
                          : subClr,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // ─── Top Days (with hours) ─────────────────────────────────────
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              physics: const BouncingScrollPhysics(),
              child: Row(
                children: behavioral.topDays.map((day) {
                  return Container(
                    width: 170,
                    margin: const EdgeInsets.only(right: 10),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: isDark ? Colors.white10 : Colors.grey.shade50,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                        color: isDark ? Colors.white12 : Colors.grey.shade200,
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Text(
                              day.day,
                              style: TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.w700,
                                color: textClr,
                              ),
                            ),
                            const Spacer(),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 6,
                                vertical: 2,
                              ),
                              decoration: BoxDecoration(
                                color: AppColors.primary.withOpacity(0.12),
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: Text(
                                '${day.score.toStringAsFixed(2)}',
                                style: TextStyle(
                                  fontSize: 10,
                                  fontWeight: FontWeight.w600,
                                  color: AppColors.primary,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            Icon(Icons.timer_rounded, size: 12, color: subClr),
                            const SizedBox(width: 4),
                            Text(
                              '${day.logCount} tasks · ${day.onTimeRate.toStringAsFixed(0)}% on time',
                              style: TextStyle(fontSize: 10, color: subClr),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        // ─── Hours ──────────────────────────────────────────
                        ...day.hours.map((hour) {
                          return Container(
                            margin: const EdgeInsets.only(bottom: 4),
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: isDark ? Colors.white12 : Colors.white,
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(
                                color: isDark
                                    ? Colors.white12
                                    : Colors.grey.shade200,
                                width: 0.5,
                              ),
                            ),
                            child: Row(
                              children: [
                                Icon(
                                  Icons.access_time_rounded,
                                  size: 12,
                                  color: AppColors.primary,
                                ),
                                const SizedBox(width: 6),
                                Expanded(
                                  child: Text(
                                    hour.hourDisplay,
                                    style: TextStyle(
                                      fontSize: 11,
                                      fontWeight: FontWeight.w600,
                                      color: textClr,
                                    ),
                                  ),
                                ),
                                Text(
                                  '${hour.onTimeRate.toStringAsFixed(0)}% · ${hour.logCount}',
                                  style: TextStyle(fontSize: 9, color: subClr),
                                ),
                              ],
                            ),
                          );
                        }),
                      ],
                    ),
                  );
                }).toList(),
              ),
            ),
            const SizedBox(height: 14),

            // ─── Stats row ──────────────────────────────────────────────────
            Row(
              children: [
                _behaviorStat(
                  Icons.timer_rounded,
                  '${behavioral.focus.avgMinutes.toStringAsFixed(0)} min',
                  'Avg focus',
                  isDark,
                ),
                const SizedBox(width: 12),
                _behaviorStat(
                  behavioral.momentum.direction == 'up'
                      ? Icons.trending_up_rounded
                      : behavioral.momentum.direction == 'down'
                      ? Icons.trending_down_rounded
                      : Icons.remove_rounded,
                  behavioral.momentum.label,
                  'Momentum',
                  isDark,
                  color: behavioral.momentum.direction == 'up'
                      ? const Color(0xFF22C55E)
                      : behavioral.momentum.direction == 'down'
                      ? const Color(0xFFEF4444)
                      : Colors.orange,
                ),
              ],
            ),
            const SizedBox(height: 8),
            // ─── Procrastination rates ────────────────────────────────────
            Row(
              children: [
                _procrastinationChip(
                  'Late night: ${behavioral.procrastination.lateNightRate.toStringAsFixed(0)}%',
                  behavioral.procrastination.lateNightRate,
                  isDark,
                ),
                const SizedBox(width: 8),
                _procrastinationChip(
                  'Rescheduled: ${behavioral.procrastination.rescheduleRate.toStringAsFixed(0)}%',
                  behavioral.procrastination.rescheduleRate,
                  isDark,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _behaviorStat(
    IconData icon,
    String label,
    String hint,
    bool isDark, {
    Color? color,
  }) {
    final textClr = isDark ? Colors.white : const Color(0xFF1C1C1E);
    final subClr = isDark ? Colors.white70 : Colors.black54;
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 10),
        decoration: BoxDecoration(
          color: isDark ? Colors.white10 : Colors.grey.shade50,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(
          children: [
            Icon(icon, size: 16, color: color ?? AppColors.primary),
            const SizedBox(width: 6),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: color ?? textClr,
                    ),
                  ),
                  Text(hint, style: TextStyle(fontSize: 9, color: subClr)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _procrastinationChip(String label, double rate, bool isDark) {
    final color = rate > 40
        ? const Color(0xFFEF4444)
        : rate > 20
        ? Colors.orange
        : const Color(0xFF22C55E);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(isDark ? 0.18 : 0.08),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 10,
          fontWeight: FontWeight.w600,
          color: color,
        ),
      ),
    );
  }

  // ─── NEEDS ATTENTION ─────────────────────────────────────────────────
  Widget _buildNeedsAttention(AnalyticsDashboard dashboard, bool isDark) {
    final attention = dashboard.needsAttention;
    final textClr = isDark ? Colors.white : const Color(0xFF1C1C1E);
    final subClr = isDark ? Colors.white70 : Colors.black54;

    final hasItems =
        attention.overdue > 0 ||
        attention.dueNext7d > 0 ||
        attention.dueSoon.isNotEmpty;

    if (!hasItems) {
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14),
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: _cardDecoration(
            isDark,
            accentBorder: const Color(0xFF22C55E).withOpacity(0.25),
          ),
          child: Row(
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  color: const Color(0xFF22C55E).withOpacity(0.14),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(
                  Icons.check_circle_rounded,
                  color: Color(0xFF22C55E),
                  size: 18,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  'All clear! No tasks need immediate attention.',
                  style: AppTextStyles.body.copyWith(
                    fontSize: 13,
                    color: subClr,
                  ),
                ),
              ),
            ],
          ),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: _cardDecoration(
          isDark,
          accentBorder: Colors.orange.withOpacity(0.2),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                _sectionTitle(
                  'Needs Attention',
                  isDark,
                  icon: Icons.warning_amber_rounded,
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 3,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.orange.withOpacity(isDark ? 0.18 : 0.1),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    '${attention.overdue + attention.dueNext7d} pending',
                    style: const TextStyle(
                      fontSize: 10,
                      color: Colors.orange,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // Counts
            Row(
              children: [
                _attentionCount(
                  '${attention.overdue}',
                  'Overdue',
                  const Color(0xFFEF4444),
                  isDark,
                ),
                const SizedBox(width: 8),
                _attentionCount(
                  '${attention.dueNext7d}',
                  'Due next 7d',
                  Colors.orange,
                  isDark,
                ),
                const SizedBox(width: 8),
                _attentionCount(
                  '${attention.dueSoon.length}',
                  'Due soon (48h)',
                  AppColors.primary,
                  isDark,
                ),
              ],
            ),
            const SizedBox(height: 14),

            // Priority breakdown
            Text(
              'Pending by priority',
              style: AppTextStyles.body.copyWith(fontSize: 10, color: subClr),
            ),
            const SizedBox(height: 6),
            ClipRRect(
              borderRadius: BorderRadius.circular(3),
              child: Row(
                children: [
                  Expanded(
                    flex: math.max(attention.pendingByPriority.high, 0) + 1,
                    child: Container(height: 6, color: const Color(0xFFEF4444)),
                  ),
                  Expanded(
                    flex: math.max(attention.pendingByPriority.medium, 0) + 1,
                    child: Container(height: 6, color: Colors.orange),
                  ),
                  Expanded(
                    flex: math.max(attention.pendingByPriority.low, 0) + 1,
                    child: Container(height: 6, color: const Color(0xFF22C55E)),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                Expanded(
                  child: Text(
                    'H ${attention.pendingByPriority.high}',
                    style: const TextStyle(
                      fontSize: 9,
                      color: Color(0xFFEF4444),
                    ),
                  ),
                ),
                Expanded(
                  child: Text(
                    'M ${attention.pendingByPriority.medium}',
                    style: const TextStyle(fontSize: 9, color: Colors.orange),
                  ),
                ),
                Expanded(
                  child: Text(
                    'L ${attention.pendingByPriority.low}',
                    style: const TextStyle(
                      fontSize: 9,
                      color: Color(0xFF22C55E),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // Due soon list
            if (attention.dueSoon.isNotEmpty) ...[
              Text(
                'Due within 48h',
                style: AppTextStyles.body.copyWith(fontSize: 10, color: subClr),
              ),
              const SizedBox(height: 6),
              ...attention.dueSoon.take(3).map((task) {
                final dueTime = DateTime.parse(task.dueDatetime).toLocal();
                final pColor = task.priority == 'high'
                    ? const Color(0xFFEF4444)
                    : task.priority == 'medium'
                    ? Colors.orange
                    : const Color(0xFF22C55E);
                return Container(
                  padding: const EdgeInsets.symmetric(vertical: 7),
                  decoration: BoxDecoration(
                    border: Border(
                      bottom: BorderSide(
                        color: isDark ? Colors.white10 : Colors.grey.shade200,
                        width: 0.5,
                      ),
                    ),
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 6,
                        height: 6,
                        decoration: BoxDecoration(
                          color: pColor,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          task.title,
                          style: AppTextStyles.body.copyWith(
                            fontSize: 12,
                            color: textClr,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      Text(
                        DateFormat('d MMM · h:mma').format(dueTime),
                        style: AppTextStyles.body.copyWith(
                          fontSize: 10,
                          color: subClr,
                        ),
                      ),
                    ],
                  ),
                );
              }),
            ],
            if (attention.dueSoon.length > 3)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(
                  '+ ${attention.dueSoon.length - 3} more',
                  style: TextStyle(
                    fontSize: 10,
                    color: AppColors.primary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _attentionCount(String value, String label, Color color, bool isDark) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 8),
        decoration: BoxDecoration(
          color: color.withOpacity(isDark ? 0.14 : 0.07),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Column(
          children: [
            Text(
              value,
              style: TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w700,
                color: color,
              ),
            ),
            Text(
              label,
              style: TextStyle(
                fontSize: 8,
                fontWeight: FontWeight.w600,
                color: color,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Stat Card ──────────────────────────────────────────────────────────
class _StatCard extends StatelessWidget {
  final String value;
  final String label;
  final double? change;
  final IconData icon;
  final Color color;
  final bool isDark;

  const _StatCard({
    required this.value,
    required this.label,
    this.change,
    required this.icon,
    required this.color,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    final cardBg = isDark ? const Color(0xFF1C1C1E) : Colors.white;
    final borderClr = isDark ? const Color(0xFF2C2C2E) : Colors.grey.shade200;
    final textClr = isDark ? Colors.white : const Color(0xFF1C1C1E);
    final subClr = isDark ? Colors.white60 : Colors.black45;

    return SizedBox(
      width: 122,
      child: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: cardBg,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: borderClr),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(isDark ? 0.06 : 0.04),
              blurRadius: 6,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Row(
              children: [
                Container(
                  width: 22,
                  height: 22,
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.14),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(icon, size: 12, color: color),
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    label,
                    style: TextStyle(fontSize: 9, color: subClr),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                FittedBox(
                  fit: BoxFit.scaleDown,
                  child: Text(
                    value,
                    style: AppTextStyles.headline.copyWith(
                      fontSize: 22,
                      fontWeight: FontWeight.w700,
                      color: textClr,
                    ),
                  ),
                ),
                const Spacer(),
                if (change != null)
                  Text(
                    change! >= 0
                        ? '↑${change!.toStringAsFixed(0)}%'
                        : '↓${change!.abs().toStringAsFixed(0)}%',
                    style: TextStyle(
                      fontSize: 9,
                      color: change! >= 0
                          ? const Color(0xFF22C55E)
                          : const Color(0xFFEF4444),
                      fontWeight: FontWeight.w600,
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Insight Card ──────────────────────────────────────────────────────
class _InsightCard extends StatelessWidget {
  final Insight insight;
  final bool isDark;

  const _InsightCard({required this.insight, required this.isDark});

  Color get _accent {
    switch (insight.type) {
      case 'positive':
        return const Color(0xFF22C55E);
      case 'warning':
        return const Color(0xFFEF4444);
      case 'tip':
        return AppColors.primary;
      default:
        return const Color(0xFF3B82F6);
    }
  }

  @override
  Widget build(BuildContext context) {
    final cardBg = isDark ? const Color(0xFF1C1C1E) : Colors.white;
    final textClr = isDark ? Colors.white : const Color(0xFF1C1C1E);
    final subClr = isDark ? Colors.white70 : Colors.black54;

    return Container(
      width: 236,
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isDark ? const Color(0xFF2C2C2E) : Colors.grey.shade200,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(isDark ? 0.10 : 0.04),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            width: 4,
            decoration: BoxDecoration(
              color: _accent,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(14),
                bottomLeft: Radius.circular(14),
              ),
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 26,
                        height: 26,
                        decoration: BoxDecoration(
                          color: _accent.withOpacity(0.14),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Icon(insight.iconData, size: 15, color: _accent),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          insight.title,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 12.5,
                            fontWeight: FontWeight.w700,
                            color: textClr,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Expanded(
                    child: Text(
                      insight.message,
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                      style: AppTextStyles.body.copyWith(
                        fontSize: 11.5,
                        height: 1.3,
                        color: subClr,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Score Gauge (unchanged — no glow) ────────────────────────────────
class _ScoreGauge extends StatelessWidget {
  final int score;
  final String rating;
  final bool isDark;

  const _ScoreGauge({
    required this.score,
    required this.rating,
    required this.isDark,
  });

  Color get _color {
    if (score >= 85) return const Color(0xFF22C55E);
    if (score >= 70) return AppColors.primary;
    if (score >= 55) return const Color(0xFF3B82F6);
    if (score >= 40) return const Color(0xFFF59E0B);
    return const Color(0xFFEF4444);
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 100,
      height: 100,
      child: CustomPaint(
        painter: _GaugePainter(
          progress: (score / 100).clamp(0.0, 1.0),
          color: _color,
          trackColor: isDark ? Colors.white12 : Colors.grey.shade200,
        ),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                '$score',
                style: AppTextStyles.headline.copyWith(
                  fontSize: 28,
                  fontWeight: FontWeight.w700,
                  color: isDark ? Colors.white : const Color(0xFF1C1C1E),
                ),
              ),
              Text(
                rating,
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  color: _color,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _GaugePainter extends CustomPainter {
  final double progress;
  final Color color;
  final Color trackColor;

  _GaugePainter({
    required this.progress,
    required this.color,
    required this.trackColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    const stroke = 10.0;
    final rect = Rect.fromLTWH(
      stroke / 2,
      stroke / 2,
      size.width - stroke,
      size.height - stroke,
    );
    const start = math.pi * 0.75;
    const sweep = math.pi * 1.5;

    final track = Paint()
      ..color = trackColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawArc(rect, start, sweep, false, track);

    if (progress > 0) {
      final prog = Paint()
        ..shader = SweepGradient(
          startAngle: start,
          endAngle: start + sweep,
          colors: [color.withOpacity(0.55), color],
        ).createShader(rect)
        ..style = PaintingStyle.stroke
        ..strokeWidth = stroke
        ..strokeCap = StrokeCap.round;
      canvas.drawArc(rect, start, sweep * progress, false, prog);
    }
  }

  @override
  bool shouldRepaint(_GaugePainter oldDelegate) =>
      oldDelegate.progress != progress || oldDelegate.color != color;
}

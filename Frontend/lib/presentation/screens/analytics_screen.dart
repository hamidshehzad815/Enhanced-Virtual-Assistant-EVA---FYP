import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:lottie/lottie.dart';
import 'package:go_router/go_router.dart';
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
            ? Center(
                child: Text(
                  'Error: ${vm.error}',
                  style: AppTextStyles.body.copyWith(fontSize: 15),
                ),
              )
            : dashboard == null
            ? const Center(child: Text('No data available'))
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
                        _buildHeader(vm, isDark, dashboard),
                        const SizedBox(height: 10),
                        _buildHeroSection(dashboard, isDark),
                        const SizedBox(height: 14),
                        _buildBehavioralSection(dashboard, isDark),
                        const SizedBox(height: 14),
                        _buildChartsSection(dashboard, isDark),
                        const SizedBox(height: 14),
                        _buildTaskSummary(dashboard, isDark),
                        const SizedBox(height: 20),
                      ],
                    ),
                  ),
                ),
              ),
      ),
    );
  }

  // ─── HEADER ────────────────────────────────────────────────────────────
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
                    'Generated ${DateFormat('d MMM y, HH:mm').format(generatedDate)} · ${dashboard.timezone}',
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

  // ─── HERO SECTION ──────────────────────────────────────────────────────
  Widget _buildHeroSection(AnalyticsDashboard dashboard, bool isDark) {
    final hero = dashboard.hero;

    final cards = [
      _HeroCard(
        icon: Icons.check_circle_rounded,
        iconColor: AppColors.primary,
        value: '${hero.completedThisWeek}',
        label: 'This week',
        change: _getChangeText(hero.weekChangePercent),
        isDark: isDark,
      ),
      _HeroCard(
        icon: Icons.trending_up_rounded,
        iconColor: Colors.green,
        value: '${hero.completedLastWeek}',
        label: 'Last week',
        sub: 'completions',
        isDark: isDark,
      ),
      _HeroCard(
        icon: Icons.timer_rounded,
        iconColor: AppColors.primary,
        value: '${hero.onTimeRate.toStringAsFixed(1)}%',
        label: 'On-time rate',
        sub: 'all time',
        isDark: isDark,
      ),
      _HeroCard(
        icon: Icons.local_fire_department_rounded,
        iconColor: const Color(0xFFBA7517),
        value: '${hero.streakDays}',
        label: 'Day streak',
        sub: 'keep going',
        isDark: isDark,
      ),
      _HeroCard(
        icon: Icons.list_alt_rounded,
        iconColor: Colors.green,
        value: '${hero.totalCompleted}',
        label: 'Total done',
        sub: 'all time',
        isDark: isDark,
      ),
      _HeroCard(
        icon: Icons.calendar_today_rounded,
        iconColor: Colors.orange,
        value: '${hero.upcoming7d}',
        label: 'Due in 7d',
        sub: 'upcoming',
        isDark: isDark,
      ),
    ];

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14),
      child: GridView.count(
        crossAxisCount: 3,
        crossAxisSpacing: 8,
        mainAxisSpacing: 8,
        childAspectRatio: 1.1,
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        children: cards,
      ),
    );
  }

  String _getChangeText(double percent) {
    if (percent == 0) return '';
    final sign = percent > 0 ? '↑' : '↓';
    return '$sign ${percent.abs().toStringAsFixed(1)}%';
  }

  // ─── BEHAVIORAL SECTION ──────────────────────────────────────────────
  Widget _buildBehavioralSection(AnalyticsDashboard dashboard, bool isDark) {
    final behavioral = dashboard.behavioral;
    final bestSlots = dashboard.bestSlots;
    final int remainingTasks =
        (behavioral.thresholds.global) - (behavioral.totalCompleted);

    final cardBg = isDark ? const Color(0xFF1C1C1E) : Colors.white;
    final borderClr = isDark ? const Color(0xFF2C2C2E) : Colors.grey.shade200;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: cardBg,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: borderClr),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(isDark ? 0.10 : 0.04),
              blurRadius: 10,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Behavioral Insights',
              style: AppTextStyles.subtitleMedium.copyWith(
                fontSize: 13,
                fontWeight: FontWeight.w700,
                color: isDark ? Colors.white70 : Colors.black54,
                letterSpacing: 0.5,
              ),
            ),
            const SizedBox(height: 8),

            // ─── Behavioral disabled 
            if (!behavioral.enabled) ...[
              Center(
                child: Column(
                  children: [
                    Lottie.asset(
                      'assets/lottie/insights.json',
                      width: 120,
                      height: 120,
                      fit: BoxFit.contain,
                    ),
                    const SizedBox(height: 10),
                    Text(
                      'Enable behavioral analytics to unlock insights',
                      style: AppTextStyles.body.copyWith(
                        fontSize: 14,
                        color: isDark ? Colors.white70 : Colors.black54,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 10),
                    ElevatedButton.icon(
                      onPressed: () => context.push('/settings'),
                      icon: const Icon(Icons.settings_rounded, size: 16),
                      label: const Text('Enable Insights'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.primary,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(
                          horizontal: 20,
                          vertical: 10,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],

            // ─── Not enough data
            if (behavioral.enabled && !behavioral.hasEnoughData) ...[
              Center(
                child: Column(
                  children: [
                    Lottie.asset(
                      'assets/lottie/insights.json',
                      width: 120,
                      height: 120,
                      fit: BoxFit.contain,
                    ),
                    const SizedBox(height: 10),
                    if (remainingTasks > 0)
                      Text(
                        'Complete $remainingTasks more tasks to unlock personalized insights.',
                        style: AppTextStyles.body.copyWith(
                          fontSize: 14,
                          color: isDark ? Colors.white70 : Colors.black54,
                        ),
                        textAlign: TextAlign.center,
                      )
                    else
                      Text(
                        '🎉 Insights unlocked! Keep completing tasks to get more personalized recommendations.',
                        style: AppTextStyles.body.copyWith(
                          fontSize: 14,
                          color: isDark ? Colors.white70 : Colors.black54,
                        ),
                        textAlign: TextAlign.center,
                      ),
                  ],
                ),
              ),
            ],

            // ─── Full data ──────────────────────────────────────────────
            if (behavioral.enabled && behavioral.hasEnoughData) ...[
              if (behavioral.strengthSummary != null)
                _AnimatedStatement(
                  text: behavioral.strengthSummary!,
                  isDark: isDark,
                ),

              const SizedBox(height: 12),

              if (behavioral.topDays.isNotEmpty) ...[
                Text(
                  'Top days',
                  style: AppTextStyles.body.copyWith(
                    fontSize: 11,
                    color: isDark ? Colors.white70 : Colors.black54,
                  ),
                ),
                const SizedBox(height: 6),
                Row(
                  children: behavioral.topDays.map((day) {
                    return Expanded(
                      child: Container(
                        margin: const EdgeInsets.only(right: 6),
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: isDark ? Colors.white10 : Colors.grey.shade50,
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              day.day,
                              style: AppTextStyles.body.copyWith(
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                                color: isDark ? Colors.white : Colors.black87,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              'Score ${day.score.toStringAsFixed(2)} · ${day.logCount} tasks',
                              style: AppTextStyles.body.copyWith(
                                fontSize: 10,
                                color: isDark ? Colors.white70 : Colors.black54,
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 12),
              ],

              if (bestSlots.isNotEmpty) ...[
                Text(
                  'Best scheduling slot',
                  style: AppTextStyles.body.copyWith(
                    fontSize: 11,
                    color: isDark ? Colors.white70 : Colors.black54,
                  ),
                ),
                const SizedBox(height: 6),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: isDark ? Colors.white10 : Colors.grey.shade50,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 32,
                        height: 32,
                        decoration: BoxDecoration(
                          color: AppColors.primary.withOpacity(0.12),
                          borderRadius: BorderRadius.circular(50),
                        ),
                        child: Icon(
                          Icons.stars_rounded,
                          color: AppColors.primary,
                          size: 16,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              bestSlots.first.suggestion,
                              style: AppTextStyles.body.copyWith(
                                fontSize: 13,
                                fontWeight: FontWeight.w500,
                                color: isDark ? Colors.white : Colors.black87,
                              ),
                              overflow: TextOverflow.ellipsis,
                              maxLines: 2,
                            ),
                            Text(
                              '${bestSlots.first.logCount} tasks · ${(bestSlots.first.onTimeRate * 100).toStringAsFixed(0)}% on time',
                              style: AppTextStyles.body.copyWith(
                                fontSize: 11,
                                color: isDark ? Colors.white70 : Colors.black54,
                              ),
                            ),
                          ],
                        ),
                      ),
                      Text(
                        bestSlots.first.score.toStringAsFixed(2),
                        style: AppTextStyles.body.copyWith(
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                          color: AppColors.primary,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ],
        ),
      ),
    );
  }

  // ─── CHARTS SECTION ──────────────────────────────────────────────────
  Widget _buildChartsSection(AnalyticsDashboard dashboard, bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14),
      child: Column(
        children: [
          _buildHeatmapCard(dashboard, isDark),
          const SizedBox(height: 14),
          _buildTrendCard(dashboard, isDark),
        ],
      ),
    );
  }

  // ─── HEATMAP ──────────────────────────────────────────────────────────
  Widget _buildHeatmapCard(AnalyticsDashboard dashboard, bool isDark) {
    final cardBg = isDark ? const Color(0xFF1C1C1E) : Colors.white;
    final borderClr = isDark ? const Color(0xFF2C2C2E) : Colors.grey.shade200;
    final textClr = isDark ? Colors.white : const Color(0xFF1C1C1E);
    final subClr = isDark ? Colors.white70 : Colors.black54;

    final heatmap = dashboard.heatmap;
    final maxIntensity = heatmap.cells.isNotEmpty
        ? heatmap.cells.map((c) => c.intensity).reduce((a, b) => a > b ? a : b)
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

    final primaryColor = isDark
        ? Colors.blue.shade400
        : const Color(0xFFD4E8F7);
    final primaryDark = isDark ? Colors.blue.shade600 : Colors.blue.shade300;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: borderClr),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(isDark ? 0.10 : 0.04),
            blurRadius: 10,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Heatmap',
            style: AppTextStyles.subtitleMedium.copyWith(
              fontSize: 13,
              fontWeight: FontWeight.w700,
              color: subClr,
              letterSpacing: 0.5,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            '${heatmap.rangeDays} days · ${heatmap.hourRange.startDisplay}–${heatmap.hourRange.endDisplay}',
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
                ...List.generate(7, (dayIndex) {
                  return Row(
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
                        final color = count > 0
                            ? Color.lerp(
                                isDark
                                    ? Colors.white.withOpacity(0.05)
                                    : primaryColor,
                                isDark ? Colors.blue.shade400 : primaryDark,
                                (count / maxIntensity).clamp(0, 1),
                              )!
                            : Colors.transparent;

                        return Container(
                          width: 18,
                          height: 14,
                          margin: const EdgeInsets.all(0.5),
                          decoration: BoxDecoration(
                            color: color,
                            borderRadius: BorderRadius.circular(2),
                            border: count > 0
                                ? Border.all(
                                    color: isDark
                                        ? Colors.blue.withOpacity(0.3)
                                        : Colors.blue.withOpacity(0.1),
                                    width: 0.5,
                                  )
                                : null,
                          ),
                          child: Center(
                            child: count > 0
                                ? Text(
                                    count.toString(),
                                    style: TextStyle(
                                      fontSize: 6,
                                      color: count > maxIntensity * 0.7
                                          ? Colors.white
                                          : textClr,
                                      fontWeight: FontWeight.w500,
                                    ),
                                  )
                                : null,
                          ),
                        );
                      }),
                    ],
                  );
                }),
              ],
            ),
          ),
          const SizedBox(height: 8),
          if (heatmap.peak != null)
            Text(
              'Peak: ${heatmap.peak!.dayName} ${heatmap.peak!.hourDisplay} · ${heatmap.peak!.count} completions · ${heatmap.peak!.onTimeRate.toStringAsFixed(1)}% on time',
              style: AppTextStyles.body.copyWith(fontSize: 11, color: subClr),
            ),
        ],
      ),
    );
  }

  // ─── TREND CHART ──────────────────────────────────────────────────────
  Widget _buildTrendCard(AnalyticsDashboard dashboard, bool isDark) {
    final cardBg = isDark ? const Color(0xFF1C1C1E) : Colors.white;
    final borderClr = isDark ? const Color(0xFF2C2C2E) : Colors.grey.shade200;
    final subClr = isDark ? Colors.white70 : Colors.black54;

    final trend = dashboard.completionTrend;

    if (trend.trend.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: cardBg,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: borderClr),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Completion Trend',
              style: AppTextStyles.subtitleMedium.copyWith(
                fontSize: 13,
                fontWeight: FontWeight.w700,
                color: subClr,
                letterSpacing: 0.5,
              ),
            ),
            const SizedBox(height: 8),
            Center(
              child: Text(
                'No data available',
                style: AppTextStyles.body.copyWith(color: subClr, fontSize: 13),
              ),
            ),
          ],
        ),
      );
    }

    final sortedTrend = List.from(trend.trend)
      ..sort((a, b) => a.week.compareTo(b.week));
    final labels = sortedTrend.map((t) => 'Wk ${t.week}').toList();
    final onTimeData = sortedTrend.map((t) => t.onTime.toDouble()).toList();
    final lateData = sortedTrend.map((t) => t.late.toDouble()).toList();

    final onTimeColor = isDark ? Colors.blue.shade400 : const Color(0xFFA8C8F5);
    final lateColor = isDark ? Colors.red.shade400 : const Color(0xFFF5A8A8);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: borderClr),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(isDark ? 0.10 : 0.04),
            blurRadius: 10,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Completion Trend',
                style: AppTextStyles.subtitleMedium.copyWith(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: subClr,
                  letterSpacing: 0.5,
                ),
              ),
              Row(
                children: [
                  _buildLegendItem('On time', onTimeColor),
                  const SizedBox(width: 10),
                  _buildLegendItem('Late', lateColor),
                ],
              ),
            ],
          ),
          const SizedBox(height: 8),
          SizedBox(
            height: 120,
            child: BarChart(
              BarChartData(
                alignment: BarChartAlignment.spaceAround,
                maxY:
                    (onTimeData + lateData).reduce((a, b) => a > b ? a : b) + 2,
                barTouchData: BarTouchData(enabled: true),
                titlesData: FlTitlesData(
                  show: true,
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      getTitlesWidget: (value, meta) {
                        final index = value.toInt();
                        if (index < 0 || index >= labels.length)
                          return const SizedBox.shrink();
                        return Text(
                          labels[index],
                          style: TextStyle(fontSize: 10, color: subClr),
                        );
                      },
                    ),
                  ),
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 24,
                      getTitlesWidget: (value, meta) {
                        return Text(
                          value.toInt().toString(),
                          style: TextStyle(fontSize: 9, color: subClr),
                        );
                      },
                    ),
                  ),
                  topTitles: AxisTitles(
                    sideTitles: SideTitles(showTitles: false),
                  ),
                  rightTitles: AxisTitles(
                    sideTitles: SideTitles(showTitles: false),
                  ),
                ),
                borderData: FlBorderData(show: false),
                gridData: FlGridData(
                  show: true,
                  drawVerticalLine: false,
                  horizontalInterval: 5,
                  getDrawingHorizontalLine: (value) {
                    return FlLine(
                      color: isDark ? Colors.white12 : Colors.grey.shade200,
                    );
                  },
                ),
                barGroups: List.generate(sortedTrend.length, (i) {
                  return BarChartGroupData(
                    x: i,
                    barRods: [
                      BarChartRodData(
                        toY: onTimeData[i],
                        color: onTimeColor,
                        width: 14,
                        borderRadius: BorderRadius.circular(3),
                      ),
                      BarChartRodData(
                        toY: lateData[i],
                        color: lateColor,
                        width: 14,
                        borderRadius: BorderRadius.circular(3),
                        fromY: onTimeData[i],
                      ),
                    ],
                  );
                }),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLegendItem(String label, Color color) {
    return Row(
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 4),
        Text(label, style: TextStyle(fontSize: 10, color: Colors.grey)),
      ],
    );
  }

  // ─── TASK SUMMARY ─────────────────────────────────────────────────────
  Widget _buildTaskSummary(AnalyticsDashboard dashboard, bool isDark) {
    final tasks = dashboard.tasks;
    final cardBg = isDark ? const Color(0xFF1C1C1E) : Colors.white;
    final borderClr = isDark ? const Color(0xFF2C2C2E) : Colors.grey.shade200;
    final textClr = isDark ? Colors.white : const Color(0xFF1C1C1E);
    final subClr = isDark ? Colors.white70 : Colors.black54;

    final highColor = isDark ? Colors.red.shade400 : const Color(0xFFF5C8C8);
    final mediumColor = isDark
        ? Colors.orange.shade400
        : const Color(0xFFF5E0C8);
    final lowColor = isDark ? Colors.green.shade400 : const Color(0xFFC8F5C8);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: cardBg,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: borderClr),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(isDark ? 0.10 : 0.04),
              blurRadius: 10,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Task Summary',
                  style: AppTextStyles.subtitleMedium.copyWith(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: subClr,
                    letterSpacing: 0.5,
                  ),
                ),
                GestureDetector(
                  onTap: () => context.push('/calendar'),
                  child: Text(
                    'View all',
                    style: AppTextStyles.body.copyWith(
                      fontSize: 12,
                      color: AppColors.primary,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),

            // ─── Counts ──────────────────────────────────────────────────
            Row(
              children: [
                _buildTaskCount('${tasks.overdue}', 'Overdue', Colors.red),
                _buildTaskCount('${tasks.pending}', 'Pending', Colors.orange),
                _buildTaskCount('${tasks.complete}', 'Complete', Colors.green),
                _buildTaskCount(
                  '${tasks.dueWithin48h.length}',
                  'Due soon',
                  AppColors.primary,
                ),
              ],
            ),
            const SizedBox(height: 10),

            // ─── Priority bar ────────────────────────────────────────────
            Text(
              'By priority',
              style: AppTextStyles.body.copyWith(fontSize: 11, color: subClr),
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                Expanded(
                  flex: tasks.byPriority.high,
                  child: Container(
                    height: 8,
                    decoration: BoxDecoration(
                      color: highColor,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                ),
                const SizedBox(width: 2),
                Expanded(
                  flex: tasks.byPriority.medium,
                  child: Container(
                    height: 8,
                    decoration: BoxDecoration(
                      color: mediumColor,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                ),
                const SizedBox(width: 2),
                Expanded(
                  flex: tasks.byPriority.low,
                  child: Container(
                    height: 8,
                    decoration: BoxDecoration(
                      color: lowColor,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                Expanded(
                  child: Text(
                    'High ${tasks.byPriority.high}',
                    style: TextStyle(
                      fontSize: 10,
                      color: Colors.red,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
                Expanded(
                  child: Text(
                    'Medium ${tasks.byPriority.medium}',
                    style: TextStyle(
                      fontSize: 10,
                      color: Colors.orange,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
                Expanded(
                  child: Text(
                    'Low ${tasks.byPriority.low}',
                    style: TextStyle(
                      fontSize: 10,
                      color: Colors.green,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),

            // ─── Due soon ────────────────────────────────────────────────
            if (tasks.dueWithin48h.isNotEmpty) ...[
              Text(
                'Due within 48h',
                style: AppTextStyles.body.copyWith(fontSize: 11, color: subClr),
              ),
              const SizedBox(height: 6),
              ...tasks.dueWithin48h.take(3).map((task) {
                final dueTime = DateTime.parse(task.dueDatetime).toLocal();
                return Container(
                  padding: const EdgeInsets.symmetric(vertical: 6),
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
                          color: task.priority == 'high'
                              ? Colors.red
                              : task.priority == 'medium'
                              ? Colors.orange
                              : Colors.green,
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
              const SizedBox(height: 6),
            ],

            // ─── Busiest day ─────────────────────────────────────────────
            Text(
              'Busiest day: ${tasks.busiestDayThisWeek.dayName} · ${tasks.busiestDayThisWeek.taskCount} tasks',
              style: AppTextStyles.body.copyWith(fontSize: 11, color: subClr),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTaskCount(String value, String label, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 8),
        decoration: BoxDecoration(
          color: color.withOpacity(0.08),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Column(
          children: [
            Text(
              value,
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w700,
                color: color,
              ),
            ),
            Text(
              label,
              style: TextStyle(
                fontSize: 10,
                color: color,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Hero Card ──────────────────────────────────────────────────────────
class _HeroCard extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String value;
  final String label;
  final String? sub;
  final String? change;
  final bool isDark;

  const _HeroCard({
    required this.icon,
    required this.iconColor,
    required this.value,
    required this.label,
    this.sub,
    this.change,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    final cardBg = isDark ? const Color(0xFF1C1C1E) : Colors.white;
    final borderClr = isDark ? const Color(0xFF2C2C2E) : Colors.grey.shade200;
    final textClr = isDark ? Colors.white : const Color(0xFF1C1C1E);
    final subClr = isDark ? Colors.white70 : Colors.black54;

    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: borderClr),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(isDark ? 0.10 : 0.04),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 24,
            height: 24,
            decoration: BoxDecoration(
              color: iconColor.withOpacity(0.12),
              borderRadius: BorderRadius.circular(50),
            ),
            child: Icon(icon, size: 13, color: iconColor),
          ),
          const SizedBox(height: 4),
          FittedBox(
            fit: BoxFit.scaleDown,
            child: Text(
              value,
              style: AppTextStyles.headline.copyWith(
                fontSize: 17,
                fontWeight: FontWeight.w700,
                color: textClr,
              ),
            ),
          ),
          Text(
            label,
            style: AppTextStyles.body.copyWith(fontSize: 10, color: subClr),
            overflow: TextOverflow.ellipsis,
          ),
          if (sub != null)
            Text(
              sub!,
              style: AppTextStyles.body.copyWith(fontSize: 9, color: subClr),
              overflow: TextOverflow.ellipsis,
            ),
          if (change != null && change!.isNotEmpty)
            Text(
              change!,
              style: AppTextStyles.body.copyWith(
                fontSize: 9,
                color: change!.contains('↓') ? Colors.red : Colors.green,
              ),
            ),
        ],
      ),
    );
  }
}

// ─── Animated Statement ────────────────────────────────────────────────
class _AnimatedStatement extends StatefulWidget {
  final String text;
  final bool isDark;

  const _AnimatedStatement({required this.text, required this.isDark});

  @override
  State<_AnimatedStatement> createState() => _AnimatedStatementState();
}

class _AnimatedStatementState extends State<_AnimatedStatement>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 600),
      vsync: this,
    );
    _fadeAnimation = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOut,
    );
    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, 0.15),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOut));
    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return FadeTransition(
          opacity: _fadeAnimation,
          child: SlideTransition(
            position: _slideAnimation,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: AppColors.primary.withOpacity(0.08),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppColors.primary.withOpacity(0.15)),
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.lightbulb_rounded,
                    size: 16,
                    color: AppColors.primary,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      widget.text,
                      style: AppTextStyles.body.copyWith(
                        fontSize: 13,
                        fontWeight: FontWeight.w500,
                        color: widget.isDark ? Colors.white : Colors.black87,
                      ),
                      overflow: TextOverflow.visible,
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

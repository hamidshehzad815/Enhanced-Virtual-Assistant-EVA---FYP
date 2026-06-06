import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colours.dart';
import '../../core/theme/app_text_style.dart';
import '../../data/models/task_data.dart';
import '../../data/models/focus_data.dart';
import '../../data/models/schedule_item.dart';
import '../providers/home_screen_viewmodel.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen>
    with SingleTickerProviderStateMixin {
  late final ScrollController _scrollController;
  late final AnimationController _progressController;
  late final Animation<double> _progressAnimation;
  bool _isInitialized = false;

  // Pastel colour pairs
  static const Color _upNextLight = Color.fromARGB(255, 223, 180, 169);
  static const Color _upNextDark = Color(0xFF2D2A2A);
  static const Color _progressLight = Color.fromARGB(255, 209, 235, 217);
  static const Color _progressDark = Color(0xFF1E2A24);
  static const Color _focusLight = Color.fromARGB(255, 203, 194, 240);
  static const Color _focusDark = Color(0xFF2D2A4A);
  static const Color _scheduleLight = Color.fromARGB(255, 201, 225, 241);
  static const Color _scheduleDark = Color(0xFF1A283A);

  // Fallback data (used when ViewModel is empty)
  static const _userName = 'Areej';
  static const _progressValue = 0.65;

  final _upcomingTask = TaskData(
    title: 'NLP Mid Exam',
    day: 'Thursday',
    taskTime: '3:00 PM',
  );

  final List<FocusData> _fallbackFocusList = [
    FocusData(
      title: 'Python Roadmap',
      nextTopic: 'OOP Concepts',
      nextTopicTime: DateTime.now().add(const Duration(hours: 2)),
    ),
    FocusData(
      title: 'Flutter Animations',
      nextTopic: 'CustomPaint',
      nextTopicTime: DateTime.now().add(const Duration(hours: 5)),
    ),
  ];

  final List<ScheduleItem> _fallbackSchedule = [
    ScheduleItem(
      time: DateTime(2023, 10, 1, 8, 0),
      title: 'Math Lecture',
      tag: 'completed',
    ),
    ScheduleItem(
      time: DateTime(2023, 10, 1, 10, 0),
      title: 'Intro to AI',
      tag: 'pending',
    ),
    ScheduleItem(
      time: DateTime(2023, 10, 1, 13, 0),
      title: 'Physics Lab',
      tag: 'ongoing',
    ),
    ScheduleItem(
      time: DateTime(2023, 10, 1, 15, 30),
      title: 'Group Study',
      tag: 'due',
    ),
    ScheduleItem(
      time: DateTime(2023, 10, 1, 17, 0),
      title: 'NLP Exam Prep',
      tag: 'pending',
    ),
  ];

  @override
  void initState() {
    super.initState();
    _scrollController = ScrollController();
    _progressController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    );
    _progressAnimation = CurvedAnimation(
      parent: _progressController,
      curve: Curves.easeOutCubic,
    );
    Future.delayed(const Duration(milliseconds: 400), () {
      if (mounted) _progressController.forward();
    });
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_isInitialized) {
      _isInitialized = true;
      context.read<HomeScreenViewModel>().loadHomeScreenData();
    }
  }

  @override
  void dispose() {
    _scrollController.dispose();
    _progressController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<HomeScreenViewModel>();
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final primaryText = Theme.of(context).textTheme.bodyMedium!.color!;
    final secondaryText = Theme.of(context).textTheme.bodySmall!.color!;

    final userName = vm.userProfile?.name ?? _userName;
    final progressValue = vm.userProfile?.dailyProgress ?? _progressValue;
    final upcomingTask = vm.upcomingTask ?? _upcomingTask;
    // ✅ Use list from ViewModel or fallback
    final focusList = vm.focusList.isNotEmpty
        ? vm.focusList
        : _fallbackFocusList;
    final schedule = vm.schedule.isNotEmpty ? vm.schedule : _fallbackSchedule;

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: SafeArea(
        child: CustomScrollView(
          controller: _scrollController,
          slivers: [
            SliverToBoxAdapter(
              child: _buildHeader(
                isDark,
                primaryText,
                secondaryText,
                context,
                userName,
              ),
            ),
            if (vm.error != null)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 8,
                  ),
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.red.shade50,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: Colors.red.shade200),
                    ),
                    child: Text(
                      vm.error!,
                      style: AppTextStyles.subtitleSmall.copyWith(
                        color: Colors.red.shade700,
                        fontSize: 13,
                      ),
                    ),
                  ),
                ),
              ),
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                child: IntrinsicHeight(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Expanded(child: _buildUpNextCard(isDark, upcomingTask)),
                      const SizedBox(width: 12),
                      Expanded(
                        child: _buildProgressCard(isDark, progressValue),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SliverToBoxAdapter(child: SizedBox(height: 12)),
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                child: _buildCurrentFocusCard(isDark, focusList), // ✅ pass list
              ),
            ),
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                child: _buildScheduleCard(
                  isDark,
                  primaryText,
                  secondaryText,
                  schedule,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ─── HEADER ──────────────────────────────────────────────
  Widget _buildHeader(
    bool isDark,
    Color primaryText,
    Color secondaryText,
    BuildContext context,
    String userName,
  ) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 20),
                Text(
                  _greeting(),
                  style: AppTextStyles.info.copyWith(
                    color: secondaryText,
                    letterSpacing: 1.0,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  userName,
                  style: AppTextStyles.headline.copyWith(
                    fontSize: 32,
                    color: primaryText,
                    height: 1.0,
                  ),
                ),
              ],
            ),
          ),
          Row(
            children: [
              GestureDetector(
                onTap: () {},
                child: Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: isDark ? AppColors.cardElevatedDark : Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: isDark
                          ? AppColors.borderDark
                          : AppColors.borderLight,
                    ),
                  ),
                  child: Icon(
                    Icons.notifications_outlined,
                    size: 20,
                    color: isDark
                        ? AppColors.secondaryTextDark
                        : AppColors.secondaryTextLight,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              GestureDetector(
                onTap: () => context.go('/settings'),
                child: Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: AppColors.primary,
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.primary.withOpacity(0.35),
                        blurRadius: 12,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: const Center(
                    child: Text(
                      'A',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ─── UP NEXT CARD ─────────────────────────────────────────
  Widget _buildUpNextCard(bool isDark, TaskData t) {
    final bg = isDark ? _upNextDark : _upNextLight;
    final border = isDark ? AppColors.borderDark : AppColors.borderLight;
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: _cardDecoration(bg, border, isDark),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'Up Next',
            style: AppTextStyles.logo.copyWith(
              fontSize: 16,
              color: isDark
                  ? AppColors.primaryTextDark
                  : AppColors.primaryTextLight,
            ),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: Color(0xFFDBEAFE).withOpacity(isDark ? 0.2 : 1.0),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  Icons.edit_calendar_rounded,
                  color: Color(0xFF3B82F6),
                  size: 22,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      t.title,
                      style: AppTextStyles.subtitleSmall.copyWith(
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                        color: isDark
                            ? AppColors.primaryTextDark
                            : AppColors.primaryTextLight,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      t.day, // Display the day
                      style: AppTextStyles.subtitleSmall.copyWith(
                        fontSize: 11,
                        color: isDark
                            ? AppColors.secondaryTextDark
                            : AppColors.secondaryTextLight,
                      ),
                    ),
                    Text(
                      t.taskTime, // Display the task time
                      style: AppTextStyles.subtitleSmall.copyWith(
                        fontSize: 11,
                        color: isDark
                            ? AppColors.secondaryTextDark
                            : AppColors.secondaryTextLight,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          SizedBox(
            height: 34,
            child: ElevatedButton(
              onPressed: () {},
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
                elevation: 0,
                minimumSize: const Size(0, 34),
              ),
              child: Text(
                'Remind Me',
                style: AppTextStyles.button.copyWith(fontSize: 12),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ─── DAILY PROGRESS CARD (donut chart) ─────────────────────
  Widget _buildProgressCard(bool isDark, double progress) {
    final bg = isDark ? _progressDark : _progressLight;
    final border = isDark ? AppColors.borderDark : AppColors.borderLight;
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: _cardDecoration(bg, border, isDark),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'Daily Progress',
            style: AppTextStyles.logo.copyWith(
              fontSize: 16,
              color: isDark
                  ? AppColors.primaryTextDark
                  : AppColors.primaryTextLight,
            ),
          ),
          const SizedBox(height: 18),
          Center(
            child: SizedBox(
              width: 120,
              height: 120,
              child: AnimatedBuilder(
                animation: _progressAnimation,
                builder: (_, __) => CustomPaint(
                  painter: _DonutPainter(
                    progress: _progressAnimation.value * progress,
                    isDark: isDark,
                  ),
                  child: Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          '${(_progressAnimation.value * progress * 100).toInt()}%',
                          style: AppTextStyles.headline.copyWith(
                            fontSize: 24,
                            fontWeight: FontWeight.w800,
                            color: AppColors.primary,
                          ),
                        ),
                        Text(
                          'done',
                          style: AppTextStyles.subtitleSmall.copyWith(
                            fontSize: 12,
                            color: isDark
                                ? AppColors.secondaryTextDark
                                : AppColors.secondaryTextLight,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ─── CURRENT FOCUS CARD (scrollable list of tiles) ─────────
  Widget _buildCurrentFocusCard(bool isDark, List<FocusData> focusList) {
    final bg = isDark ? _focusDark : _focusLight;
    final border = isDark ? AppColors.borderDark : AppColors.borderLight;
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: _cardDecoration(bg, border, isDark),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Learning',
            style: AppTextStyles.info.copyWith(
              color: isDark
                  ? AppColors.secondaryTextDark
                  : AppColors.secondaryTextLight,
              letterSpacing: 1.0,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Current Focus',
            style: AppTextStyles.logo.copyWith(
              fontSize: 16,
              color: isDark
                  ? AppColors.primaryTextDark
                  : AppColors.primaryTextLight,
            ),
          ),
          const SizedBox(height: 16),
          ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 240),
            child: ListView.separated(
              shrinkWrap: true,
              physics: const BouncingScrollPhysics(),
              itemCount: focusList.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (_, index) =>
                  _buildFocusTile(focusList[index], isDark),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFocusTile(FocusData f, bool isDark) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: isDark ? Colors.black12 : Colors.white.withOpacity(0.5),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isDark ? AppColors.borderDark : AppColors.borderLight,
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            f.title,
            style: TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w700,
              color: isDark
                  ? AppColors.primaryTextDark
                  : AppColors.primaryTextLight,
            ),
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              Icon(Icons.schedule, size: 14, color: AppColors.primary),
              const SizedBox(width: 4),
              Text(
                f.nextTopic,
                style: TextStyle(
                  fontSize: 12,
                  color: isDark
                      ? AppColors.secondaryTextDark
                      : AppColors.secondaryTextLight,
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: AppColors.primary.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  _format12HourTime(f.nextTopicTime),
                  style: const TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w500,
                    color: AppColors.primary,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ─── TODAY'S SCHEDULE CARD (with tagged tiles) ─────────────
  Widget _buildScheduleCard(
    bool isDark,
    Color primaryText,
    Color secondaryText,
    List<ScheduleItem> schedule,
  ) {
    final bg = isDark ? _scheduleDark : _scheduleLight;
    final border = isDark ? AppColors.borderDark : AppColors.borderLight;
    return Container(
      decoration: _cardDecoration(bg, border, isDark),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 18, 18, 8),
            child: Text(
              "Today's Schedule",
              style: AppTextStyles.logo.copyWith(
                fontSize: 16,
                color: primaryText,
              ),
            ),
          ),
          ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 340),
            child: ListView.separated(
              padding: const EdgeInsets.symmetric(horizontal: 18),
              physics: const BouncingScrollPhysics(),
              itemCount: schedule.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (_, i) => _buildScheduleItem(schedule[i], isDark),
            ),
          ),
          const SizedBox(height: 12),
        ],
      ),
    );
  }

  Widget _buildScheduleItem(ScheduleItem item, bool isDark) {
    final tagColor = _getTagColor(item.tag);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: isDark ? Colors.black12 : Colors.white.withOpacity(0.7),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isDark ? AppColors.borderDark : AppColors.borderLight,
          width: 1,
        ),
      ),
      child: Row(
        children: [
          SizedBox(
            width: 60,
            child: Text(
              _format12HourTime(item.time),
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: isDark
                    ? AppColors.secondaryTextDark
                    : AppColors.secondaryTextLight,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              item.title,
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: isDark
                    ? AppColors.primaryTextDark
                    : AppColors.primaryTextLight,
              ),
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: tagColor.withOpacity(isDark ? 0.2 : 0.1),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: tagColor, width: 1),
            ),
            child: Text(
              item.tag.toUpperCase(),
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.bold,
                color: tagColor,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Color _getTagColor(String tag) {
    switch (tag.toLowerCase()) {
      case 'completed':
        return Colors.green;
      case 'ongoing':
        return Colors.blue;
      case 'pending':
        return Colors.orange;
      case 'due':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  // ─── HELPERS ───────────────────────────────────────────────
  String _format12HourTime(DateTime time) {
    int hour = time.hour;
    final minute = time.minute;
    final period = hour >= 12 ? 'PM' : 'AM';
    hour = hour % 12;
    if (hour == 0) hour = 12;
    return '$hour:${minute.toString().padLeft(2, '0')} $period';
  }

  BoxDecoration _cardDecoration(Color bg, Color border, bool isDark) {
    return BoxDecoration(
      color: bg,
      borderRadius: BorderRadius.circular(24),
      border: Border.all(color: border, width: 1),
      boxShadow: [
        BoxShadow(
          color: Colors.black.withOpacity(isDark ? 0.3 : 0.04),
          blurRadius: 16,
          offset: const Offset(0, 4),
        ),
      ],
    );
  }

  String _greeting() {
    final h = DateTime.now().hour;
    if (h < 12) return 'GOOD MORNING,';
    if (h < 17) return 'GOOD AFTERNOON,';
    return 'GOOD EVENING,';
  }
}

// ─── DONUT PAINTER ───────────────────────────────────────────
class _DonutPainter extends CustomPainter {
  final double progress;
  final bool isDark;

  const _DonutPainter({required this.progress, required this.isDark});

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height / 2;
    final radius = (size.width / 2) - 6;
    const strokeWidth = 8.0;

    final trackPaint = Paint()
      ..color = isDark ? AppColors.borderDark : const Color(0xFFE5E7EB)
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    final progressPaint = Paint()
      ..shader = const LinearGradient(
        colors: [AppColors.primary, AppColors.primaryDark],
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      ).createShader(Rect.fromCircle(center: Offset(cx, cy), radius: radius))
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    canvas.drawCircle(Offset(cx, cy), radius, trackPaint);
    final sweepAngle = 2 * math.pi * progress.clamp(0.0, 1.0);
    canvas.drawArc(
      Rect.fromCircle(center: Offset(cx, cy), radius: radius),
      -math.pi / 2,
      sweepAngle,
      false,
      progressPaint,
    );
  }

  @override
  bool shouldRepaint(_DonutPainter old) => old.progress != progress;
}

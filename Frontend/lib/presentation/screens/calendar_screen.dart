import '../../core/theme/app_text_style.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:table_calendar/table_calendar.dart';
import '../../core/theme/app_colours.dart';
import '../../data/models/calendar_task_model.dart';
import '../providers/calendar_viewmodel.dart';
import '../providers/task_refresh_notifier.dart';
import 'package:lottie/lottie.dart';
import '../widgets/task_edit_sheet.dart';
import '../widgets/collaborator_avatars.dart';

class CalendarScreen extends StatefulWidget {
  final DateTime? initialDate;
  final String? initialTaskId;

  const CalendarScreen({super.key, this.initialDate, this.initialTaskId});

  @override
  State<CalendarScreen> createState() => _CalendarScreenState();
}

class _CalendarScreenState extends State<CalendarScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _listAnimController;
  late final Animation<double> _listFadeAnim;
  bool _dialogShown = false;
  bool _dialogOpenScheduled = false;
  VoidCallback? _viewModelListener;
  DateTime _lastLoadTime = DateTime.now();
  CalendarViewModel? _vm;
  bool _refreshListening = false;
  bool _depsInitialized = false;

  @override
  void initState() {
    super.initState();
    _listAnimController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 320),
    );
    _listFadeAnim = CurvedAnimation(
      parent: _listAnimController,
      curve: Curves.easeOut,
    );
    _listAnimController.forward();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final refreshNotifier = context.read<TaskRefreshNotifier>();
    // Register once — didChangeDependencies can run many times.
    if (!_refreshListening) {
      refreshNotifier.addListener(_onRefreshSignal);
      _refreshListening = true;
    }
    final vm = context.read<CalendarViewModel>();
    _vm = vm;
    if (_viewModelListener == null) {
      _viewModelListener = _tryOpenDialog;
      vm.addListener(_viewModelListener!);
    }
    // Load on first entry, or when another screen signaled a task change.
    // Do NOT reload just because tasks are empty (that races in-flight loads).
    final shouldLoad = !_depsInitialized
        || refreshNotifier.needsRefresh;
    _depsInitialized = true;
    if (shouldLoad) {
      refreshNotifier.consume();
      _lastLoadTime = DateTime.now();
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        vm.loadTasks();
      });
    }
    _scheduleDialogTry();
  }

  @override
  void dispose() {
    if (_refreshListening) {
      context.read<TaskRefreshNotifier>().removeListener(_onRefreshSignal);
      _refreshListening = false;
    }
    if (_viewModelListener != null) {
      _vm?.removeListener(_viewModelListener!);
    }
    _listAnimController.dispose();
    super.dispose();
  }

  void _tryOpenDialog() {
    if (!mounted || _dialogShown || widget.initialTaskId == null) return;

    final vm = context.read<CalendarViewModel>();
    if (vm.tasks.isEmpty) {
      _scheduleDialogTry();
      return;
    }

    try {
      final task = vm.tasks.firstWhere((t) => t.id == widget.initialTaskId);
      if (!task.isLearningTask) {
        _showEditDialog(context, vm, task);
        _dialogShown = true;
      }
    } catch (_) {
      // Task not found – ignore
    }
  }

  void _scheduleDialogTry() {
    if (!mounted || _dialogOpenScheduled) return;
    _dialogOpenScheduled = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _dialogOpenScheduled = false;
      _tryOpenDialog();
    });
  }

  void _onRefreshSignal() {
    if (!mounted) return;
    context.read<TaskRefreshNotifier>().consume();
    _lastLoadTime = DateTime.now();
    final vm = context.read<CalendarViewModel>();
    vm.loadTasks(); // reload tasks from database
    // optional: animate the list again
    _listAnimController.reset();
    _listAnimController.forward();
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<CalendarViewModel>();
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: SafeArea(
        child: Column(
          children: [
            _buildScreenHeader(isDark),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: _buildCalendar(context, vm, isDark),
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: _buildTaskListCard(context, vm, isDark),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ========== HEADER ==========
  Widget _buildScreenHeader(bool isDark) {
    final titleColor = isDark ? Colors.white : AppColors.primaryTextLight;
    final subtitleColor = isDark
        ? Colors.white70
        : AppColors.secondaryTextLight;
    final today = DateTime.now();
    const monthNames = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];
    final formattedDate =
        '${monthNames[today.month - 1]} ${today.day}, ${today.year}';

    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Calendar',
                  style: AppTextStyles.headerLarge.copyWith(
                    color: titleColor,
                    letterSpacing: -0.5,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Your schedule for the day',
                  style: AppTextStyles.subtitleMedium.copyWith(
                    color: subtitleColor,
                  ),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: isDark
                  ? const Color(0xFF2C2C2C)
                  : AppColors.primary.withOpacity(0.1),
              borderRadius: BorderRadius.circular(30),
              border: Border.all(
                color: isDark
                    ? const Color(0xFF3A3A3A)
                    : AppColors.primary.withOpacity(0.2),
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.calendar_today_rounded,
                  size: 14,
                  color: AppColors.primary,
                ),
                const SizedBox(width: 6),
                Text(
                  formattedDate,
                  style: AppTextStyles.body.copyWith(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: AppColors.primary,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ========== CALENDAR – Full Width, No Side Padding ==========
  Widget _buildCalendar(
    BuildContext context,
    CalendarViewModel vm,
    bool isDark,
  ) {
    final cardBg = isDark
        ? const Color(0xFF1A1F2E)
        : const Color.fromARGB(255, 163, 211, 230);
    final borderColor = isDark ? AppColors.borderDark : Colors.grey.shade200;
    final textColorLight = isDark ? Colors.white : const Color(0xFF1F2937);
    final weekdayColor = isDark
        ? Colors.white.withOpacity(0.65)
        : const Color(0xFF6B7280);
    final outsideText = isDark
        ? Colors.white.withOpacity(0.35)
        : const Color(0xFF9CA3AF);

    const monthNames = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];

    return Container(
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(32),
        border: Border.all(color: borderColor, width: isDark ? 0.5 : 1),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(isDark ? 0.25 : 0.04),
            blurRadius: 20,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(20),
          topRight: Radius.circular(20),
        ),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(18, 18, 18, 14),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  IconButton(
                    onPressed: () => vm.setFocusedDay(
                      DateTime(vm.focusedDay.year, vm.focusedDay.month - 1, 1),
                    ),
                    icon: Icon(
                      Icons.chevron_left_rounded,
                      color: isDark ? Colors.white70 : const Color(0xFF4B5563),
                      size: 28,
                    ),
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                  ),
                  Text(
                    '${monthNames[vm.focusedDay.month - 1]} ${vm.focusedDay.year}',
                    style: AppTextStyles.body.copyWith(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                      color: textColorLight,
                    ),
                  ),
                  IconButton(
                    onPressed: () => vm.setFocusedDay(
                      DateTime(vm.focusedDay.year, vm.focusedDay.month + 1, 1),
                    ),
                    icon: Icon(
                      Icons.chevron_right_rounded,
                      color: isDark ? Colors.white70 : const Color(0xFF4B5563),
                      size: 28,
                    ),
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: TableCalendar<CalendarTask>(
                  firstDay: DateTime.utc(2024, 1, 1),
                  lastDay: DateTime.utc(2027, 12, 31),
                  focusedDay: vm.focusedDay,
                  selectedDayPredicate: (day) => isSameDay(vm.selectedDay, day),
                  calendarFormat: vm.calendarFormat,
                  eventLoader: vm.eventLoader,
                  startingDayOfWeek: StartingDayOfWeek.sunday,
                  availableGestures: AvailableGestures.all,
                  daysOfWeekHeight: 28,
                  rowHeight: 50,
                  onDaySelected: (selected, focused) {
                    HapticFeedback.selectionClick();
                    vm.onDaySelected(selected, focused);
                    _listAnimController.reset();
                    _listAnimController.forward();
                  },
                  onPageChanged: (focused) => vm.setFocusedDay(focused),
                  onFormatChanged: (format) => vm.setCalendarFormat(format),
                  headerVisible: false,
                  daysOfWeekStyle: DaysOfWeekStyle(
                    weekdayStyle: AppTextStyles.body.copyWith(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: weekdayColor,
                    ),
                    weekendStyle: AppTextStyles.body.copyWith(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: weekdayColor,
                    ),
                  ),
                  calendarStyle: CalendarStyle(
                    todayDecoration: BoxDecoration(
                      color: isDark
                          ? Colors.white.withOpacity(0.15)
                          : AppColors.primary.withOpacity(0.12),
                      shape: BoxShape.circle,
                    ),
                    todayTextStyle: AppTextStyles.body.copyWith(
                      color: isDark ? Colors.white : AppColors.primary,
                      fontWeight: FontWeight.w700,
                      fontSize: 14,
                    ),
                    selectedDecoration: const BoxDecoration(
                      color: AppColors.primary,
                      shape: BoxShape.circle,
                    ),
                    selectedTextStyle: AppTextStyles.body.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w700,
                      fontSize: 14,
                    ),
                    defaultTextStyle: AppTextStyles.body.copyWith(
                      color: textColorLight,
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                    weekendTextStyle: AppTextStyles.body.copyWith(
                      color: textColorLight.withOpacity(0.85),
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                    outsideDaysVisible: true,
                    outsideTextStyle: AppTextStyles.body.copyWith(
                      color: outsideText,
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                    markerDecoration: BoxDecoration(
                      color: AppColors.primary,
                      shape: BoxShape.circle,
                    ),
                    markerSize: 5,
                    markersMaxCount: 1,
                    markerMargin: const EdgeInsets.only(top: 4),
                    cellMargin: const EdgeInsets.all(2),
                    tableBorder: TableBorder.all(color: Colors.transparent),
                  ),
                  calendarBuilders: CalendarBuilders(
                    defaultBuilder: (context, day, focusedDay) {
                      final isSelected = isSameDay(day, vm.selectedDay);
                      final isToday = isSameDay(day, DateTime.now());
                      final isCurrentMonth = day.month == vm.focusedDay.month;

                      Color textColor;
                      if (isSelected) {
                        textColor = Colors.white;
                      } else if (isToday) {
                        textColor = isDark ? Colors.white : AppColors.primary;
                      } else {
                        textColor = isCurrentMonth
                            ? textColorLight
                            : outsideText;
                      }

                      Widget? background;
                      if (isSelected) {
                        background = Container(
                          width: 34,
                          height: 34,
                          decoration: const BoxDecoration(
                            color: AppColors.primary,
                            shape: BoxShape.circle,
                          ),
                        );
                      } else if (isToday) {
                        background = Container(
                          width: 34,
                          height: 34,
                          decoration: BoxDecoration(
                            color: isDark
                                ? Colors.white.withOpacity(0.15)
                                : AppColors.primary.withOpacity(0.12),
                            shape: BoxShape.circle,
                          ),
                        );
                      }

                      return Center(
                        child: Stack(
                          alignment: Alignment.center,
                          children: [
                            if (background != null) background,
                            Text(
                              '${day.day}',
                              style: AppTextStyles.body.copyWith(
                                fontSize: 14,
                                fontWeight: (isSelected || isToday)
                                    ? FontWeight.w700
                                    : FontWeight.w500,
                                color: textColor,
                              ),
                            ),
                          ],
                        ),
                      );
                    },
                  ),
                ),
              ),
              const SizedBox(height: 4),
            ],
          ),
        ),
      ),
    );
  }

  // ========== TASK LIST CARD – Flat Top, Only Bottom Corners Rounded ==========
  Widget _buildTaskListCard(
    BuildContext context,
    CalendarViewModel vm,
    bool isDark,
  ) {
    return Container(
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E1E1E) : Colors.white,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(32),
          topRight: Radius.circular(32),
        ),
        border: Border(
          left: BorderSide(color: Colors.grey),
          right: BorderSide(color: Colors.grey),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(isDark ? 0.20 : 0.08),
            blurRadius: 18,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(32),
          topRight: Radius.circular(32),
        ),
        child: RefreshIndicator(
          onRefresh: () async {
            await vm.loadTasks();
            _listAnimController.reset();
            _listAnimController.forward();
          },
          child: CustomScrollView(
            slivers: [
              SliverToBoxAdapter(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Grey drag handle – kept for visual cue
                    const SizedBox(height: 6),
                    Center(
                      child: Container(
                        width: 42,
                        height: 4,
                        decoration: BoxDecoration(
                          color: (isDark ? Colors.white : Colors.grey)
                              .withOpacity(0.28),
                          borderRadius: BorderRadius.circular(99),
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    // Header – now with less top padding
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 20),
                      child: _buildTaskListHeaderContent(context, vm, isDark),
                    ),
                  ],
                ),
              ),
              if (vm.filteredTasks.isEmpty)
                SliverToBoxAdapter(child: _buildEmptyState(isDark))
              else
                SliverPadding(
                  padding: const EdgeInsets.only(bottom: 15),
                  sliver: SliverList(
                    delegate: SliverChildBuilderDelegate(
                      (_, i) => FadeTransition(
                        opacity: _listFadeAnim,
                        child: _buildTaskTile(
                          context,
                          vm,
                          vm.filteredTasks[i],
                          isDark,
                          i,
                        ),
                      ),
                      childCount: vm.filteredTasks.length,
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  // ========== TASK LIST HEADER CONTENT ==========
  Widget _buildTaskListHeaderContent(
    BuildContext context,
    CalendarViewModel vm,
    bool isDark,
  ) {
    final primary = isDark
        ? AppColors.primaryTextDark
        : AppColors.primaryTextLight;
    final secondary = isDark
        ? AppColors.secondaryTextDark
        : AppColors.secondaryTextLight;
    const months = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];
    final isToday = isSameDay(vm.selectedDay, DateTime.now());
    final dateLabel = isToday
        ? 'Today'
        : '${_dayName(vm.selectedDay.weekday)}, ${vm.selectedDay.day} ${months[vm.selectedDay.month - 1]}';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          dateLabel,
          style: AppTextStyles.body.copyWith(
            fontSize: 20,
            fontWeight: FontWeight.w700,
            color: primary,
            letterSpacing: -0.3,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          '${vm.selectedTotal} task${vm.selectedTotal != 1 ? 's' : ''}',
          style: AppTextStyles.subtitleMedium.copyWith(color: secondary),
        ),
      ],
    );
  }

  // ========== TASK TILE (with learning tasks support) ==========
  Widget _buildTaskTile(
    BuildContext context,
    CalendarViewModel vm,
    CalendarTask task,
    bool isDark,
    int index,
  ) {
    final bg = isDark ? const Color(0xFF2C2C2C) : const Color(0xFFF3F4F6);
    final border = isDark ? const Color(0xFF3A3A3A) : AppColors.borderLight;
    final primary = isDark ? Colors.white : AppColors.primaryTextLight;
    final secondary = isDark
        ? const Color(0xFFB8C2D9)
        : AppColors.secondaryTextLight;
    final priorityColor = _priorityColor(task.priority);
    final statusColor = _statusColor(task.displayStatus);

    final isLearning = task.isLearningTask;

    // ─── Base tile widget ──────────────────────────────────────────────
    Widget tile = ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: GestureDetector(
        onTap: isLearning ? null : () => _showEditDialog(context, vm, task),
        child: AnimatedOpacity(
          duration: const Duration(milliseconds: 300),
          opacity: task.isCompleted ? 0.65 : 1.0,
          child: Container(
            decoration: BoxDecoration(
              color: bg,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: border),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(isDark ? 0.16 : 0.04),
                  blurRadius: 10,
                  offset: const Offset(0, 3),
                ),
              ],
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: IntrinsicHeight(
                child: Row(
                  children: [
                    Container(width: 4, color: priorityColor),
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(14, 13, 14, 13),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              width: 38,
                              height: 38,
                              decoration: BoxDecoration(
                                color: _categoryColor(
                                  task.priority,
                                ).withOpacity(isDark ? 0.18 : 0.10),
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: Icon(
                                _categoryIcon(task.priority),
                                size: 18,
                                color: _categoryColor(task.priority),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  // ── Title row (with lock icon for learning tasks) ──
                                  Row(
                                    children: [
                                      Expanded(
                                        child: Text(
                                          task.title,
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: AppTextStyles.body.copyWith(
                                            fontSize: 14,
                                            fontWeight: FontWeight.w600,
                                            color: primary,
                                            decoration: task.isCompleted
                                                ? TextDecoration.lineThrough
                                                : null,
                                            decorationColor: secondary,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 6),
                                  // ── Time and status ──
                                  Row(
                                    children: [
                                      Icon(
                                        Icons.schedule_rounded,
                                        size: 12,
                                        color: secondary,
                                      ),
                                      const SizedBox(width: 3),
                                      Text(
                                        vm.formatTimeRange(task, context),
                                        style: AppTextStyles.body.copyWith(
                                          fontSize: 11,
                                          color: secondary,
                                          fontWeight: FontWeight.w500,
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Container(
                                        padding: const EdgeInsets.symmetric(
                                          horizontal: 6,
                                          vertical: 2,
                                        ),
                                        decoration: BoxDecoration(
                                          color: statusColor.withOpacity(0.12),
                                          borderRadius: BorderRadius.circular(
                                            6,
                                          ),
                                        ),
                                        child: Text(
                                          task.displayStatus.toUpperCase(),
                                          style: AppTextStyles.body.copyWith(
                                            fontSize: 9,
                                            fontWeight: FontWeight.w700,
                                            color: statusColor,
                                            letterSpacing: 0.3,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                  // ── Collaborators (shared tasks only) ──
                                  if (task.collaborators.isNotEmpty) ...[
                                    const SizedBox(height: 6),
                                    CollaboratorSummaryRow(
                                      collaborators: task.collaborators,
                                    ),
                                  ],
                                ],
                              ),
                            ),
                            // ─── Toggle button OR lock icon ──────────────
                            if (!isLearning)
                              GestureDetector(
                                onTap: () async {
                                  try {
                                    await vm.toggleTask(task);
                                  } catch (e) {
                                    if (!mounted) return;
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(
                                        content: Text(
                                          'Failed to update task: $e',
                                        ),
                                      ),
                                    );
                                  }
                                },
                                child: AnimatedContainer(
                                  duration: const Duration(milliseconds: 250),
                                  width: 28,
                                  height: 28,
                                  decoration: BoxDecoration(
                                    color: task.isCompleted
                                        ? const Color(0xFF22C55E)
                                        : Colors.transparent,
                                    shape: BoxShape.circle,
                                    border: Border.all(
                                      color: task.isCompleted
                                          ? const Color(0xFF22C55E)
                                          : (isDark
                                                ? const Color(0xFF3A3A3A)
                                                : AppColors.borderLight),
                                      width: 2,
                                    ),
                                  ),
                                  child: task.isCompleted
                                      ? const Icon(
                                          Icons.check_rounded,
                                          color: Colors.white,
                                          size: 16,
                                        )
                                      : null,
                                ),
                              )
                            else
                              const SizedBox(width: 28),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );

    // ─── Wrap with Dismissible only if NOT learning ────────────────
    if (!isLearning) {
      tile = Dismissible(
        key: Key(task.id),
        direction: DismissDirection.endToStart,
        background: ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: Container(
            alignment: Alignment.centerRight,
            padding: const EdgeInsets.only(right: 20),
            color: const Color(0xFFEF4444).withOpacity(0.12),
            child: const Icon(
              Icons.delete_outline_rounded,
              color: Color(0xFFEF4444),
              size: 22,
            ),
          ),
        ),
        onDismissed: (_) async {
          try {
            await vm.deleteTask(task);
            if (!mounted) return;
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text('${task.title} removed'),
                duration: const Duration(seconds: 1),
                behavior: SnackBarBehavior.floating,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                margin: const EdgeInsets.all(12),
              ),
            );
          } catch (e) {
            if (!mounted) return;
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('Failed to delete task: $e')),
            );
          }
        },
        child: tile,
      );
    }

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
      child: tile,
    );
  }

  // ========== EMPTY STATE ==========
  Widget _buildEmptyState(bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 40),
      child: Column(
        children: [
          SizedBox(
            height: 200,
            width: 200,
            child: Lottie.asset(
              'assets/lottie/Agenda.json',
              fit: BoxFit.contain,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            'No tasks for this day',
            style: AppTextStyles.body.copyWith(
              fontSize: 16,
              fontWeight: FontWeight.w600,
              color: AppColors.primary.withOpacity(0.7),
            ),
          ),
        ],
      ),
    );
  }

  // ========== EDIT SHEET ==========
  void _showEditDialog(
    BuildContext context,
    CalendarViewModel vm,
    CalendarTask task,
  ) {
    showTaskEditSheet(
      context,
      viewModel: vm,
      task: task,
      onSaved: () {
        if (!mounted) return;
        _listAnimController.reset();
        _listAnimController.forward();
      },
    );
  }

  // ========== HELPERS ==========
  Color _priorityColor(TaskPriority p) {
    switch (p) {
      case TaskPriority.high:
        return const Color(0xFFEF4444);
      case TaskPriority.medium:
        return const Color(0xFFF59E0B);
      case TaskPriority.low:
        return const Color(0xFF22C55E);
    }
  }

  Color _statusColor(String displayStatus) {
    switch (displayStatus) {
      case 'pending':
        return Colors.orange;
      case 'ongoing':
        return Colors.blue;
      case 'overdue':
        return Colors.red;
      case 'complete':
        return Colors.green;
      default:
        return Colors.grey;
    }
  }

  IconData _categoryIcon(TaskPriority p) {
    switch (p) {
      case TaskPriority.high:
        return Icons.priority_high;
      case TaskPriority.medium:
        return Icons.flag;
      case TaskPriority.low:
        return Icons.flag_outlined;
    }
  }

  Color _categoryColor(TaskPriority p) {
    switch (p) {
      case TaskPriority.high:
        return const Color(0xFFEF4444);
      case TaskPriority.medium:
        return const Color(0xFFF59E0B);
      case TaskPriority.low:
        return const Color(0xFF22C55E);
    }
  }

  String _dayName(int weekday) {
    const days = [
      'Monday',
      'Tuesday',
      'Wednesday',
      'Thursday',
      'Friday',
      'Saturday',
      'Sunday',
    ];
    return days[weekday - 1];
  }
}

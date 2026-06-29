// ─── Root ─────────────
class AnalyticsDashboard {
  final String generatedAt;
  final String timezone;
  final int rangeDays;
  final HeroStats hero;
  final BehavioralSection behavioral;
  final HeatmapSection heatmap;
  final TasksSection tasks;
  final CompletionTrendSection completionTrend;
  final List<BestSlot> bestSlots;

  AnalyticsDashboard({
    required this.generatedAt,
    required this.timezone,
    required this.rangeDays,
    required this.hero,
    required this.behavioral,
    required this.heatmap,
    required this.tasks,
    required this.completionTrend,
    required this.bestSlots,
  });

  factory AnalyticsDashboard.fromJson(Map<String, dynamic> json) {
    return AnalyticsDashboard(
      generatedAt: json['generated_at'],
      timezone: json['timezone'],
      rangeDays: json['range_days'],
      hero: HeroStats.fromJson(json['hero']),
      behavioral: BehavioralSection.fromJson(json['behavioral']),
      heatmap: HeatmapSection.fromJson(json['heatmap']),
      tasks: TasksSection.fromJson(json['tasks']),
      completionTrend: CompletionTrendSection.fromJson(
        json['completion_trend'],
      ),
      bestSlots: (json['best_slots'] as List)
          .map((s) => BestSlot.fromJson(s))
          .toList(),
    );
  }
}

// ─── Hero Stats ──────────────────────────────────────────────────────────
class HeroStats {
  final int completedThisWeek;
  final int completedLastWeek;
  final double weekChangePercent;
  final double onTimeRate;
  final int totalCompleted;
  final int streakDays;
  final int upcoming7d;

  HeroStats({
    required this.completedThisWeek,
    required this.completedLastWeek,
    required this.weekChangePercent,
    required this.onTimeRate,
    required this.totalCompleted,
    required this.streakDays,
    required this.upcoming7d,
  });

  factory HeroStats.fromJson(Map<String, dynamic> json) {
    return HeroStats(
      completedThisWeek: json['completed_this_week'] ?? 0,
      completedLastWeek: json['completed_last_week'] ?? 0,
      weekChangePercent: (json['week_change_percent'] ?? 0).toDouble(),
      onTimeRate: (json['on_time_rate'] ?? 0).toDouble(),
      totalCompleted: json['total_completed'] ?? 0,
      streakDays: json['streak_days'] ?? 0,
      upcoming7d: json['upcoming_7d'] ?? 0,
    );
  }
}

// ─── Behavioral ──────────────────────────────────────────────────────────
class BehavioralSection {
  final bool enabled;
  final bool hasEnoughData;
  final Thresholds thresholds;
  final int totalCompleted;
  final List<TopDay> topDays;
  final List<HourWindow> hourWindows;
  final String? strengthSummary;
  final List<UnreliableDay> unreliableDays;
  final CompletionRate completionRate;
  final double? avgTimeTaken;

  BehavioralSection({
    required this.enabled,
    required this.hasEnoughData,
    required this.thresholds,
    required this.totalCompleted,
    required this.topDays,
    required this.hourWindows,
    this.strengthSummary,
    required this.unreliableDays,
    required this.completionRate,
    this.avgTimeTaken,
  });

  factory BehavioralSection.fromJson(Map<String, dynamic> json) {
    return BehavioralSection(
      enabled: json['enabled'] ?? false,
      hasEnoughData: json['has_enough_data'] ?? false,
      thresholds: Thresholds.fromJson(json['thresholds'] ?? {}),
      totalCompleted: json['total_completed'] ?? 0,
      topDays:
          (json['top_days'] as List?)
              ?.map((d) => TopDay.fromJson(d))
              .toList() ??
          [],
      hourWindows:
          (json['hour_windows'] as List?)
              ?.map((w) => HourWindow.fromJson(w))
              .toList() ??
          [],
      strengthSummary: json['strength_summary'],
      unreliableDays:
          (json['unreliable_days'] as List?)
              ?.map((d) => UnreliableDay.fromJson(d))
              .toList() ??
          [],
      completionRate: CompletionRate.fromJson(json['completion_rate'] ?? {}),
      avgTimeTaken: json['avg_time_taken']?.toDouble(),
    );
  }
}

class Thresholds {
  final int global;
  final int perDay;

  Thresholds({required this.global, required this.perDay});

  factory Thresholds.fromJson(Map<String, dynamic> json) {
    return Thresholds(
      global: json['global'] ?? 20,
      perDay: json['per_day'] ?? 5,
    );
  }
}

class TopDay {
  final String day;
  final int dayNum;
  final double score;
  final int logCount;
  final double onTimeRate;

  TopDay({
    required this.day,
    required this.dayNum,
    required this.score,
    required this.logCount,
    required this.onTimeRate,
  });

  factory TopDay.fromJson(Map<String, dynamic> json) {
    return TopDay(
      day: json['day'],
      dayNum: json['day_num'],
      score: (json['score'] ?? 0).toDouble(),
      logCount: json['log_count'] ?? 0,
      onTimeRate: (json['on_time_rate'] ?? 0).toDouble(),
    );
  }
}

class HourWindow {
  final int dayNum;
  final String dayName;
  final int startHour;
  final int endHour;
  final String startDisplay;
  final String endDisplay;
  final String label;
  final double score;
  final int logCount;

  HourWindow({
    required this.dayNum,
    required this.dayName,
    required this.startHour,
    required this.endHour,
    required this.startDisplay,
    required this.endDisplay,
    required this.label,
    required this.score,
    required this.logCount,
  });

  factory HourWindow.fromJson(Map<String, dynamic> json) {
    return HourWindow(
      dayNum: json['day_num'],
      dayName: json['day_name'],
      startHour: json['start_hour'],
      endHour: json['end_hour'],
      startDisplay: json['start_display'],
      endDisplay: json['end_display'],
      label: json['label'],
      score: (json['score'] ?? 0).toDouble(),
      logCount: json['log_count'] ?? 0,
    );
  }
}

class UnreliableDay {
  final String day;
  final int dayNum;
  final int logCount;
  final int needed;

  UnreliableDay({
    required this.day,
    required this.dayNum,
    required this.logCount,
    required this.needed,
  });

  factory UnreliableDay.fromJson(Map<String, dynamic> json) {
    return UnreliableDay(
      day: json['day'],
      dayNum: json['day_num'],
      logCount: json['log_count'] ?? 0,
      needed: json['needed'] ?? 5,
    );
  }
}

class CompletionRate {
  final int totalCompleted;
  final int onTime;
  final int late;
  final double onTimeRate;

  CompletionRate({
    required this.totalCompleted,
    required this.onTime,
    required this.late,
    required this.onTimeRate,
  });

  factory CompletionRate.fromJson(Map<String, dynamic> json) {
    return CompletionRate(
      totalCompleted: json['total_completed'] ?? 0,
      onTime: json['on_time'] ?? 0,
      late: json['late'] ?? 0,
      onTimeRate: (json['on_time_rate'] ?? 0).toDouble(),
    );
  }
}

// ─── Heatmap ─────────────────────────────────────────────────────────────
class HeatmapSection {
  final int rangeDays;
  final String timezone;
  final HourRange hourRange;
  final List<HeatmapCell> cells;
  final HeatmapCell? peak;
  final HeatmapCell? weakest;

  HeatmapSection({
    required this.rangeDays,
    required this.timezone,
    required this.hourRange,
    required this.cells,
    this.peak,
    this.weakest,
  });

  factory HeatmapSection.fromJson(Map<String, dynamic> json) {
    return HeatmapSection(
      rangeDays: json['range_days'] ?? 30,
      timezone: json['timezone'] ?? 'UTC',
      hourRange: HourRange.fromJson(json['hour_range'] ?? {}),
      cells:
          (json['cells'] as List?)
              ?.map((c) => HeatmapCell.fromJson(c))
              .toList() ??
          [],
      peak: json['peak'] != null ? HeatmapCell.fromJson(json['peak']) : null,
      weakest: json['weakest'] != null
          ? HeatmapCell.fromJson(json['weakest'])
          : null,
    );
  }
}

class HourRange {
  final int start;
  final int end;
  final String startDisplay;
  final String endDisplay;

  HourRange({
    required this.start,
    required this.end,
    required this.startDisplay,
    required this.endDisplay,
  });

  factory HourRange.fromJson(Map<String, dynamic> json) {
    return HourRange(
      start: json['start'] ?? 6,
      end: json['end'] ?? 23,
      startDisplay: json['start_display'] ?? '6AM',
      endDisplay: json['end_display'] ?? '11PM',
    );
  }
}

class HeatmapCell {
  final int day;
  final String dayName;
  final int hour;
  final String hourDisplay;
  final int count;
  final double onTimeRate;
  final int intensity;

  HeatmapCell({
    required this.day,
    required this.dayName,
    required this.hour,
    required this.hourDisplay,
    required this.count,
    required this.onTimeRate,
    required this.intensity,
  });

  factory HeatmapCell.fromJson(Map<String, dynamic> json) {
    return HeatmapCell(
      day: json['day'],
      dayName: json['day_name'],
      hour: json['hour'],
      hourDisplay: json['hour_display'],
      count: json['count'] ?? 0,
      onTimeRate: (json['on_time_rate'] ?? 0).toDouble(),
      intensity: json['intensity'] ?? 0,
    );
  }
}

// ─── Tasks ──────────────────────────────────────────────────────────────
class TasksSection {
  final int pending;
  final int complete;
  final int overdue;
  final PriorityCounts byPriority;
  final List<DueSoonTask> dueWithin48h;
  final BusiestDay busiestDayThisWeek;

  TasksSection({
    required this.pending,
    required this.complete,
    required this.overdue,
    required this.byPriority,
    required this.dueWithin48h,
    required this.busiestDayThisWeek,
  });

  factory TasksSection.fromJson(Map<String, dynamic> json) {
    return TasksSection(
      pending: json['pending'] ?? 0,
      complete: json['complete'] ?? 0,
      overdue: json['overdue'] ?? 0,
      byPriority: PriorityCounts.fromJson(json['by_priority'] ?? {}),
      dueWithin48h:
          (json['due_within_48h'] as List?)
              ?.map((t) => DueSoonTask.fromJson(t))
              .toList() ??
          [],
      busiestDayThisWeek: BusiestDay.fromJson(
        json['busiest_day_this_week'] ?? {},
      ),
    );
  }
}

class PriorityCounts {
  final int high;
  final int medium;
  final int low;

  PriorityCounts({required this.high, required this.medium, required this.low});

  factory PriorityCounts.fromJson(Map<String, dynamic> json) {
    return PriorityCounts(
      high: json['high'] ?? 0,
      medium: json['medium'] ?? 0,
      low: json['low'] ?? 0,
    );
  }
}

class DueSoonTask {
  final String id;
  final String title;
  final String dueDatetime;
  final String priority;
  final String status;

  DueSoonTask({
    required this.id,
    required this.title,
    required this.dueDatetime,
    required this.priority,
    required this.status,
  });

  factory DueSoonTask.fromJson(Map<String, dynamic> json) {
    return DueSoonTask(
      id: json['id'],
      title: json['title'],
      dueDatetime: json['due_datetime'],
      priority: json['priority'] ?? 'medium',
      status: json['status'] ?? 'pending',
    );
  }
}

class BusiestDay {
  final int dayNum;
  final String dayName;
  final int taskCount;

  BusiestDay({
    required this.dayNum,
    required this.dayName,
    required this.taskCount,
  });

  factory BusiestDay.fromJson(Map<String, dynamic> json) {
    return BusiestDay(
      dayNum: json['day_num'] ?? 0,
      dayName: json['day_name'] ?? 'Monday',
      taskCount: json['task_count'] ?? 0,
    );
  }
}

// ─── Completion Trend ──────────────────────────────────────────────────
class CompletionTrendSection {
  final int weeks;
  final List<WeekTrend> trend;

  CompletionTrendSection({required this.weeks, required this.trend});

  factory CompletionTrendSection.fromJson(Map<String, dynamic> json) {
    return CompletionTrendSection(
      weeks: json['weeks'] ?? 3,
      trend:
          (json['trend'] as List?)
              ?.map((t) => WeekTrend.fromJson(t))
              .toList() ??
          [],
    );
  }
}

class WeekTrend {
  final int week;
  final int count;
  final int onTime;
  final int late;
  final double onTimeRate;

  WeekTrend({
    required this.week,
    required this.count,
    required this.onTime,
    required this.late,
    required this.onTimeRate,
  });

  factory WeekTrend.fromJson(Map<String, dynamic> json) {
    return WeekTrend(
      week: json['week'] ?? 0,
      count: json['count'] ?? 0,
      onTime: json['on_time'] ?? 0,
      late: json['late'] ?? 0,
      onTimeRate: (json['on_time_rate'] ?? 0).toDouble(),
    );
  }
}

// ─── Best Slot ──────────────────────────────────────────────────────────
class BestSlot {
  final int dayNum;
  final String dayName;
  final int hour;
  final String hourDisplay;
  final double score;
  final double onTimeRate;
  final int logCount;
  final String suggestion;

  BestSlot({
    required this.dayNum,
    required this.dayName,
    required this.hour,
    required this.hourDisplay,
    required this.score,
    required this.onTimeRate,
    required this.logCount,
    required this.suggestion,
  });

  factory BestSlot.fromJson(Map<String, dynamic> json) {
    return BestSlot(
      dayNum: json['day_num'],
      dayName: json['day_name'],
      hour: json['hour'],
      hourDisplay: json['hour_display'],
      score: (json['score'] ?? 0).toDouble(),
      onTimeRate: (json['on_time_rate'] ?? 0).toDouble(),
      logCount: json['log_count'] ?? 0,
      suggestion: json['suggestion'] ?? '',
    );
  }
}

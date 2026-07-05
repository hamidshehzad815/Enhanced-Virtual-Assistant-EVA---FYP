// lib/data/models/analytics_model.dart
import 'package:flutter/material.dart';

// ─── ROOT ──────────────────────────────────────────────────────────────
class AnalyticsDashboard {
  final String generatedAt;
  final String timezone;
  final int rangeDays;
  final Meta meta;
  final Snapshot snapshot;
  final List<Insight> insights;
  final Activity activity;
  final Behavioral behavioral;
  final Heatmap heatmap;
  final WorkPatterns workPatterns;
  final NeedsAttention needsAttention;

  AnalyticsDashboard({
    required this.generatedAt,
    required this.timezone,
    required this.rangeDays,
    required this.meta,
    required this.snapshot,
    required this.insights,
    required this.activity,
    required this.behavioral,
    required this.heatmap,
    required this.workPatterns,
    required this.needsAttention,
  });

  factory AnalyticsDashboard.fromJson(Map<String, dynamic> json) {
    final data = json['data'];
    return AnalyticsDashboard(
      generatedAt: data['generated_at'] ?? '',
      timezone: data['timezone'] ?? 'UTC',
      rangeDays: data['range_days'] ?? 30,
      meta: Meta.fromJson(data['meta'] ?? {}),
      snapshot: Snapshot.fromJson(data['snapshot'] ?? {}),
      insights:
          (data['insights'] as List?)
              ?.map((i) => Insight.fromJson(i))
              .toList() ??
          [],
      activity: Activity.fromJson(data['activity'] ?? {}),
      behavioral: Behavioral.fromJson(data['behavioral'] ?? {}),
      heatmap: Heatmap.fromJson(data['heatmap'] ?? {}),
      workPatterns: WorkPatterns.fromJson(data['work_patterns'] ?? {}),
      needsAttention: NeedsAttention.fromJson(data['needs_attention'] ?? {}),
    );
  }
}

// ─── META ──────────────────────────────────────────────────────────────
class Meta {
  final bool hasEnoughData;
  final int minTasks;
  final int tasksRemaining;
  Meta({
    this.hasEnoughData = false,
    this.minTasks = 20,
    this.tasksRemaining = 0,
  });
  factory Meta.fromJson(Map<String, dynamic> json) => Meta(
    hasEnoughData: json['has_enough_data'] ?? false,
    minTasks: json['min_tasks'] ?? 20,
    tasksRemaining: json['tasks_remaining'] ?? 0,
  );
}

// ─── SNAPSHOT ──────────────────────────────────────────────────────────
class Snapshot {
  final ProductivityScore productivityScore;
  final double onTimeRate;
  final int currentStreak;
  final Completed completed;
  Snapshot({
    required this.productivityScore,
    required this.onTimeRate,
    required this.currentStreak,
    required this.completed,
  });
  factory Snapshot.fromJson(Map<String, dynamic> json) => Snapshot(
    productivityScore: ProductivityScore.fromJson(
      json['productivity_score'] ?? {},
    ),
    onTimeRate: (json['on_time_rate'] ?? 0).toDouble(),
    currentStreak: json['current_streak'] ?? 0,
    completed: Completed.fromJson(json['completed'] ?? {}),
  );
}

class ProductivityScore {
  final int score;
  final String rating;
  final String caption;
  ProductivityScore({
    this.score = 0,
    this.rating = 'Building',
    this.caption = '',
  });
  factory ProductivityScore.fromJson(Map<String, dynamic> json) =>
      ProductivityScore(
        score: json['score'] ?? 0,
        rating: json['rating'] ?? 'Building',
        caption: json['caption'] ?? 'Keep completing tasks to build momentum.',
      );
}

class Completed {
  final int period;
  final int previous;
  final double changePercent;
  Completed({this.period = 0, this.previous = 0, this.changePercent = 0});
  factory Completed.fromJson(Map<String, dynamic> json) => Completed(
    period: json['period'] ?? 0,
    previous: json['previous'] ?? 0,
    changePercent: (json['change_percent'] ?? 0).toDouble(),
  );
}

// ─── INSIGHT ──────────────────────────────────────────────────────────
class Insight {
  final String id;
  final String type;
  final String icon;
  final String title;
  final String message;
  Insight({
    required this.id,
    required this.type,
    required this.icon,
    required this.title,
    required this.message,
  });
  factory Insight.fromJson(Map<String, dynamic> json) => Insight(
    id: json['id'] ?? '0',
    type: json['type'] ?? 'info',
    icon: json['icon'] ?? 'info',
    title: json['title'] ?? '',
    message: json['message'] ?? '',
  );
  IconData get iconData {
    switch (icon) {
      case 'local_fire_department':
        return Icons.local_fire_department_rounded;
      case 'trending_up':
        return Icons.trending_up_rounded;
      case 'trending_down':
        return Icons.trending_down_rounded;
      case 'verified':
        return Icons.verified_rounded;
      case 'schedule':
        return Icons.schedule_rounded;
      case 'bolt':
        return Icons.bolt_rounded;
      case 'priority_high':
        return Icons.priority_high_rounded;
      case 'warning_amber':
        return Icons.warning_amber_rounded;
      case 'wb_sunny':
        return Icons.wb_sunny_rounded;
      case 'calendar_month':
        return Icons.calendar_month_rounded;
      case 'rocket_launch':
        return Icons.rocket_launch_rounded;
      default:
        return Icons.info_rounded;
    }
  }
}

// ─── ACTIVITY ──────────────────────────────────────────────────────────
class Activity {
  final List<ActivityPoint> series;
  final int activeDays;
  final double avgPerActiveDay;
  Activity({
    this.series = const [],
    this.activeDays = 0,
    this.avgPerActiveDay = 0,
  });
  factory Activity.fromJson(Map<String, dynamic> json) => Activity(
    series:
        (json['series'] as List?)
            ?.map((p) => ActivityPoint.fromJson(p))
            .toList() ??
        [],
    activeDays: json['active_days'] ?? 0,
    avgPerActiveDay: (json['avg_per_active_day'] ?? 0).toDouble(),
  );
}

class ActivityPoint {
  final String date;
  final int count;
  final int onTime;
  final int late;
  ActivityPoint({
    this.date = '',
    this.count = 0,
    this.onTime = 0,
    this.late = 0,
  });
  factory ActivityPoint.fromJson(Map<String, dynamic> json) => ActivityPoint(
    date: json['date'] ?? '',
    count: json['count'] ?? 0,
    onTime: json['on_time'] ?? 0,
    late: json['late'] ?? 0,
  );
}

// ─── BEHAVIORAL ─────────────────────────────────────────────────────────
class Behavioral {
  final bool hasScores;
  final String source;
  final List<TopDay> topDays;
  final Focus focus;
  final Momentum momentum;
  final Procrastination procrastination;
  final List<UnreliableDay> unreliableDays;
  Behavioral({
    this.hasScores = false,
    this.source = 'history',
    this.topDays = const [],
    required this.focus,
    required this.momentum,
    required this.procrastination,
    this.unreliableDays = const [],
  });
  factory Behavioral.fromJson(Map<String, dynamic> json) => Behavioral(
    hasScores: json['has_scores'] ?? false,
    source: json['source'] ?? 'history',
    topDays:
        (json['top_days'] as List?)?.map((d) => TopDay.fromJson(d)).toList() ??
        [],
    focus: Focus.fromJson(json['focus'] ?? {}),
    momentum: Momentum.fromJson(json['momentum'] ?? {}),
    procrastination: Procrastination.fromJson(json['procrastination'] ?? {}),
    unreliableDays:
        (json['unreliable_days'] as List?)
            ?.map((d) => UnreliableDay.fromJson(d))
            .toList() ??
        [],
  );
}

class TopDay {
  final String day;
  final int dayNum;
  final double score;
  final int logCount;
  final double onTimeRate;
  final List<TopHour> hours;
  TopDay({
    required this.day,
    required this.dayNum,
    required this.score,
    required this.logCount,
    required this.onTimeRate,
    this.hours = const [],
  });
  factory TopDay.fromJson(Map<String, dynamic> json) => TopDay(
    day: json['day'] ?? '',
    dayNum: json['day_num'] ?? 0,
    score: (json['score'] ?? 0).toDouble(),
    logCount: json['log_count'] ?? 0,
    onTimeRate: (json['on_time_rate'] ?? 0).toDouble(),
    hours:
        (json['hours'] as List?)?.map((h) => TopHour.fromJson(h)).toList() ??
        [],
  );
}

class TopHour {
  final int hour;
  final String hourDisplay;
  final double score;
  final double onTimeRate;
  final int logCount;
  TopHour({
    required this.hour,
    required this.hourDisplay,
    required this.score,
    required this.onTimeRate,
    required this.logCount,
  });
  factory TopHour.fromJson(Map<String, dynamic> json) => TopHour(
    hour: json['hour'] ?? 0,
    hourDisplay: json['hour_display'] ?? '',
    score: (json['score'] ?? 0).toDouble(),
    onTimeRate: (json['on_time_rate'] ?? 0).toDouble(),
    logCount: json['log_count'] ?? 0,
  );
}

class Focus {
  final double avgMinutes;
  final int sampleSize;
  Focus({this.avgMinutes = 0, this.sampleSize = 0});
  factory Focus.fromJson(Map<String, dynamic> json) => Focus(
    avgMinutes: (json['avg_minutes'] ?? 0).toDouble(),
    sampleSize: json['sample_size'] ?? 0,
  );
}

class Momentum {
  final String direction;
  final double delta;
  final String label;
  Momentum({this.direction = 'steady', this.delta = 0, this.label = ''});
  factory Momentum.fromJson(Map<String, dynamic> json) => Momentum(
    direction: json['direction'] ?? 'steady',
    delta: (json['delta'] ?? 0).toDouble(),
    label: json['label'] ?? '',
  );
}

class Procrastination {
  final double lateNightRate;
  final double rescheduleRate;
  Procrastination({this.lateNightRate = 0, this.rescheduleRate = 0});
  factory Procrastination.fromJson(Map<String, dynamic> json) =>
      Procrastination(
        lateNightRate: (json['late_night_rate'] ?? 0).toDouble(),
        rescheduleRate: (json['reschedule_rate'] ?? 0).toDouble(),
      );
}

class UnreliableDay {
  final String day;
  final int logCount;
  final int needed;
  UnreliableDay({this.day = '', this.logCount = 0, this.needed = 5});
  factory UnreliableDay.fromJson(Map<String, dynamic> json) => UnreliableDay(
    day: json['day'] ?? '',
    logCount: json['log_count'] ?? 0,
    needed: json['needed'] ?? 5,
  );
}

// ─── HEATMAP ─────────────────────────────────────────────────────────────
class Heatmap {
  final HourRange hourRange;
  final List<HeatmapCell> cells;
  Heatmap({required this.hourRange, this.cells = const []});
  factory Heatmap.fromJson(Map<String, dynamic> json) => Heatmap(
    hourRange: HourRange.fromJson(json['hour_range'] ?? {}),
    cells:
        (json['cells'] as List?)
            ?.map((c) => HeatmapCell.fromJson(c))
            .toList() ??
        [],
  );
}

class HourRange {
  final int start;
  final int end;
  final String startDisplay;
  final String endDisplay;
  HourRange({
    this.start = 6,
    this.end = 23,
    this.startDisplay = '6AM',
    this.endDisplay = '11PM',
  });
  factory HourRange.fromJson(Map<String, dynamic> json) => HourRange(
    start: json['start'] ?? 6,
    end: json['end'] ?? 23,
    startDisplay: json['start_display'] ?? '6AM',
    endDisplay: json['end_display'] ?? '11PM',
  );
}

class HeatmapCell {
  final int day;
  final String dayName;
  final int hour;
  final String hourDisplay;
  final int count;
  final double onTimeRate;
  HeatmapCell({
    this.day = 0,
    this.dayName = '',
    this.hour = 0,
    this.hourDisplay = '',
    this.count = 0,
    this.onTimeRate = 0,
  });
  factory HeatmapCell.fromJson(Map<String, dynamic> json) => HeatmapCell(
    day: json['day'] ?? 0,
    dayName: json['day_name'] ?? '',
    hour: json['hour'] ?? 0,
    hourDisplay: json['hour_display'] ?? '',
    count: json['count'] ?? 0,
    onTimeRate: (json['on_time_rate'] ?? 0).toDouble(),
  );
}

// ─── WORK PATTERNS ─────────────────────────────────────────────────────
class WorkPatterns {
  final List<TimeBucket> timeOfDay;
  final List<PriorityRow> byPriority;
  WorkPatterns({this.timeOfDay = const [], this.byPriority = const []});
  factory WorkPatterns.fromJson(Map<String, dynamic> json) => WorkPatterns(
    timeOfDay:
        (json['time_of_day'] as List?)
            ?.map((t) => TimeBucket.fromJson(t))
            .toList() ??
        [],
    byPriority:
        (json['by_priority'] as List?)
            ?.map((p) => PriorityRow.fromJson(p))
            .toList() ??
        [],
  );
}

class TimeBucket {
  final String key;
  final String label;
  final String rangeDisplay;
  final int count;
  final double percent;
  final double onTimeRate;
  TimeBucket({
    this.key = '',
    this.label = '',
    this.rangeDisplay = '',
    this.count = 0,
    this.percent = 0,
    this.onTimeRate = 0,
  });
  factory TimeBucket.fromJson(Map<String, dynamic> json) => TimeBucket(
    key: json['key'] ?? '',
    label: json['label'] ?? '',
    rangeDisplay: json['range_display'] ?? '',
    count: json['count'] ?? 0,
    percent: (json['percent'] ?? 0).toDouble(),
    onTimeRate: (json['on_time_rate'] ?? 0).toDouble(),
  );
}

class PriorityRow {
  final String priority;
  final String label;
  final int completed;
  final double onTimeRate;
  final double percent;
  final double avgMinutes;
  PriorityRow({
    this.priority = '',
    this.label = '',
    this.completed = 0,
    this.onTimeRate = 0,
    this.percent = 0,
    this.avgMinutes = 0,
  });
  factory PriorityRow.fromJson(Map<String, dynamic> json) => PriorityRow(
    priority: json['priority'] ?? '',
    label: json['label'] ?? '',
    completed: json['completed'] ?? 0,
    onTimeRate: (json['on_time_rate'] ?? 0).toDouble(),
    percent: (json['percent'] ?? 0).toDouble(),
    avgMinutes: (json['avg_minutes'] ?? 0).toDouble(),
  );
}

// ─── NEEDS ATTENTION ──────────────────────────────────────────────────
class NeedsAttention {
  final int overdue;
  final int dueNext7d;
  final List<DueSoonTask> dueSoon;
  final PendingByPriority pendingByPriority;
  NeedsAttention({
    this.overdue = 0,
    this.dueNext7d = 0,
    this.dueSoon = const [],
    required this.pendingByPriority,
  });
  factory NeedsAttention.fromJson(Map<String, dynamic> json) => NeedsAttention(
    overdue: json['overdue'] ?? 0,
    dueNext7d: json['due_next_7d'] ?? 0,
    dueSoon:
        (json['due_soon'] as List?)
            ?.map((t) => DueSoonTask.fromJson(t))
            .toList() ??
        [],
    pendingByPriority: PendingByPriority.fromJson(
      json['pending_by_priority'] ?? {},
    ),
  );
}

class DueSoonTask {
  final String id;
  final String title;
  final String dueDatetime;
  final String priority;
  DueSoonTask({
    this.id = '',
    this.title = '',
    this.dueDatetime = '',
    this.priority = 'medium',
  });
  factory DueSoonTask.fromJson(Map<String, dynamic> json) => DueSoonTask(
    id: json['id'] ?? '',
    title: json['title'] ?? '',
    dueDatetime: json['due_datetime'] ?? '',
    priority: json['priority'] ?? 'medium',
  );
}

class PendingByPriority {
  final int high;
  final int medium;
  final int low;
  PendingByPriority({this.high = 0, this.medium = 0, this.low = 0});
  factory PendingByPriority.fromJson(Map<String, dynamic> json) =>
      PendingByPriority(
        high: json['high'] ?? 0,
        medium: json['medium'] ?? 0,
        low: json['low'] ?? 0,
      );
}

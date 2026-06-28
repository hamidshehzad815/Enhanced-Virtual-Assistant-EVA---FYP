class ScheduleDatesResponse {
  final String timezone;
  final String goalId;
  final String scheduleId;
  final String scheduleLabel;
  final List<WeekdaySlot> weekdays;
  final Range range;
  final List<ScheduleDate> dates;

  ScheduleDatesResponse({
    required this.timezone,
    required this.goalId,
    required this.scheduleId,
    required this.scheduleLabel,
    required this.weekdays,
    required this.range,
    required this.dates,
  });

  factory ScheduleDatesResponse.fromJson(Map<String, dynamic> json) {
    return ScheduleDatesResponse(
      timezone: json['timezone'],
      goalId: json['goal_id'],
      scheduleId: json['schedule_id'],
      scheduleLabel: json['schedule_label'],
      weekdays: (json['weekdays'] as List)
          .map((w) => WeekdaySlot.fromJson(w))
          .toList(),
      range: Range.fromJson(json['range']),
      dates: (json['dates'] as List)
          .map((d) => ScheduleDate.fromJson(d))
          .toList(),
    );
  }
}

class WeekdaySlot {
  final int day;
  final String dayLabel;
  final String time;
  final int durationMinutes;

  WeekdaySlot({required this.day, required this.dayLabel, required this.time, required this.durationMinutes});

  factory WeekdaySlot.fromJson(Map<String, dynamic> json) {
    return WeekdaySlot(
      day: json['day'],
      dayLabel: json['day_label'],
      time: json['time'],
      durationMinutes: json['duration_minutes'],
    );
  }
}

class Range {
  final String from;
  final String to;

  Range({required this.from, required this.to});

  factory Range.fromJson(Map<String, dynamic> json) {
    return Range(from: json['from'], to: json['to']);
  }
}

class ScheduleDate {
  final String date; // YYYY-MM-DD
  final int day;
  final String dayLabel;
  final String time;
  final int durationMinutes;
  final String scheduledDatetime; // ISO with offset

  ScheduleDate({
    required this.date,
    required this.day,
    required this.dayLabel,
    required this.time,
    required this.durationMinutes,
    required this.scheduledDatetime,
  });

  factory ScheduleDate.fromJson(Map<String, dynamic> json) {
    return ScheduleDate(
      date: json['date'],
      day: json['day'],
      dayLabel: json['day_label'],
      time: json['time'],
      durationMinutes: json['duration_minutes'],
      scheduledDatetime: json['scheduled_datetime'],
    );
  }
}
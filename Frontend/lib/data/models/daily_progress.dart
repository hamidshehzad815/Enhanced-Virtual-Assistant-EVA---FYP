class DailyProgress {
  final int completedTasks;
  final int totalTasks;
  final int completionPercentage;

  DailyProgress({
    required this.completedTasks,
    required this.totalTasks,
    required this.completionPercentage,
  });

  factory DailyProgress.fromJson(
    Map<String, dynamic> json,
  ) {
    return DailyProgress(
      completedTasks:
          json['completed_tasks'] ?? 0,
      totalTasks:
          json['total_tasks'] ?? 0,
      completionPercentage:
          json['completion_percentage'] ?? 0,
    );
  }
}
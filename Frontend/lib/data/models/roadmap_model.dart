import 'collaborator.dart';

export 'collaborator.dart';

// ── Language option for dropdown (still used in PlansScreen?) ──
class LanguageOption {
  final String key;
  final String label;

  LanguageOption({required this.key, required this.label});

  factory LanguageOption.fromJson(Map<String, dynamic> json) {
    return LanguageOption(key: json['key'], label: json['label']);
  }
}

// ── Sessions summary ──
class SessionsSummary {
  final int completed;
  final int skipped;
  final int pending;
  final int ongoing;

  SessionsSummary({
    this.completed = 0,
    this.skipped = 0,
    this.pending = 0,
    this.ongoing = 0,
  });

  factory SessionsSummary.fromJson(Map<String, dynamic> json) {
    return SessionsSummary(
      completed: json['completed'] ?? 0,
      skipped: json['skipped'] ?? 0,
      pending: json['pending'] ?? 0,
      ongoing: json['ongoing'] ?? 0,
    );
  }

  Map<String, dynamic> toJson() => {
        'completed': completed,
        'skipped': skipped,
        'pending': pending,
        'ongoing': ongoing,
      };
}

// ── Plan summary (from GET /api/roadmaps/plans) ──
class PlanSummary {
  final String id;
  final String title;
  final String language;
  final String languageKey;
  final String trackLabel;
  final String status; // active, paused, completed, cancelled
  final DateTime startDate;
  final DateTime endDate;
  final int completedTopics;
  final int totalTopics;
  final double progressPercent;
  final int sessionCount;
  final SessionsSummary summary;
  final List<Collaborator> collaborators;

  PlanSummary({
    required this.id,
    required this.title,
    required this.language,
    required this.languageKey,
    required this.trackLabel,
    required this.status,
    required this.startDate,
    required this.endDate,
    required this.completedTopics,
    required this.totalTopics,
    required this.progressPercent,
    required this.sessionCount,
    required this.summary,
    this.collaborators = const [],
  });

  factory PlanSummary.fromJson(Map<String, dynamic> json) {
    return PlanSummary(
      id: json['id'],
      title: json['title'],
      language: json['language'],
      languageKey: json['language_key'],
      trackLabel: json['track_label'] ?? '',
      status: json['status'],
      startDate: DateTime.parse(json['start_date']),
      endDate: DateTime.parse(json['end_date']),
      completedTopics: json['completed_topics'] ?? 0,
      totalTopics: json['total_topics'] ?? 0,
      progressPercent: (json['progress_percent'] ?? 0).toDouble(),
      sessionCount: json['session_count'] ?? 0,
      summary: SessionsSummary.fromJson(json['sessions_summary'] ?? {}),
      collaborators: Collaborator.listFromJson(json['collaborators']),
    );
  }
}

// ── Roadmap detail (from GET /api/roadmaps/:goalId) ──
class RoadmapDetail {
  final String id;
  final String title;
  final String language;
  final String languageKey;
  final String trackLabel;
  final String status;
  final DateTime startDate;
  final DateTime endDate;
  final int completedTopics;
  final int totalTopics;
  final double progressPercent;
  final int sessionCount;
  final SessionsSummary summary;
  final List<Session> sessions;
  final List<Collaborator> collaborators;

  RoadmapDetail({
    required this.id,
    required this.title,
    required this.language,
    required this.languageKey,
    required this.trackLabel,
    required this.status,
    required this.startDate,
    required this.endDate,
    required this.completedTopics,
    required this.totalTopics,
    required this.progressPercent,
    required this.sessionCount,
    required this.summary,
    required this.sessions,
    this.collaborators = const [],
  });

  factory RoadmapDetail.fromJson(Map<String, dynamic> json) {
    return RoadmapDetail(
      id: json['id'],
      title: json['title'],
      language: json['language'],
      languageKey: json['language_key'],
      trackLabel: json['track_label'] ?? '',
      status: json['status'],
      startDate: DateTime.parse(json['start_date']),
      endDate: DateTime.parse(json['end_date']),
      completedTopics: json['completed_topics'] ?? 0,
      totalTopics: json['total_topics'] ?? 0,
      progressPercent: (json['progress_percent'] ?? 0).toDouble(),
      sessionCount: json['session_count'] ?? 0,
      summary: SessionsSummary.fromJson(json['sessions_summary'] ?? {}),
      sessions: (json['sessions'] as List?)
              ?.map((s) => Session.fromJson(s))
              .toList() ??
          [],
      collaborators: Collaborator.listFromJson(json['collaborators']),
    );
  }
}

// ── Session (topic) ──
class Session {
  final String id;
  final int order;
  final String title;
  final String status; // pending, ongoing, completed, skipped
  final DateTime? scheduledDate;
  final int estimatedDuration; // minutes
  final List<Resource> resources;
  final String sessionState; // locked, unlocked_future, ongoing, overdue, completed, skipped, upcoming
  final bool isCurrent;
  final DateTime? unlockAt;
  final DateTime? completedAt;

  /// Per-collaborator status on this session (who has reached / finished it).
  final List<SessionCollaboratorStatus> collaboratorProgress;

  Session({
    required this.id,
    required this.order,
    required this.title,
    required this.status,
    this.scheduledDate,
    required this.estimatedDuration,
    this.resources = const [],
    required this.sessionState,
    this.isCurrent = false,
    this.unlockAt,
    this.completedAt,
    this.collaboratorProgress = const [],
  });

  factory Session.fromJson(Map<String, dynamic> json) {
    return Session(
      id: json['id'],
      order: json['order'] ?? 0,
      title: json['title'],
      status: json['status'] ?? 'pending',
      scheduledDate: json['scheduled_date'] != null
          ? DateTime.parse(json['scheduled_date'])
          : null,
      estimatedDuration: json['estimated_duration'] ?? 90,
      resources: (json['resources'] as List?)
              ?.map((r) => Resource.fromJson(r))
              .toList() ??
          [],
      sessionState: json['session_state'] ?? 'upcoming',
      isCurrent: json['is_current'] ?? false,
      unlockAt: json['unlock_at'] != null
          ? DateTime.parse(json['unlock_at'])
          : null,
      completedAt: json['completed_at'] != null
          ? DateTime.parse(json['completed_at'])
          : null,
      collaboratorProgress:
          SessionCollaboratorStatus.listFromJson(json['collaborator_progress']),
    );
  }
}

// ── Resource ──
class Resource {
  final String title;
  final String url;
  final String? thumbnail;
  final String? channelName;

  Resource({
    required this.title,
    required this.url,
    this.thumbnail,
    this.channelName,
  });

  factory Resource.fromJson(Map<String, dynamic> json) {
    return Resource(
      title: json['title'],
      url: json['url'],
      thumbnail: json['thumbnail'],
      channelName: json['channel_name'],
    );
  }
}
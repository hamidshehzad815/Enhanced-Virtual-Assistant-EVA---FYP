// Collaborator models shared by tasks and roadmaps.
//
// Backend shape (see tasks-api.md / roadmaps-api.md):
//   { user: { _id, name, username, profile_picture }, status, progress? }
//
// `progress` is only present on roadmap collaborators once they've accepted.

enum CollaboratorStatus { pending, accepted, rejected }

CollaboratorStatus _statusFromApi(dynamic value) {
  switch (value?.toString().toLowerCase()) {
    case 'accepted':
      return CollaboratorStatus.accepted;
    case 'rejected':
      return CollaboratorStatus.rejected;
    default:
      return CollaboratorStatus.pending;
  }
}

class CollaboratorUser {
  final String id;
  final String name;
  final String username;
  final String? profilePicture;

  const CollaboratorUser({
    required this.id,
    required this.name,
    required this.username,
    this.profilePicture,
  });

  factory CollaboratorUser.fromJson(Map<String, dynamic> json) {
    return CollaboratorUser(
      id: (json['_id'] ?? json['id'] ?? '').toString(),
      name: (json['name'] ?? '').toString(),
      username: (json['username'] ?? '').toString(),
      profilePicture: json['profile_picture'] as String?,
    );
  }

  /// Two-letter initials for the avatar fallback.
  String get initials {
    final source = name.trim().isNotEmpty ? name.trim() : username.trim();
    if (source.isEmpty) return '?';
    final parts = source.split(RegExp(r'\s+'));
    if (parts.length >= 2 && parts[0].isNotEmpty && parts[1].isNotEmpty) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return source[0].toUpperCase();
  }
}

/// A collaborator's overall progress on a shared roadmap plan.
class CollaboratorProgress {
  final int completedTopics;
  final int totalTopics;
  final double progressPercent;

  /// Session `order` they're currently on; null when they've finished.
  final int? currentOrder;

  /// Their plan status: active, completed, paused, cancelled.
  final String planStatus;

  const CollaboratorProgress({
    required this.completedTopics,
    required this.totalTopics,
    required this.progressPercent,
    required this.currentOrder,
    required this.planStatus,
  });

  bool get isFinished =>
      planStatus == 'completed' ||
      (totalTopics > 0 && completedTopics >= totalTopics);

  bool get isPaused => planStatus == 'paused';
  bool get isCancelled => planStatus == 'cancelled';
  bool get isDeleted => planStatus == 'deleted';

  /// True when the participant is no longer actively working the plan.
  bool get isInactive => isPaused || isCancelled || isDeleted;

  factory CollaboratorProgress.fromJson(Map<String, dynamic> json) {
    return CollaboratorProgress(
      completedTopics: json['completed_topics'] ?? 0,
      totalTopics: json['total_topics'] ?? 0,
      progressPercent: (json['progress_percent'] ?? 0).toDouble(),
      currentOrder: json['current_order'] as int?,
      planStatus: (json['plan_status'] ?? 'active').toString(),
    );
  }
}

class Collaborator {
  final CollaboratorUser user;
  final CollaboratorStatus status;
  final CollaboratorProgress? progress;

  /// True when this participant is the plan/task owner (shown to collaborators).
  final bool isOwner;

  const Collaborator({
    required this.user,
    required this.status,
    this.progress,
    this.isOwner = false,
  });

  bool get isAccepted => status == CollaboratorStatus.accepted;
  bool get isPending => status == CollaboratorStatus.pending;
  bool get isRejected => status == CollaboratorStatus.rejected;

  factory Collaborator.fromJson(Map<String, dynamic> json) {
    return Collaborator(
      user: CollaboratorUser.fromJson(
        (json['user'] as Map?)?.cast<String, dynamic>() ?? const {},
      ),
      status: _statusFromApi(json['status']),
      isOwner: json['is_owner'] == true,
      progress: json['progress'] != null
          ? CollaboratorProgress.fromJson(
              (json['progress'] as Map).cast<String, dynamic>(),
            )
          : null,
    );
  }

  static List<Collaborator> listFromJson(dynamic raw) {
    if (raw is! List) return const [];
    return raw
        .whereType<Map>()
        .map((e) => Collaborator.fromJson(e.cast<String, dynamic>()))
        // Rejected collaborators are hidden from the UI (per issue #43).
        .where((c) => !c.isRejected)
        .toList();
  }
}

/// A collaborator's status on one specific roadmap session.
/// Session status enum: pending | ongoing | completed | skipped.
class SessionCollaboratorStatus {
  final String userId;
  final String status;

  const SessionCollaboratorStatus({required this.userId, required this.status});

  bool get isCompleted => status == 'completed';

  factory SessionCollaboratorStatus.fromJson(Map<String, dynamic> json) {
    return SessionCollaboratorStatus(
      userId: (json['user_id'] ?? '').toString(),
      status: (json['status'] ?? 'pending').toString(),
    );
  }

  static List<SessionCollaboratorStatus> listFromJson(dynamic raw) {
    if (raw is! List) return const [];
    return raw
        .whereType<Map>()
        .map((e) => SessionCollaboratorStatus.fromJson(e.cast<String, dynamic>()))
        .toList();
  }
}

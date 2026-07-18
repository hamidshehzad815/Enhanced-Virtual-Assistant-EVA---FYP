import 'package:flutter/material.dart';
import '../../core/theme/app_colours.dart';
import '../../data/models/collaborator.dart';

/// Shared UI for showing collaborators (issue #43): avatars with initials
/// fallback, invite-status styling, an overlapping stack for compact spots,
/// and a progress tile for the roadmap header.

Color collaboratorStatusColor(CollaboratorStatus status) {
  switch (status) {
    case CollaboratorStatus.accepted:
      return const Color(0xFF16A34A); // green
    case CollaboratorStatus.pending:
      return AppColors.primary; // amber
    case CollaboratorStatus.rejected:
      return Colors.grey;
  }
}

String collaboratorStatusLabel(CollaboratorStatus status) {
  switch (status) {
    case CollaboratorStatus.accepted:
      return 'Accepted';
    case CollaboratorStatus.pending:
      return 'Invited';
    case CollaboratorStatus.rejected:
      return 'Declined';
  }
}

/// Badge colour/label for a participant — the owner gets a distinct treatment.
Color collaboratorBadgeColor(Collaborator c) =>
    c.isOwner ? AppColors.primary : collaboratorStatusColor(c.status);

String collaboratorBadgeLabel(Collaborator c) =>
    c.isOwner ? 'Owner' : collaboratorStatusLabel(c.status);

/// A single circular avatar with network image + initials fallback.
/// Pending collaborators render dimmed with a status ring; accepted show a
/// small check badge.
class CollaboratorAvatar extends StatelessWidget {
  final Collaborator collaborator;
  final double radius;
  final bool showStatusRing;
  final bool showBadge;
  final Color? borderColor;

  const CollaboratorAvatar({
    super.key,
    required this.collaborator,
    this.radius = 16,
    this.showStatusRing = true,
    this.showBadge = false,
    this.borderColor,
  });

  @override
  Widget build(BuildContext context) {
    final user = collaborator.user;
    final statusColor = collaboratorStatusColor(collaborator.status);
    final dimmed = collaborator.isPending;
    final ringColor = borderColor ??
        (showStatusRing
            ? statusColor
            : Theme.of(context).scaffoldBackgroundColor);

    final pic = user.profilePicture;
    final hasImage = pic != null && pic.isNotEmpty;

    Widget avatar = CircleAvatar(
      radius: radius,
      backgroundColor: AppColors.primary,
      child: hasImage
          ? ClipOval(
              child: Image.network(
                pic,
                fit: BoxFit.cover,
                width: radius * 2,
                height: radius * 2,
                errorBuilder: (_, __, ___) => _initials(),
              ),
            )
          : _initials(),
    );

    if (dimmed) {
      avatar = Opacity(opacity: 0.55, child: avatar);
    }

    return Container(
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(color: ringColor, width: 2),
      ),
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Padding(padding: const EdgeInsets.all(1), child: avatar),
          if (showBadge)
            Positioned(
              right: -2,
              bottom: -2,
              child: _StatusBadge(status: collaborator.status),
            ),
        ],
      ),
    );
  }

  Widget _initials() {
    return Center(
      child: Text(
        collaborator.user.initials,
        style: TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.bold,
          fontSize: radius * 0.8,
        ),
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  final CollaboratorStatus status;
  const _StatusBadge({required this.status});

  @override
  Widget build(BuildContext context) {
    final color = collaboratorStatusColor(status);
    final icon = status == CollaboratorStatus.accepted
        ? Icons.check
        : Icons.schedule;
    return Container(
      padding: const EdgeInsets.all(2),
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        border: Border.all(
          color: Theme.of(context).scaffoldBackgroundColor,
          width: 1.5,
        ),
      ),
      child: Icon(icon, size: 9, color: Colors.white),
    );
  }
}

/// Overlapping row of avatars with a "+N" overflow chip. Compact — for cards.
class CollaboratorAvatarStack extends StatelessWidget {
  final List<Collaborator> collaborators;
  final double radius;
  final int maxVisible;

  const CollaboratorAvatarStack({
    super.key,
    required this.collaborators,
    this.radius = 14,
    this.maxVisible = 3,
  });

  @override
  Widget build(BuildContext context) {
    if (collaborators.isEmpty) return const SizedBox.shrink();

    final visible = collaborators.take(maxVisible).toList();
    final overflow = collaborators.length - visible.length;
    final overlap = radius * 1.15;

    final children = <Widget>[];
    for (var i = 0; i < visible.length; i++) {
      children.add(Padding(
        padding: EdgeInsets.only(left: i == 0 ? 0 : overlap),
        child: CollaboratorAvatar(
          collaborator: visible[i],
          radius: radius,
          showStatusRing: true,
        ),
      ));
    }
    if (overflow > 0) {
      children.add(Padding(
        padding: EdgeInsets.only(left: overlap),
        child: CircleAvatar(
          radius: radius,
          backgroundColor: Theme.of(context).cardColor,
          child: Text(
            '+$overflow',
            style: TextStyle(
              fontSize: radius * 0.7,
              fontWeight: FontWeight.w700,
              color: Theme.of(context).hintColor,
            ),
          ),
        ),
      ));
    }

    return Row(mainAxisSize: MainAxisSize.min, children: children);
  }
}

/// "Shared with" label + avatar stack, for task cards / detail rows.
class CollaboratorSummaryRow extends StatelessWidget {
  final List<Collaborator> collaborators;
  final String label;

  const CollaboratorSummaryRow({
    super.key,
    required this.collaborators,
    this.label = 'Shared with',
  });

  @override
  Widget build(BuildContext context) {
    if (collaborators.isEmpty) return const SizedBox.shrink();

    final names = collaborators
        .map((c) => c.user.name.isNotEmpty ? c.user.name : '@${c.user.username}')
        .join(', ');
    final anyPending = collaborators.any((c) => c.isPending);

    return Row(
      children: [
        Icon(Icons.group_outlined, size: 15, color: Theme.of(context).hintColor),
        const SizedBox(width: 6),
        CollaboratorAvatarStack(collaborators: collaborators, radius: 12),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            anyPending ? '$names · invited' : names,
            style: TextStyle(
              fontSize: 11.5,
              color: Theme.of(context).hintColor,
              fontWeight: FontWeight.w500,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
}

/// Rich per-collaborator tile with progress — for the roadmap header.
class CollaboratorProgressTile extends StatelessWidget {
  final Collaborator collaborator;
  final int totalSessions;

  const CollaboratorProgressTile({
    super.key,
    required this.collaborator,
    required this.totalSessions,
  });

  @override
  Widget build(BuildContext context) {
    final progress = collaborator.progress;
    final statusColor = collaboratorBadgeColor(collaborator);
    final name = collaborator.user.name.isNotEmpty
        ? collaborator.user.name
        : '@${collaborator.user.username}';

    String subtitle;
    double? fraction;
    if (collaborator.isPending) {
      subtitle = 'Invited — hasn\'t joined yet';
    } else if (progress == null) {
      subtitle = collaborator.isOwner ? 'Owns this roadmap' : 'Accepted';
    } else if (progress.isFinished) {
      subtitle = 'Finished the roadmap 🎉';
      fraction = 1.0;
    } else {
      final reached = progress.currentOrder;
      final total = progress.totalTopics > 0 ? progress.totalTopics : totalSessions;
      fraction = total > 0 ? progress.completedTopics / total : 0.0;
      subtitle = reached != null
          ? '${progress.completedTopics}/$total done · on session $reached'
          : '${progress.completedTopics}/$total sessions done';
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          CollaboratorAvatar(
            collaborator: collaborator,
            radius: 18,
            showBadge: true,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Flexible(
                      child: Text(
                        name,
                        style: const TextStyle(
                          fontSize: 13.5,
                          fontWeight: FontWeight.w700,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Container(
                      padding:
                          const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                      decoration: BoxDecoration(
                        color: statusColor.withValues(alpha: 0.14),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        collaboratorBadgeLabel(collaborator),
                        style: TextStyle(
                          fontSize: 9.5,
                          fontWeight: FontWeight.w700,
                          color: statusColor,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 3),
                Text(
                  subtitle,
                  style: TextStyle(
                    fontSize: 11,
                    color: Theme.of(context).hintColor,
                  ),
                ),
                if (fraction != null) ...[
                  const SizedBox(height: 5),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: fraction.clamp(0.0, 1.0),
                      minHeight: 5,
                      backgroundColor:
                          Theme.of(context).hintColor.withValues(alpha: 0.15),
                      valueColor: AlwaysStoppedAnimation(
                        progress?.isFinished == true
                            ? const Color(0xFF16A34A)
                            : AppColors.primary,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

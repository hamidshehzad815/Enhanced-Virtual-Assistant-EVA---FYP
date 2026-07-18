// lib/presentation/widgets/notification_bell.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colours.dart';
import '../../data/models/app_notification.dart';
import '../providers/notification_viewmodel.dart';
import '../providers/task_refresh_notifier.dart';

/// Dashboard bell icon with an unread badge. Tapping opens the notifications
/// panel (list + Accept/Reject for collaboration invites).
class NotificationBell extends StatelessWidget {
  const NotificationBell({super.key});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final unread = context.watch<NotificationViewModel>().unreadCount;

    return GestureDetector(
      onTap: () => _openPanel(context),
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: isDark ? AppColors.cardElevatedDark : Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: isDark ? AppColors.borderDark : AppColors.borderLight,
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
          if (unread > 0)
            Positioned(
              right: -3,
              top: -3,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                constraints: const BoxConstraints(minWidth: 18, minHeight: 18),
                decoration: BoxDecoration(
                  color: Colors.red,
                  borderRadius: BorderRadius.circular(9),
                  border: Border.all(
                    color: isDark ? AppColors.scaffoldColorDark : Colors.white,
                    width: 1.5,
                  ),
                ),
                child: Text(
                  unread > 99 ? '99+' : '$unread',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  void _openPanel(BuildContext context) {
    final vm = context.read<NotificationViewModel>();
    vm.loadNotifications();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => ChangeNotifierProvider<NotificationViewModel>.value(
        value: vm,
        child: const _NotificationPanel(),
      ),
    );
  }
}

class _NotificationPanel extends StatelessWidget {
  const _NotificationPanel();

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final vm = context.watch<NotificationViewModel>();
    final hasUnread = vm.notifications.any((n) => !n.isRead);

    return Container(
      constraints: BoxConstraints(
        maxHeight: MediaQuery.of(context).size.height * 0.8,
      ),
      decoration: BoxDecoration(
        color: isDark ? AppColors.cardDark : Colors.white,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            margin: const EdgeInsets.only(top: 12),
            width: 40,
            height: 4,
            decoration: BoxDecoration(
              color: isDark ? AppColors.borderDark : AppColors.borderLight,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 14, 8, 6),
            child: Row(
              children: [
                Text(
                  'Notifications',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: isDark
                        ? AppColors.primaryTextDark
                        : AppColors.primaryTextLight,
                  ),
                ),
                const Spacer(),
                if (hasUnread)
                  TextButton(
                    onPressed: () => vm.markAllRead(),
                    child: const Text('Mark all read'),
                  ),
                IconButton(
                  icon: Icon(
                    Icons.close,
                    color: isDark
                        ? AppColors.secondaryTextDark
                        : AppColors.secondaryTextLight,
                  ),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
          ),
          Flexible(child: _buildBody(context, vm)),
          const SizedBox(height: 8),
        ],
      ),
    );
  }

  Widget _buildBody(BuildContext context, NotificationViewModel vm) {
    if (vm.isLoading && vm.notifications.isEmpty) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 50),
        child: Center(child: CircularProgressIndicator()),
      );
    }

    if (vm.error != null && vm.notifications.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 40, horizontal: 24),
        child: Column(
          children: [
            const Icon(Icons.wifi_off, size: 44, color: Colors.grey),
            const SizedBox(height: 10),
            const Text(
              'Could not load notifications',
              style: TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 6),
            TextButton(
              onPressed: () => vm.loadNotifications(),
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (vm.notifications.isEmpty) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 56),
        child: Column(
          children: [
            Icon(Icons.notifications_none, size: 48, color: Colors.grey),
            SizedBox(height: 12),
            Text('No notifications yet', style: TextStyle(color: Colors.grey)),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () => vm.loadNotifications(),
      child: ListView.separated(
        shrinkWrap: true,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        itemCount: vm.notifications.length,
        separatorBuilder: (_, __) => const Divider(height: 1),
        itemBuilder: (_, i) =>
            _NotificationTile(notification: vm.notifications[i]),
      ),
    );
  }
}

class _NotificationTile extends StatefulWidget {
  final AppNotification notification;
  const _NotificationTile({required this.notification});

  @override
  State<_NotificationTile> createState() => _NotificationTileState();
}

class _NotificationTileState extends State<_NotificationTile> {
  bool _busy = false;

  Future<void> _respond(String action) async {
    final vm = context.read<NotificationViewModel>();
    final messenger = ScaffoldMessenger.of(context);
    setState(() => _busy = true);
    try {
      final result = await vm.respondToInvite(widget.notification, action);
      if (action == 'accept' && (result == 'accepted' || result == 'already')) {
        // Cloned task / learning sessions must appear on collaborator calendar.
        context.read<TaskRefreshNotifier>().refresh();
      }
      final msg = result == 'already'
          ? 'Invite already handled.'
          : result == 'accepted'
              ? 'Invite accepted.'
              : 'Invite rejected.';
      messenger.showSnackBar(SnackBar(content: Text(msg)));
    } catch (e) {
      messenger.showSnackBar(
        SnackBar(
          content: Text(
            'Failed: ${e.toString().replaceAll('Exception: ', '')}',
          ),
        ),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _deleteNotification() async {
    final vm = context.read<NotificationViewModel>();
    final messenger = ScaffoldMessenger.of(context);
    try {
      await vm.deleteNotification(widget.notification.id);
    } catch (e) {
      if (!mounted) return;
      messenger.showSnackBar(
        SnackBar(
          content: Text(
            'Failed to delete notification: ${e.toString().replaceAll('Exception: ', '')}',
          ),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final n = widget.notification;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final primaryText =
        isDark ? AppColors.primaryTextDark : AppColors.primaryTextLight;

    return Dismissible(
      key: ValueKey(n.id),
      direction: DismissDirection.endToStart,
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.symmetric(horizontal: 20),
        decoration: const BoxDecoration(color: Colors.red),
        child: const Icon(Icons.delete_outline, color: Colors.white, size: 24),
      ),
      onDismissed: (_) => _deleteNotification(),
      child: InkWell(
        onTap: n.isRead
            ? null
            : () => context.read<NotificationViewModel>().markRead(n.id),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 12),
          child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 8,
                  height: 8,
                  margin: const EdgeInsets.only(top: 6, right: 10),
                  decoration: BoxDecoration(
                    color: n.isRead ? Colors.transparent : AppColors.primary,
                    shape: BoxShape.circle,
                  ),
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        n.title,
                        style: TextStyle(
                          fontWeight:
                              n.isRead ? FontWeight.w500 : FontWeight.w700,
                          fontSize: 14,
                          color: primaryText,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        n.message,
                        style: const TextStyle(
                          fontSize: 13,
                          color: Colors.grey,
                        ),
                      ),
                      if (n.actionTaken != null) ...[
                        const SizedBox(height: 4),
                        Text(
                          'You ${n.actionTaken} this invite',
                          style: const TextStyle(
                            fontSize: 12,
                            fontStyle: FontStyle.italic,
                            color: Colors.grey,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
            if (n.canRespond) ...[
              const SizedBox(height: 10),
              Padding(
                padding: const EdgeInsets.only(left: 18),
                child: _busy
                    ? const Center(
                        child: SizedBox(
                          height: 22,
                          width: 22,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        ),
                      )
                    : Row(
                        children: [
                          Expanded(
                            child: ElevatedButton(
                              onPressed: () => _respond('accept'),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: const Color(0xFF16A34A),
                                padding:
                                    const EdgeInsets.symmetric(vertical: 10),
                              ),
                              child: const Text('Accept'),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: OutlinedButton(
                              onPressed: () => _respond('reject'),
                              style: OutlinedButton.styleFrom(
                                foregroundColor: Colors.red,
                                side: const BorderSide(color: Colors.red),
                                padding:
                                    const EdgeInsets.symmetric(vertical: 10),
                              ),
                              child: const Text('Reject'),
                            ),
                          ),
                        ],
                      ),
              ),
            ],
          ],
          ),
        ),
      ),
    );
  }
}

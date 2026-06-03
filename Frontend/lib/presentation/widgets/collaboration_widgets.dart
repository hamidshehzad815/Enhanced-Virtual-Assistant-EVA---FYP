import 'package:flutter/material.dart';
import '../../core/theme/app_text_style.dart';
import '../../data/models/collaboration_conversation.dart';
import 'package:go_router/go_router.dart';

class CollaborationSearchBar extends StatelessWidget {
  final TextEditingController controller;
  const CollaborationSearchBar({required this.controller, super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final hintColor = theme.hintColor;

    return Container(
      decoration: BoxDecoration(
        color: theme.cardColor,
        borderRadius: BorderRadius.circular(50),
        border: Border.all(color: theme.dividerColor),
      ),
      child: TextField(
        controller: controller,
        style: theme.textTheme.bodyMedium,
        decoration: InputDecoration(
          hintText: 'Search friend by username…',
          hintStyle: theme.inputDecorationTheme.hintStyle,
          border: InputBorder.none,
          enabledBorder: InputBorder.none,
          focusedBorder: InputBorder.none,
          prefixIcon: Icon(Icons.search_rounded, size: 18, color: hintColor),
          contentPadding: const EdgeInsets.symmetric(vertical: 12),
          isDense: true,
        ),
      ),
    );
  }
}

class ProfileQuoteRow extends StatelessWidget {
  final String quote;
  final VoidCallback onEditQuote;
  const ProfileQuoteRow({
    required this.quote,
    required this.onEditQuote,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final primaryColor = theme.colorScheme.primary;

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      child: IntrinsicHeight(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Container(
              width: 82,
              decoration: BoxDecoration(
                color: theme.cardColor,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: theme.dividerColor),
              ),
              padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 8),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircleAvatar(
                    radius: 24,
                    backgroundColor: primaryColor,
                    child: Text(
                      'YP',
                      style: theme.textTheme.titleSmall?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text('YOU', style: theme.textTheme.labelLarge),
                ],
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: GestureDetector(
                onTap: onEditQuote,
                child: Container(
                  decoration: BoxDecoration(
                    color: theme.cardColor,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: theme.dividerColor),
                  ),
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Row(
                        children: [
                          Text(
                            'QUOTE OF THE DAY',
                            style: theme.textTheme.labelLarge?.copyWith(
                              color: primaryColor,
                            ),
                          ),
                          const Spacer(),
                          Icon(
                            Icons.edit_outlined,
                            size: 14,
                            color: primaryColor,
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        quote,
                        style: AppTextStyles.titleMedium.copyWith(
                          fontSize: 13,
                          fontStyle: FontStyle.italic,
                          height: 1.5,
                          color: theme.textTheme.bodyMedium?.color,
                        ),
                        maxLines: 3,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class EditQuoteSheet extends StatelessWidget {
  final TextEditingController controller;
  final ValueChanged<String> onSave;
  const EditQuoteSheet({
    required this.controller,
    required this.onSave,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final primaryColor = theme.colorScheme.primary;

    return Padding(
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 24,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: theme.dividerColor,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 20),
          Text('Edit your quote', style: theme.textTheme.titleMedium),
          const SizedBox(height: 4),
          Text(
            'Tap save to update the quote of the day.',
            style: theme.textTheme.bodySmall,
          ),
          const SizedBox(height: 16),
          TextField(
            controller: controller,
            maxLines: 4,
            style: AppTextStyles.titleMedium.copyWith(
              fontSize: 14,
              fontStyle: FontStyle.italic,
              color: theme.textTheme.bodyMedium?.color,
            ),
            decoration: InputDecoration(
              hintText: 'Enter an inspiring quote…',
              hintStyle: theme.inputDecorationTheme.hintStyle,
              filled: true,
              fillColor: theme.cardColor,
              enabledBorder: theme.inputDecorationTheme.enabledBorder,
              focusedBorder: theme.inputDecorationTheme.focusedBorder,
              contentPadding: const EdgeInsets.all(14),
            ),
          ),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: () {
              onSave(controller.text);
              Navigator.pop(context);
            },
            style: ElevatedButton.styleFrom(backgroundColor: primaryColor),
            child: Text(
              'Save quote',
              style: theme.textTheme.titleSmall?.copyWith(color: Colors.white),
            ),
          ),
        ],
      ),
    );
  }
}

class MessagesSection extends StatelessWidget {
  final List<ConversationModel> conversations;
  final ValueChanged<ConversationModel> onConversationTap;
  const MessagesSection({
    required this.conversations,
    required this.onConversationTap,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final primaryColor = theme.colorScheme.primary;

    return Container(
      decoration: BoxDecoration(
        color: theme.scaffoldBackgroundColor,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 10),
            child: Row(
              children: [
                Text('Messages', style: theme.textTheme.titleSmall),
                const Spacer(),
                Stack(
                  children: [
                    Container(
                      width: 36,
                      height: 36,
                      decoration: BoxDecoration(
                        color: theme.cardColor,
                        shape: BoxShape.circle,
                      ),
                      child: Icon(
                        Icons.notifications_none_rounded,
                        size: 20,
                        color: theme.textTheme.bodyMedium?.color,
                      ),
                    ),
                    Positioned(
                      top: 7,
                      right: 7,
                      child: Container(
                        width: 8,
                        height: 8,
                        decoration: BoxDecoration(
                          color: primaryColor,
                          shape: BoxShape.circle,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          Expanded(
            child: ListView.separated(
              padding: const EdgeInsets.fromLTRB(12, 0, 12, 24),
              itemCount: conversations.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (ctx, i) => ConversationTile(
                conversation: conversations[i],
                onTap: () => onConversationTap(conversations[i]),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class ConversationTile extends StatelessWidget {
  final ConversationModel conversation;
  final VoidCallback onTap;
  const ConversationTile({
    required this.conversation,
    required this.onTap,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final primaryColor = theme.colorScheme.primary;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: theme.cardColor,
          borderRadius: BorderRadius.circular(16),
          border: Border(
            left: conversation.hasUnread
                ? BorderSide(color: primaryColor, width: 3)
                : BorderSide.none,
            top: BorderSide(color: theme.dividerColor, width: 0.5),
            right: BorderSide(color: theme.dividerColor, width: 0.5),
            bottom: BorderSide(color: theme.dividerColor, width: 0.5),
          ),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: Row(
          children: [
            CircleAvatar(
              radius: 22,
              backgroundColor: conversation.avatarColor,
              child: Text(
                conversation.avatarInitials,
                style: theme.textTheme.titleSmall?.copyWith(
                  color: Colors.white,
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          conversation.displayName,
                          style: theme.textTheme.titleSmall,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        conversation.timestamp,
                        style: theme.textTheme.bodySmall?.copyWith(
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 3),
                  Text(
                    conversation.lastMessage,
                    style: theme.textTheme.bodySmall?.copyWith(fontSize: 12),
                    overflow: TextOverflow.ellipsis,
                    maxLines: 1,
                  ),
                ],
              ),
            ),
            if (conversation.hasUnread) ...[
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: primaryColor,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  conversation.unreadCount.toString(),
                  style: theme.textTheme.labelLarge?.copyWith(
                    color: Colors.white,
                    fontSize: 11,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class AppDrawer extends StatelessWidget {
  const AppDrawer({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Drawer(
      backgroundColor: theme.cardColor,
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 24, 20, 16),
              child: Text(
                "Let's Study with Pal!!!",
                style: theme.textTheme.titleLarge?.copyWith(fontSize: 18),
              ),
            ),
            Divider(color: theme.dividerColor),
            const SizedBox(height: 8),
            DrawerItem(
              icon: Icons.person_add_alt_1_outlined,
              label: 'Add a friend',
              onTap: () => Navigator.pop(context),
            ),
            DrawerItem(
              icon: Icons.block_outlined,
              label: 'Block a friend',
              onTap: () => Navigator.pop(context),
            ),
            DrawerItem(
              icon: Icons.send_outlined,
              label: 'Send request',
              onTap: () => Navigator.pop(context),
            ),
            Divider(color: theme.dividerColor, indent: 20, endIndent: 20),
            DrawerItem(
              icon: Icons.person_outline_rounded,
              label: 'Profile',
              onTap: () => Navigator.pop(context),
            ),
            DrawerItem(
              icon: Icons.settings_outlined,
              label: 'Settings',
              onTap: () => context.go('/settings'),
            ),
          ],
        ),
      ),
    );
  }
}

class DrawerItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const DrawerItem({
    required this.icon,
    required this.label,
    required this.onTap,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final primaryColor = theme.colorScheme.primary;

    return ListTile(
      leading: Icon(icon, color: primaryColor, size: 22),
      title: Text(label, style: theme.textTheme.bodyMedium),
      onTap: onTap,
      horizontalTitleGap: 8,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 2),
    );
  }
}

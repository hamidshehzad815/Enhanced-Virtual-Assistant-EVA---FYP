import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colours.dart';
import '../../core/theme/app_text_style.dart';
import '../providers/settings_viewmodel.dart';

class AppShell extends StatefulWidget {
  final Widget child;
  final String location;

  const AppShell({super.key, required this.child, required this.location});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell>
    with SingleTickerProviderStateMixin {
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();
  late final AnimationController _navController;
  late final Animation<double> _navAnimation;

  @override
  void initState() {
    super.initState();
    _navController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 260),
      value: 1.0, // always visible by default
    );
    _navAnimation = CurvedAnimation(
      parent: _navController,
      curve: Curves.easeInOut,
    );
  }

  @override
  void dispose() {
    _navController.dispose();
    super.dispose();
  }

  // ── Tab definitions ───────────────────────────────────────────────────────
  static const _tabs = [
    _TabItem(
      icon: Icons.home_outlined,
      activeIcon: Icons.home_filled,
      label: 'Home',
      route: '/',
    ),
    _TabItem(
      icon: Icons.calendar_month_outlined,
      activeIcon: Icons.calendar_month_rounded,
      label: 'Calendar',
      route: '/calendar',
    ),
    _TabItem(
      icon: Icons.chat_bubble_outline_rounded,
      activeIcon: Icons.chat_bubble_rounded,
      label: 'Chat',
      route: '/chat',
    ),
    _TabItem(
      icon: Icons.route_outlined,
      activeIcon: Icons.route_rounded,
      label: 'Roadmap',
      route: '/roadmap',
    ),
    _TabItem(
      icon: Icons.bar_chart_rounded,
      activeIcon: Icons.bar_chart,
      label: 'Analytics',
      route: '/analytics',
    ),
    _TabItem(
      icon: Icons.grid_view_outlined,
      activeIcon: Icons.grid_view_rounded,
      label: 'More',
      route: '__more__',
    ),
  ];

  int get _currentIndex {
    switch (widget.location) {
      case '/':
        return 0;
      case '/calendar':
        return 1;
      case '/chat':
        return 2;
      case '/roadmap':
        return 3;
      case '/analytics':
        return 4;
      case '/settings':
      case '/collaboration':
        return 5; // More tab
      default:
        return 0;
    }
  }

  void _onTabTap(int index, BuildContext ctx) {
    if (_tabs[index].route == '__more__') {
      _showMoreSheet(ctx);
    } else {
      // If any modal (eg. bottom sheet) is open, dismiss it first so it
      // doesn't persist on the destination screen.
      // Try dismissing any modal routes opened either on the root navigator
      // or the current navigator so bottom sheets don't persist after tab switch.
      // Try dismissing modal routes multiple times (root + local)
      // Dismiss root modal routes first, then the local navigator.
      for (int i = 0; i < 3; i++) {
        try {
          if (Navigator.of(ctx, rootNavigator: true).canPop()) {
            Navigator.of(ctx, rootNavigator: true).pop();
            continue;
          }
        } catch (_) {}
        try {
          if (Navigator.of(ctx).canPop()) {
            Navigator.of(ctx).pop();
          }
        } catch (_) {}
      }

      if (index == 2) {
        ctx.push('/chat');
      } else {
        ctx.go(_tabs[index].route);
      }
    }
  }

  void _showMoreSheet(BuildContext ctx) {
    final isDark = Theme.of(ctx).brightness == Brightness.dark;
    showModalBottomSheet(
      context: ctx,
      backgroundColor: Colors.transparent,
      isScrollControlled: false,
      builder: (_) => _MoreSheet(
        isDark: isDark,
        parentContext: ctx,
        onLogout: () => _handleMoreLogout(ctx),
      ),
    );
  }

  void _handleMoreLogout(BuildContext ctx) {
    Navigator.pop(ctx);
    showDialog<bool>(
      context: ctx,
      barrierDismissible: false,
      builder: (dialogCtx) {
        return AlertDialog(
          title: const Text('Log Out'),
          content: const Text('Are you sure you want to log out?'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogCtx).pop(false),
              child: const Text('Cancel'),
            ),
            TextButton(
              onPressed: () => Navigator.of(dialogCtx).pop(true),
              child: const Text('Log Out', style: TextStyle(color: Colors.red)),
            ),
          ],
        );
      },
    ).then((confirmed) async {
      if (confirmed != true) return;
      try {
        await ctx.read<SettingsViewModel>().logout();
      } catch (e) {
        if (ctx.mounted) {
          ScaffoldMessenger.of(ctx).showSnackBar(
            SnackBar(
              content: Text('Logout failed: $e'),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
      if (ctx.mounted) {
        ctx.go('/welcome');
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      key: _scaffoldKey,
      backgroundColor: Colors.transparent,
      body: widget.child,
      bottomNavigationBar: SizeTransition(
        sizeFactor: _navAnimation,
        axisAlignment: -1,
        child: _NavBar(
          isDark: isDark,
          currentIndex: _currentIndex,
          tabs: _tabs,
          onTap: (i) => _onTabTap(i, context),
        ),
      ),
    );
  }
}

// ── Bottom Nav Bar widget ─────────────────────────────────────────────────────
class _NavBar extends StatelessWidget {
  final bool isDark;
  final int currentIndex;
  final List<_TabItem> tabs;
  final ValueChanged<int> onTap;

  const _NavBar({
    required this.isDark,
    required this.currentIndex,
    required this.tabs,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final bg = isDark ? AppColors.cardDark : Colors.white;
    final border = isDark ? AppColors.borderDark : const Color(0xFFE5E7EB);

    return Container(
      height: 72,
      decoration: BoxDecoration(
        color: bg,
        border: Border(top: BorderSide(color: border, width: 1)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(isDark ? 0.35 : 0.07),
            blurRadius: 24,
            offset: const Offset(0, -4),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: Row(
          children: List.generate(tabs.length, (i) {
            final selected = i == currentIndex;
            final color = selected
                ? AppColors.primary
                : (isDark
                      ? AppColors.secondaryTextDark
                      : AppColors.secondaryTextLight);

            return Expanded(
              child: GestureDetector(
                onTap: () => onTap(i),
                behavior: HitTestBehavior.opaque,
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    // Pill indicator behind icon when selected
                    AnimatedContainer(
                      duration: const Duration(milliseconds: 220),
                      curve: Curves.easeOutCubic,
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: selected
                            ? AppColors.primary.withOpacity(0.12)
                            : Colors.transparent,
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Icon(
                        selected ? tabs[i].activeIcon : tabs[i].icon,
                        size: 22,
                        color: color,
                      ),
                    ),
                    const SizedBox(height: 2),
                    AnimatedDefaultTextStyle(
                      duration: const Duration(milliseconds: 220),
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: selected
                            ? FontWeight.w700
                            : FontWeight.w400,
                        color: color,
                        fontFamily: 'Inter',
                      ),
                      child: Text(tabs[i].label),
                    ),
                  ],
                ),
              ),
            );
          }),
        ),
      ),
    );
  }
}

// ── More bottom sheet ─────────────────────────────────────────────────────────
class _MoreSheet extends StatelessWidget {
  final bool isDark;
  final BuildContext parentContext;
  final VoidCallback onLogout;

  const _MoreSheet({
    required this.isDark,
    required this.parentContext,
    required this.onLogout,
  });

  @override
  Widget build(BuildContext context) {
    final bg = isDark ? AppColors.cardDark : Colors.white;
    final titleColor = isDark
        ? AppColors.primaryTextDark
        : AppColors.primaryTextLight;
    final subtitleColor = isDark
        ? AppColors.secondaryTextDark
        : AppColors.secondaryTextLight;

    final items = [
      _MoreItem(
        icon: Icons.people_outline_rounded,
        label: 'Friends & Collaborators',
        subtitle: 'Study together, share tasks',
        color: const Color(0xFF22C55E),
        onTap: () {
          Navigator.pop(context);
          parentContext.go('/collaboration');
        },
      ),
      _MoreItem(
        icon: Icons.settings_outlined,
        label: 'Settings',
        subtitle: 'App preferences & account',
        color: const Color(0xFF3B82F6),
        onTap: () {
          Navigator.pop(context);
          parentContext.go('/settings');
        },
      ),
      _MoreItem(
        icon: Icons.logout_rounded,
        label: 'Log Out',
        subtitle: 'Sign out of your account',
        color: const Color(0xFFEF4444),
        onTap: onLogout,
      ),
    ];

    return Container(
      decoration: BoxDecoration(
        color: bg,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.18),
            blurRadius: 32,
            offset: const Offset(0, -8),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Handle
          Center(
            child: Padding(
              padding: const EdgeInsets.only(top: 12, bottom: 4),
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: isDark
                      ? AppColors.borderDark
                      : const Color(0xFFE5E7EB),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
          ),

          // Title
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 12, 24, 4),
            child: Text(
              'More Options',
              style: AppTextStyles.logo.copyWith(
                fontSize: 18,
                color: titleColor,
              ),
            ),
          ),

          const SizedBox(height: 8),

          // Items
          ...items.map(
            (item) => InkWell(
              onTap: item.onTap,
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 20,
                  vertical: 12,
                ),
                child: Row(
                  children: [
                    // Icon container
                    Container(
                      width: 46,
                      height: 46,
                      decoration: BoxDecoration(
                        color: item.color.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: Icon(item.icon, color: item.color, size: 22),
                    ),
                    const SizedBox(width: 14),
                    // Labels
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            item.label,
                            style: TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w600,
                              color: titleColor,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            item.subtitle,
                            style: TextStyle(
                              fontSize: 12,
                              color: subtitleColor,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Icon(
                      Icons.chevron_right_rounded,
                      color: subtitleColor,
                      size: 20,
                    ),
                  ],
                ),
              ),
            ),
          ),

          const SizedBox(height: 20),
        ],
      ),
    );
  }
}

// ── Data classes ──────────────────────────────────────────────────────────────
class _TabItem {
  final IconData icon;
  final IconData activeIcon;
  final String label;
  final String route;
  const _TabItem({
    required this.icon,
    required this.activeIcon,
    required this.label,
    required this.route,
  });
}

class _MoreItem {
  final IconData icon;
  final String label;
  final String subtitle;
  final Color color;
  final VoidCallback onTap;
  const _MoreItem({
    required this.icon,
    required this.label,
    required this.subtitle,
    required this.color,
    required this.onTap,
  });
}

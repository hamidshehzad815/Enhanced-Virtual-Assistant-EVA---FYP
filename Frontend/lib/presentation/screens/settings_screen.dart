import 'package:flutter/material.dart';
import '../../core/theme/app_colours.dart';
import '../../core/theme/app_text_style.dart';
import '../../data/models/setting_model.dart';
import '../widgets/settings_widgets.dart';
import 'package:provider/provider.dart';
import '../providers/theme_provider.dart';
import '../providers/settings_viewmodel.dart';
import '../providers/profile_viewmodel.dart';
import 'package:go_router/go_router.dart';
import '../../router/app_router.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final TextEditingController _searchController = TextEditingController();

  static const List<String> fullDayNames = [
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
    'Sunday',
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<SettingsViewModel>().loadSettings();
      context.read<ProfileViewModel>().loadProfile();
    });
    _searchController.addListener(() {
      context.read<SettingsViewModel>().updateSearchQuery(
        _searchController.text,
      );
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<SettingsViewModel>();
    final settings = vm.settings;
    final searchQuery = vm.searchQuery;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final profileVM = context.watch<ProfileViewModel>();
    final profile = profileVM.profile;

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: SafeArea(
        child: Column(
          children: [
            _buildHeader(isDark),
            SettingsSearchBar(
              controller: _searchController,
              searchQuery: searchQuery,
              onClear: () {
                _searchController.clear();
                vm.updateSearchQuery('');
              },
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
                children: [
                  SettingsProfileCard(
                    isDark: isDark,
                    searchQuery: searchQuery,
                    profile: profile,
                    onEditProfile: () => _navigateToEditProfile(profileVM),
                  ),
                  const SizedBox(height: 20),
                  SettingsSection(
                    isDark: isDark,
                    icon: Icons.tune_rounded,
                    iconColor: const Color(0xFF3B82F6),
                    title: 'App Preferences',
                    tiles: _appPreferenceTiles(vm, settings, isDark),
                    searchQuery: searchQuery,
                  ),
                  const SizedBox(height: 20),
                  SettingsSection(
                    isDark: isDark,
                    icon: Icons.notifications_outlined,
                    iconColor: const Color(0xFFF59E0B),
                    title: 'Notifications',
                    tiles: _notificationTiles(vm, settings, isDark),
                    searchQuery: searchQuery,
                  ),
                  const SizedBox(height: 20),
                  SettingsSection(
                    isDark: isDark,
                    icon: Icons.school_outlined,
                    iconColor: const Color(0xFF8B5CF6),
                    title: 'Tasks Scheduling',
                    tiles: _learningTiles(vm, settings, isDark),
                    searchQuery: searchQuery,
                  ),
                  const SizedBox(height: 20),
                  SettingsSection(
                    isDark: isDark,
                    icon: Icons.assignment_rounded,
                    iconColor: const Color.fromARGB(255, 187, 91, 104),
                    title: 'Learning Scheduling',
                    tiles: _scheduleTiles(vm, settings, isDark),
                    searchQuery: searchQuery,
                  ),
                  const SizedBox(height: 20),
                  SettingsSection(
                    isDark: isDark,
                    icon: Icons.lock_outline_rounded,
                    iconColor: const Color(0xFF22C55E),
                    title: 'Privacy & Social',
                    tiles: _privacyTiles(vm, settings, isDark),
                    searchQuery: searchQuery,
                  ),
                  const SizedBox(height: 20),
                  SettingsSection(
                    isDark: isDark,
                    icon: Icons.info_outline_rounded,
                    iconColor: const Color(0xFF6B7280),
                    title: 'About',
                    tiles: _aboutTiles(isDark),
                    searchQuery: searchQuery,
                  ),
                  const SizedBox(height: 20),
                  _buildDangerZone(vm, isDark),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(bool isDark) {
    final primary = isDark
        ? AppColors.primaryTextDark
        : AppColors.primaryTextLight;
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 4),
      child: Row(
        children: [
          Text(
            'Settings',
            style: AppTextStyles.logo.copyWith(fontSize: 26, color: primary),
          ),
        ],
      ),
    );
  }

  void _navigateToEditProfile(ProfileViewModel profileVM) {
    context.push(AppRoutes.editProfile);
  }

  // ========================= APP PREFERENCES =========================
  List<SettingTileData> _appPreferenceTiles(
    SettingsViewModel vm,
    SettingsModel settings,
    bool isDark,
  ) => [
    SettingTileData(
      icon: Icons.palette_outlined,
      iconColor: const Color(0xFF3B82F6),
      label: 'Theme',
      subtitle: 'Controls app appearance',
      valueBadge: settings.theme == 'system'
          ? 'System'
          : '${settings.theme[0].toUpperCase()}${settings.theme.substring(1)}',
      onTap: () => _showOptionsSheet(
        title: 'Theme',
        options: const ['light', 'dark', 'system'],
        selected: settings.theme,
        labels: const ['Light', 'Dark', 'System default'],
        icons: const [
          Icons.light_mode_rounded,
          Icons.dark_mode_rounded,
          Icons.phone_android_rounded,
        ],
        onSelect: (v) async {
          final oldTheme = settings.theme;
          try {
            await Provider.of<ThemeProvider>(
              context,
              listen: false,
            ).setTheme(v);
            await vm.updateTheme(v);
          } catch (e) {
            await Provider.of<ThemeProvider>(
              context,
              listen: false,
            ).setTheme(oldTheme);
            if (mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text(
                    'Failed to update theme: ${_friendlyErrorMessage(e)}',
                  ),
                  backgroundColor: Colors.red,
                ),
              );
            }
          }
        },
      ),
    ),
    SettingTileData(
      icon: Icons.sync_rounded,
      iconColor: const Color(0xFF3B82F6),
      label: 'Google Calendar Sync',
      subtitle: 'Sync tasks to Google Calendar',
      toggleValue: settings.googleCalendarSyncEnabled,
      onToggle: (v) async => vm.updateGoogleCalendarSync(v),
    ),
    SettingTileData(
      icon: Icons.show_chart_outlined,
      iconColor: const Color(0xFF3B82F6),
      label: 'Allow Behavioural Insights',
      subtitle: 'Let Eva analyze your learning patterns',
      toggleValue: settings.behavioralAnalyticsEnabled,
      onToggle: (v) async => vm.updateBehaviorAnalytics(v),
    ),
  ];

  // ========================= NOTIFICATIONS =========================
  List<SettingTileData> _notificationTiles(
    SettingsViewModel vm,
    SettingsModel settings,
    bool isDark,
  ) {
    final tiles = [
      SettingTileData(
        icon: Icons.notifications_active_outlined,
        iconColor: const Color(0xFFF59E0B),
        label: 'All Notifications',
        subtitle: 'Master toggle for all alerts',
        toggleValue: settings.notificationsEnabled,
        onToggle: (v) async => vm.updateNotificationsEnabled(v),
      ),
      SettingTileData(
        icon: Icons.phone_android_rounded,
        iconColor: const Color(0xFFF59E0B),
        label: 'Push Notifications',
        subtitle: 'Alerts on your device',
        toggleValue: settings.pushNotificationsEnabled,
        enabled: settings.notificationsEnabled,
        onToggle: (v) async => vm.updatePushNotificationsEnabled(v),
      ),
      SettingTileData(
        icon: Icons.email_outlined,
        iconColor: const Color(0xFFF59E0B),
        label: 'Email Notifications',
        subtitle: 'Summaries sent to your email',
        toggleValue: settings.emailNotificationsEnabled,
        enabled: settings.notificationsEnabled,
        onToggle: (v) async => vm.updateEmailNotificationsEnabled(v),
      ),
      SettingTileData(
        icon: Icons.bedtime_outlined,
        iconColor: const Color(0xFFF59E0B),
        label: 'Quiet Hours',
        subtitle: 'Silence notifications during defined intervals',
        toggleValue: settings.quietHoursEnabled,
        onToggle: (v) async => vm.updateQuietHoursEnabled(v),
      ),
    ];

    if (settings.quietHoursEnabled) {
      tiles.add(
        SettingTileData(
          icon: Icons.edit_calendar_rounded,
          iconColor: const Color(0xFFF59E0B),
          label: 'Manage Quiet Hours',
          subtitle: 'Add or remove intervals',
          valueBadge: '${settings.quietHours.length} interval(s)',
          onTap: () => _showQuietHoursManager(vm),
        ),
      );
    }
    return tiles;
  }

  // ========================= TASKS SCHEDULING =========================
  List<SettingTileData> _learningTiles(
    SettingsViewModel vm,
    SettingsModel settings,
    bool isDark,
  ) => [
    SettingTileData(
      icon: Icons.alarm_rounded,
      iconColor: const Color(0xFF8B5CF6),
      label: 'Default Reminder',
      subtitle: 'Before tasks & exams',
      valueBadge: '${settings.defaultReminderMinutes} min',
      onTap: () => _showDurationPicker(
        title: 'Default Reminder Time',
        currentValue: settings.defaultReminderMinutes,
        options: const [5, 10, 15, 30, 60, 120],
        unit: 'min',
        onSelect: (v) async => vm.updateDefaultReminderMinutes(v),
      ),
    ),
    SettingTileData(
      icon: Icons.timer_outlined,
      iconColor: const Color(0xFF8B5CF6),
      label: 'Default Task Duration',
      valueBadge: '${settings.defaultTaskDuration} min',
      onTap: () => _showDurationPicker(
        title: 'Default Task Duration',
        currentValue: settings.defaultTaskDuration,
        options: const [30, 60, 90, 120, 180, 240],
        unit: 'min',
        onSelect: (v) async => vm.updateDefaultTaskDuration(v),
      ),
    ),
  ];

  // ========================= LEARNING SCHEDULING =========================
  List<SettingTileData> _scheduleTiles(
    SettingsViewModel vm,
    SettingsModel settings,
    bool isDark,
  ) => [
    SettingTileData(
      icon: Icons.schedule_rounded,
      iconColor: const Color.fromARGB(255, 187, 91, 104),
      label: 'Learning Schedules',
      subtitle: 'Define multiple study slots',
      valueBadge: '${settings.learningSchedules.length} learning schedule(s)',
      onTap: () => _showLearningSchedulesManager(vm),
    ),
    SettingTileData(
      icon: Icons.menu_book_rounded,
      iconColor: const Color.fromARGB(255, 187, 91, 104),
      label: 'Learning Reminder Time',
      subtitle: 'Before study sessions',
      valueBadge: '${settings.defaultLearningReminderMinutes} min',
      onTap: () => _showDurationPicker(
        title: 'Reminder Time',
        currentValue: settings.defaultLearningReminderMinutes,
        options: const [5, 10, 15, 30, 60],
        unit: 'min',
        onSelect: (v) async => vm.updateDefaultLearningReminderMinutes(v),
      ),
    ),
  ];

  // ========================= PRIVACY & SOCIAL =========================
  List<SettingTileData> _privacyTiles(
    SettingsViewModel vm,
    SettingsModel settings,
    bool isDark,
  ) => [
    SettingTileData(
      icon: Icons.group,
      iconColor: const Color(0xFF22C55E),
      label: 'Allow Friends Request',
      toggleValue: settings.allowFriendRequests,
      onToggle: (v) async => vm.updateAllowFriendRequests(v),
    ),
    SettingTileData(
      icon: Icons.shield_outlined,
      iconColor: const Color(0xFF22C55E),
      label: 'Privacy Policy',
      onTap: () {},
    ),
    SettingTileData(
      icon: Icons.description_outlined,
      iconColor: const Color(0xFF22C55E),
      label: 'Terms of Service',
      onTap: () {},
    ),
  ];

  // ========================= ABOUT =========================
  List<SettingTileData> _aboutTiles(bool isDark) => [
    SettingTileData(
      icon: Icons.info_outline_rounded,
      iconColor: const Color(0xFF6B7280),
      label: 'App Version',
      valueBadge: '1.0.0',
      onTap: () {},
    ),
    SettingTileData(
      icon: Icons.star_outline_rounded,
      iconColor: const Color(0xFF6B7280),
      label: 'Rate EVA',
      subtitle: 'Love the app? Leave a review',
      onTap: () {},
    ),
    SettingTileData(
      icon: Icons.bug_report_outlined,
      iconColor: const Color(0xFF6B7280),
      label: 'Report a Bug',
      onTap: () {},
    ),
    SettingTileData(
      icon: Icons.help_outline_rounded,
      iconColor: const Color(0xFF6B7280),
      label: 'Help & Support',
      onTap: () {},
    ),
  ];

  // ========================= DANGER ZONE =========================
  Widget _buildDangerZone(SettingsViewModel vm, bool isDark) {
    if (vm.searchQuery.isNotEmpty) return const SizedBox.shrink();

    final bg = isDark ? AppColors.cardDark : Colors.white;
    final divider = isDark ? AppColors.borderDark : const Color(0xFFF3F4F6);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Row(
            children: [
              Container(
                width: 28,
                height: 28,
                decoration: BoxDecoration(
                  color: const Color(0xFFEF4444).withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.warning_amber_rounded,
                  size: 15,
                  color: Color(0xFFEF4444),
                ),
              ),
              const SizedBox(width: 10),
              Text(
                'Danger Zone',
                style: AppTextStyles.subtitleMedium.copyWith(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.3,
                  color: const Color(0xFFEF4444),
                ),
              ),
            ],
          ),
        ),
        Container(
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: const Color(0xFFEF4444).withOpacity(0.3)),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(isDark ? 0.2 : 0.04),
                blurRadius: 12,
                offset: const Offset(0, 3),
              ),
            ],
          ),
          child: Column(
            children: [
              InkWell(
                onTap: () => _showConfirmDialog(
                  title: 'Log Out',
                  message: 'Are you sure you want to log out?',
                  confirmLabel: 'Log Out',
                  confirmColor: const Color(0xFFEF4444),
                  onConfirm: () async {
                    try {
                      await context.read<SettingsViewModel>().logout();
                      if (mounted) {
                        context.go(AppRoutes.welcome);
                      }
                    } catch (e) {
                      if (mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                              'Logout failed: ${_friendlyErrorMessage(e)}',
                            ),
                            backgroundColor: Colors.red,
                          ),
                        );
                      }
                    }
                  },
                ),
                borderRadius: const BorderRadius.vertical(
                  top: Radius.circular(18),
                ),
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 14,
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 36,
                        height: 36,
                        decoration: BoxDecoration(
                          color: const Color(0xFFEF4444).withOpacity(0.08),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: const Icon(
                          Icons.logout_rounded,
                          size: 18,
                          color: Color(0xFFEF4444),
                        ),
                      ),
                      const SizedBox(width: 14),
                      const Expanded(
                        child: Text(
                          'Log Out',
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                            color: Color(0xFFEF4444),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              Divider(height: 1, color: divider, indent: 16, endIndent: 16),
              InkWell(
                onTap: () => _showConfirmDialog(
                  title: 'Delete Account',
                  message:
                      'This will permanently delete your account and all data. This cannot be undone.',
                  confirmLabel: 'Delete Forever',
                  confirmColor: const Color(0xFFEF4444),
                  onConfirm: () async {
                    try {
                      await context.read<SettingsViewModel>().deleteAccount();
                    } catch (e) {
                      if (mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                              'Account deletion failed: ${_friendlyErrorMessage(e)}',
                            ),
                            backgroundColor: Colors.red,
                          ),
                        );
                      }
                    }
                  },
                ),
                borderRadius: const BorderRadius.vertical(
                  bottom: Radius.circular(18),
                ),
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 14,
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 36,
                        height: 36,
                        decoration: BoxDecoration(
                          color: const Color(0xFFEF4444).withOpacity(0.08),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: const Icon(
                          Icons.delete_forever_rounded,
                          size: 18,
                          color: Color(0xFFEF4444),
                        ),
                      ),
                      const SizedBox(width: 14),
                      const Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Delete Account',
                              style: TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.w500,
                                color: Color(0xFFEF4444),
                              ),
                            ),
                            SizedBox(height: 2),
                            Text(
                              'Permanently removes all your data',
                              style: TextStyle(
                                fontSize: 11,
                                color: Color(0xFF9CA3AF),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  // ==================== QUIET HOURS MANAGER ====================
  void _showQuietHoursManager(SettingsViewModel vm) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final List<QuietHourInterval> tempList = List.from(vm.settings.quietHours);

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setSheetState) {
            return Container(
              decoration: BoxDecoration(
                color: isDark ? AppColors.cardDark : Colors.white,
                borderRadius: const BorderRadius.vertical(
                  top: Radius.circular(24),
                ),
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  _buildSheetHandle(isDark),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(20, 8, 20, 16),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'Quiet Hours',
                          style: AppTextStyles.logo.copyWith(fontSize: 18),
                        ),
                        IconButton(
                          icon: const Icon(Icons.add_circle_outline),
                          onPressed: () => setSheetState(() {
                            tempList.add(
                              QuietHourInterval(
                                label: 'New Interval',
                                startTime: const TimeOfDay(hour: 22, minute: 0),
                                endTime: const TimeOfDay(hour: 7, minute: 0),
                                enabled: true,
                              ),
                            );
                          }),
                          color: AppColors.primary,
                        ),
                      ],
                    ),
                  ),
                  if (tempList.isEmpty)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 40),
                      child: Column(
                        children: [
                          Icon(
                            Icons.bedtime_outlined,
                            size: 48,
                            color: Colors.grey.shade400,
                          ),
                          const SizedBox(height: 12),
                          Text(
                            'No quiet hours defined',
                            style: TextStyle(color: Colors.grey.shade500),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'Tap + to add an interval',
                            style: TextStyle(
                              fontSize: 12,
                              color: Colors.grey.shade400,
                            ),
                          ),
                        ],
                      ),
                    )
                  else
                    ConstrainedBox(
                      constraints: BoxConstraints(
                        maxHeight: MediaQuery.of(ctx).size.height * 0.6,
                      ),
                      child: ListView.builder(
                        shrinkWrap: true,
                        itemCount: tempList.length,
                        itemBuilder: (_, idx) => _buildQuietHourTile(
                          ctx,
                          idx,
                          tempList,
                          setSheetState,
                          isDark,
                        ),
                      ),
                    ),
                  _buildSaveCancelButtons(
                    ctx,
                    onSave: () async {
                      try {
                        await vm.updateQuietHours(tempList);
                        if (ctx.mounted) {
                          Navigator.pop(ctx);
                          ScaffoldMessenger.of(ctx).showSnackBar(
                            const SnackBar(
                              content: Text('Quiet hours saved successfully'),
                              backgroundColor: Colors.green,
                            ),
                          );
                        }
                      } catch (e) {
                        if (ctx.mounted) {
                          ScaffoldMessenger.of(ctx).showSnackBar(
                            SnackBar(
                              content: Text(
                                'Failed to save: ${_friendlyErrorMessage(e)}',
                              ),
                              backgroundColor: Colors.red,
                            ),
                          );
                        }
                      }
                    },
                  ),
                  const SizedBox(height: 12),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildQuietHourTile(
    BuildContext ctx,
    int index,
    List<QuietHourInterval> list,
    StateSetter setSheetState,
    bool isDark,
  ) {
    final interval = list[index];
    final controller = TextEditingController(text: interval.label);

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      color: isDark ? AppColors.cardElevatedDark : Colors.grey.shade50,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            Row(
              children: [
                Flexible(
                  flex: 3,
                  child: TextField(
                    controller: controller,
                    decoration: const InputDecoration(
                      hintText: 'Label (e.g., Sleeping)',
                      border: InputBorder.none,
                      isDense: true,
                    ),
                    style: const TextStyle(fontWeight: FontWeight.w500),
                    onChanged: (value) => interval.label = value,
                  ),
                ),
                Switch(
                  value: interval.enabled,
                  onChanged: (val) =>
                      setSheetState(() => interval.enabled = val),
                  activeColor: AppColors.primary,
                ),
                IconButton(
                  icon: const Icon(Icons.delete_outline, size: 20),
                  onPressed: () {
                    setSheetState(() => list.removeAt(index));
                    controller.dispose();
                  },
                  color: Colors.red.shade400,
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: _buildTimePickerTile(
                    label: 'From',
                    time: interval.startTime,
                    onChanged: (t) =>
                        setSheetState(() => interval.startTime = t),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildTimePickerTile(
                    label: 'To',
                    time: interval.endTime,
                    onChanged: (t) => setSheetState(() => interval.endTime = t),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  // ==================== LEARNING SCHEDULES MANAGER ====================
  void _showLearningSchedulesManager(SettingsViewModel vm) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        return AnimatedBuilder(
          animation: vm,
          builder: (ctx, _) {
            final schedules = vm.settings.learningSchedules;
            return Container(
              decoration: BoxDecoration(
                color: isDark ? AppColors.cardDark : Colors.white,
                borderRadius: const BorderRadius.vertical(
                  top: Radius.circular(24),
                ),
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  _buildSheetHandle(isDark),
                  Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'Learning Schedules',
                          style: AppTextStyles.logo.copyWith(fontSize: 18),
                        ),
                        IconButton(
                          icon: const Icon(Icons.add),
                          onPressed: () => _showCreateScheduleSheet(vm),
                          color: AppColors.primary,
                        ),
                      ],
                    ),
                  ),
                  if (schedules.isEmpty)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 40),
                      child: Column(
                        children: [
                          Icon(
                            Icons.schedule,
                            size: 48,
                            color: Colors.grey.shade400,
                          ),
                          const SizedBox(height: 12),
                          Text(
                            'No learning schedules',
                            style: TextStyle(color: Colors.grey.shade500),
                          ),
                        ],
                      ),
                    )
                  else
                    ConstrainedBox(
                      constraints: BoxConstraints(
                        maxHeight: MediaQuery.of(ctx).size.height * 0.6,
                      ),
                      child: ListView.builder(
                        shrinkWrap: true,
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        itemCount: schedules.length,
                        itemBuilder: (_, idx) {
                          final schedule = schedules[idx];
                          return Container(
                            margin: const EdgeInsets.only(bottom: 10),
                            decoration: BoxDecoration(
                              color: isDark
                                  ? AppColors.cardElevatedDark
                                  : Colors.grey.shade50,
                              borderRadius: BorderRadius.circular(14),
                              border: Border.all(
                                color: isDark
                                    ? AppColors.borderDark
                                    : AppColors.borderLight,
                              ),
                            ),
                            child: InkWell(
                              borderRadius: BorderRadius.circular(14),
                              onTap: () => _showScheduleDetail(vm, schedule),
                              child: Padding(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 14,
                                  vertical: 12,
                                ),
                                child: Row(
                                  children: [
                                    Container(
                                      width: 36,
                                      height: 36,
                                      decoration: BoxDecoration(
                                        color: AppColors.primary.withOpacity(
                                          0.12,
                                        ),
                                        borderRadius: BorderRadius.circular(10),
                                      ),
                                      child: const Icon(
                                        Icons.schedule_rounded,
                                        size: 18,
                                        color: AppColors.primary,
                                      ),
                                    ),
                                    const SizedBox(width: 12),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            schedule.label,
                                            style: TextStyle(
                                              fontWeight: FontWeight.w600,
                                              fontSize: 14,
                                              color: isDark
                                                  ? AppColors.primaryTextDark
                                                  : AppColors.primaryTextLight,
                                            ),
                                            overflow: TextOverflow.ellipsis,
                                          ),
                                          const SizedBox(height: 2),
                                          Text(
                                            '${schedule.slots.length} day(s) scheduled',
                                            style: TextStyle(
                                              fontSize: 12,
                                              color: isDark
                                                  ? AppColors.secondaryTextDark
                                                  : AppColors
                                                        .secondaryTextLight,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                    IconButton(
                                      icon: const Icon(
                                        Icons.delete_outline,
                                        color: Colors.red,
                                        size: 20,
                                      ),
                                      onPressed: () => _showConfirmDialog(
                                        title: 'Delete Schedule',
                                        message:
                                            'Delete "${schedule.label}"? This cannot be undone.',
                                        confirmLabel: 'Delete',
                                        confirmColor: Colors.red,
                                        onConfirm: () async {
                                          try {
                                            await vm.deleteLearningSchedule(
                                              schedule.id,
                                            );
                                          } catch (e) {
                                            if (ctx.mounted) {
                                              ScaffoldMessenger.of(
                                                ctx,
                                              ).showSnackBar(
                                                SnackBar(
                                                  content: Text(
                                                    'Failed to delete schedule: ${_friendlyErrorMessage(e)}',
                                                  ),
                                                  backgroundColor: Colors.red,
                                                ),
                                              );
                                            }
                                          }
                                        },
                                      ),
                                    ),
                                    Icon(
                                      Icons.chevron_right,
                                      color: isDark
                                          ? AppColors.secondaryTextDark
                                          : AppColors.secondaryTextLight,
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          );
                        },
                      ),
                    ),
                  const SizedBox(height: 12),
                ],
              ),
            );
          },
        );
      },
    );
  }

  // ==================== CREATE SCHEDULE ====================
  void _showCreateScheduleSheet(SettingsViewModel vm) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final labelController = TextEditingController();
    String label = '';
    List<_NewSlotData> slots = [];

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setSheetState) {
            return Container(
              decoration: BoxDecoration(
                color: isDark ? AppColors.cardDark : Colors.white,
                borderRadius: const BorderRadius.vertical(
                  top: Radius.circular(24),
                ),
              ),
              constraints: BoxConstraints(
                maxHeight: MediaQuery.of(ctx).size.height * 0.85,
              ),
              child: SingleChildScrollView(
                child: Padding(
                  padding: EdgeInsets.only(
                    left: 20,
                    right: 20,
                    top: 20,
                    bottom: MediaQuery.of(ctx).viewInsets.bottom + 20,
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildSheetHandle(isDark),
                      const SizedBox(height: 16),
                      Text(
                        'New Learning Schedule',
                        style: AppTextStyles.logo.copyWith(fontSize: 18),
                      ),
                      const SizedBox(height: 16),
                      TextField(
                        controller: labelController,
                        style: TextStyle(
                          color: Theme.of(context).textTheme.bodyMedium?.color,
                        ),
                        decoration: InputDecoration(
                          labelText: 'Title',
                          hintText: 'e.g. Morning Study Block',
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide: BorderSide(
                              color: isDark
                                  ? AppColors.borderDark
                                  : AppColors.borderLight,
                            ),
                          ),
                        ),
                        onChanged: (v) => setSheetState(() => label = v),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'Select days',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: Theme.of(context).textTheme.bodyMedium?.color,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 6,
                        runSpacing: 6,
                        children: List.generate(7, (day) {
                          final selected = slots.any((s) => s.day == day);
                          return FilterChip(
                            label: Text(fullDayNames[day]),
                            selected: selected,
                            selectedColor: AppColors.primary.withOpacity(0.2),
                            checkmarkColor: AppColors.primary,
                            backgroundColor: isDark
                                ? AppColors.cardElevatedDark
                                : Colors.grey.shade100,
                            onSelected: (sel) => setSheetState(() {
                              if (sel) {
                                slots.add(_NewSlotData(day: day));
                              } else {
                                slots.removeWhere((s) => s.day == day);
                              }
                            }),
                          );
                        }),
                      ),
                      const SizedBox(height: 12),
                      if (slots.isEmpty)
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          child: Text(
                            'Pick at least one day, then set its time and duration',
                            style: TextStyle(color: Colors.grey.shade500),
                          ),
                        )
                      else
                        ...slots.map(
                          (slot) =>
                              _buildNewSlotRow(slot, setSheetState, slots),
                        ),
                      const SizedBox(height: 20),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton(
                              onPressed: () => Navigator.pop(ctx),
                              style: OutlinedButton.styleFrom(
                                foregroundColor: Theme.of(
                                  ctx,
                                ).textTheme.bodyMedium?.color,
                                side: BorderSide(
                                  color: isDark
                                      ? AppColors.borderDark
                                      : AppColors.borderLight,
                                ),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                padding: const EdgeInsets.symmetric(
                                  vertical: 12,
                                ),
                              ),
                              child: const Text('Cancel'),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: ElevatedButton(
                              onPressed: () async {
                                // 1. Validate title
                                if (label.trim().isEmpty) {
                                  ScaffoldMessenger.of(ctx).showSnackBar(
                                    const SnackBar(
                                      content: Text('Please enter a title'),
                                      backgroundColor: Colors.red,
                                    ),
                                  );
                                  return;
                                }

                                // 2. Validate at least one day selected
                                if (slots.isEmpty) {
                                  ScaffoldMessenger.of(ctx).showSnackBar(
                                    const SnackBar(
                                      content: Text('Select at least one day'),
                                      backgroundColor: Colors.red,
                                    ),
                                  );
                                  return;
                                }

                                // 3. Validate time & duration are set for every slot
                                if (slots.any(
                                  (s) =>
                                      s.time == null ||
                                      s.durationMinutes == null,
                                )) {
                                  ScaffoldMessenger.of(ctx).showSnackBar(
                                    const SnackBar(
                                      content: Text(
                                        'Please set time and duration for all selected days',
                                      ),
                                      backgroundColor: Colors.red,
                                    ),
                                  );
                                  return;
                                }

                                // 4. Check for conflicts (convert to _SlotData for compatibility)
                                final conflictSlots = slots
                                    .map(
                                      (s) => _SlotData(
                                        day: s.day,
                                        time: s.time!,
                                        durationMinutes: s.durationMinutes!,
                                      ),
                                    )
                                    .toList();
                                final conflict = _findScheduleConflict(
                                  vm,
                                  conflictSlots,
                                  excludeId: null,
                                );
                                if (conflict != null) {
                                  ScaffoldMessenger.of(ctx).showSnackBar(
                                    SnackBar(
                                      content: Text('Conflicts with $conflict'),
                                      backgroundColor: Colors.red,
                                    ),
                                  );
                                  return;
                                }

                                // 5. Create the schedule
                                try {
                                  await vm.createLearningSchedule(
                                    label.trim(),
                                    slots
                                        .map(
                                          (s) => ScheduleSlot(
                                            day: s.day,
                                            time: _formatTimeStatic(s.time!),
                                            durationMinutes: s.durationMinutes!,
                                          ),
                                        )
                                        .toList(),
                                  );
                                  if (ctx.mounted) {
                                    Navigator.pop(ctx);
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(
                                        content: Text('Schedule created'),
                                        backgroundColor: Colors.green,
                                      ),
                                    );
                                  }
                                } catch (e) {
                                  if (ctx.mounted) {
                                    ScaffoldMessenger.of(ctx).showSnackBar(
                                      SnackBar(
                                        content: Text(
                                          'Failed to create: ${_friendlyErrorMessage(e)}',
                                        ),
                                        backgroundColor: Colors.red,
                                      ),
                                    );
                                  }
                                }
                              },
                              style: ElevatedButton.styleFrom(
                                backgroundColor: AppColors.primary,
                                foregroundColor: Colors.white,
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                padding: const EdgeInsets.symmetric(
                                  vertical: 12,
                                ),
                              ),
                              child: const Text('Save'),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildNewSlotRow(
    _NewSlotData slot,
    StateSetter setSheetState,
    List<_NewSlotData> slots,
  ) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textColor = Theme.of(context).textTheme.bodyMedium?.color;
    final bgColor = isDark ? AppColors.cardElevatedDark : Colors.grey.shade50;
    final borderColor = isDark ? AppColors.borderDark : AppColors.borderLight;

    return Container(
      margin: const EdgeInsets.only(bottom: 4),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: borderColor),
      ),
      child: Row(
        children: [
          Text(
            fullDayNames[slot.day],
            style: TextStyle(
              fontWeight: FontWeight.w600,
              fontSize: 13,
              color: AppColors.primary,
            ),
          ),
          const SizedBox(width: 12),
          GestureDetector(
            onTap: () async {
              final picked = await showTimePicker(
                context: context,
                initialTime: slot.time ?? const TimeOfDay(hour: 9, minute: 0),
              );
              if (picked != null) setSheetState(() => slot.time = picked);
            },
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.access_time,
                  size: 14,
                  color: AppColors.primary,
                ),
                const SizedBox(width: 4),
                Text(
                  slot.time?.format(context) ?? 'Set time',
                  style: TextStyle(
                    fontSize: 13,
                    color: slot.time == null ? Colors.orange : textColor,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 16),
          GestureDetector(
            onTap: () async {
              int temp = slot.durationMinutes ?? 60;
              await showModalBottomSheet(
                context: context,
                backgroundColor: isDark ? AppColors.cardDark : Colors.white,
                builder: (_) => StatefulBuilder(
                  builder: (dCtx, setDurationState) => Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'Duration',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: textColor,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            IconButton(
                              icon: const Icon(Icons.remove),
                              color: textColor,
                              onPressed: () => setDurationState(
                                () => temp = (temp - 15).clamp(15, 480),
                              ),
                            ),
                            Text(
                              '$temp min',
                              style: TextStyle(fontSize: 20, color: textColor),
                            ),
                            IconButton(
                              icon: const Icon(Icons.add),
                              color: textColor,
                              onPressed: () => setDurationState(
                                () => temp = (temp + 15).clamp(15, 480),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        ElevatedButton(
                          onPressed: () => Navigator.pop(dCtx),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppColors.primary,
                            foregroundColor: Colors.white,
                          ),
                          child: const Text('Set'),
                        ),
                      ],
                    ),
                  ),
                ),
              );
              setSheetState(() => slot.durationMinutes = temp);
            },
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.timer_outlined,
                  size: 14,
                  color: AppColors.primary,
                ),
                const SizedBox(width: 4),
                Text(
                  slot.durationMinutes == null
                      ? 'Set min'
                      : '${slot.durationMinutes} min',
                  style: TextStyle(
                    fontSize: 13,
                    color: slot.durationMinutes == null
                        ? Colors.orange
                        : textColor,
                  ),
                ),
              ],
            ),
          ),
          const Spacer(),
          IconButton(
            icon: const Icon(Icons.close, size: 16, color: Colors.red),
            onPressed: () => setSheetState(
              () => slots.removeWhere((s) => s.day == slot.day),
            ),
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
          ),
        ],
      ),
    );
  }

  // ==================== SCHEDULE DETAIL / EDIT ====================
  void _showScheduleDetail(SettingsViewModel vm, LearningSchedule schedule) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    bool isEditing = false;

    String label = schedule.label;
    final String originalLabel = schedule.label;
    List<_SlotData> slots = schedule.slots
        .map(
          (s) => _SlotData(
            day: s.day,
            time: _parseTimeStatic(s.time),
            durationMinutes: s.durationMinutes,
          ),
        )
        .toList();
    final List<_SlotData> originalSlots = schedule.slots
        .map(
          (s) => _SlotData(
            day: s.day,
            time: _parseTimeStatic(s.time),
            durationMinutes: s.durationMinutes,
          ),
        )
        .toList();

    final labelController = TextEditingController(text: label);

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setSheetState) {
            bool hasChanges() {
              if (label.trim() != originalLabel.trim()) return true;
              if (slots.length != originalSlots.length) return true;
              for (final s in slots) {
                final matches = originalSlots
                    .where((o) => o.day == s.day)
                    .toList();
                if (matches.isEmpty) return true;
                final o = matches.first;
                if (o.time.hour != s.time.hour ||
                    o.time.minute != s.time.minute ||
                    o.durationMinutes != s.durationMinutes) {
                  return true;
                }
              }
              return false;
            }

            final textColor = Theme.of(context).textTheme.bodyMedium?.color;

            return Container(
              decoration: BoxDecoration(
                color: isDark ? AppColors.cardDark : Colors.white,
                borderRadius: const BorderRadius.vertical(
                  top: Radius.circular(24),
                ),
              ),
              constraints: BoxConstraints(
                maxHeight: MediaQuery.of(ctx).size.height * 0.85,
              ),
              child: SingleChildScrollView(
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 12,
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildSheetHandle(isDark),
                      const SizedBox(height: 10),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Expanded(
                            child: isEditing
                                ? TextField(
                                    controller: labelController,
                                    style: TextStyle(
                                      fontSize: 20,
                                      fontWeight: FontWeight.bold,
                                      color: textColor,
                                    ),
                                    decoration: const InputDecoration(
                                      hintText: 'Schedule title',
                                      border: InputBorder.none,
                                    ),
                                    onChanged: (v) =>
                                        setSheetState(() => label = v),
                                  )
                                : Text(
                                    label,
                                    style: TextStyle(
                                      fontSize: 20,
                                      fontWeight: FontWeight.bold,
                                      color: textColor,
                                    ),
                                  ),
                          ),
                          if (!isEditing)
                            TextButton.icon(
                              onPressed: () =>
                                  setSheetState(() => isEditing = true),
                              icon: const Icon(
                                Icons.edit_outlined,
                                size: 18,
                                color: AppColors.primary,
                              ),
                              label: const Text(
                                'Edit',
                                style: TextStyle(color: AppColors.primary),
                              ),
                            ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Text(
                        '${slots.length} day(s) scheduled',
                        style: TextStyle(
                          fontSize: 13,
                          color: isDark
                              ? AppColors.secondaryTextDark
                              : AppColors.secondaryTextLight,
                        ),
                      ),
                      const SizedBox(height: 16),
                      if (isEditing)
                        ...slots.map(
                          (slot) =>
                              _buildEditableSlotRow(slot, setSheetState, slots),
                        )
                      else
                        ...slots.map((slot) => _buildReadOnlySlotRow(slot)),
                      if (isEditing) ...[
                        const SizedBox(height: 12),
                        Text(
                          'Select days',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: textColor,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Wrap(
                          spacing: 6,
                          runSpacing: 6,
                          children: List.generate(7, (day) {
                            final selected = slots.any((s) => s.day == day);
                            return FilterChip(
                              label: Text(fullDayNames[day]),
                              selected: selected,
                              selectedColor: AppColors.primary.withOpacity(0.2),
                              checkmarkColor: AppColors.primary,
                              backgroundColor: isDark
                                  ? AppColors.cardElevatedDark
                                  : Colors.grey.shade100,
                              onSelected: (sel) => setSheetState(() {
                                if (sel) {
                                  slots.add(
                                    _SlotData(
                                      day: day,
                                      time: const TimeOfDay(hour: 9, minute: 0),
                                      durationMinutes: 60,
                                    ),
                                  );
                                } else {
                                  slots.removeWhere((s) => s.day == day);
                                }
                              }),
                            );
                          }),
                        ),
                      ],
                      const SizedBox(height: 20),
                      if (isEditing)
                        Row(
                          children: [
                            Expanded(
                              child: OutlinedButton(
                                onPressed: () {
                                  setSheetState(() {
                                    isEditing = false;
                                    label = originalLabel;
                                    labelController.text = originalLabel;
                                    slots = originalSlots
                                        .map(
                                          (o) => _SlotData(
                                            day: o.day,
                                            time: o.time,
                                            durationMinutes: o.durationMinutes,
                                          ),
                                        )
                                        .toList();
                                  });
                                },
                                style: OutlinedButton.styleFrom(
                                  foregroundColor: textColor,
                                  side: BorderSide(
                                    color: isDark
                                        ? AppColors.borderDark
                                        : AppColors.borderLight,
                                  ),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  padding: const EdgeInsets.symmetric(
                                    vertical: 12,
                                  ),
                                ),
                                child: const Text('Cancel'),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: ElevatedButton(
                                onPressed: () async {
                                  if (label.trim().isEmpty) {
                                    ScaffoldMessenger.of(ctx).showSnackBar(
                                      const SnackBar(
                                        content: Text('Please enter a title'),
                                        backgroundColor: Colors.red,
                                      ),
                                    );
                                    return;
                                  }
                                  if (slots.isEmpty) {
                                    ScaffoldMessenger.of(ctx).showSnackBar(
                                      const SnackBar(
                                        content: Text(
                                          'Select at least one day',
                                        ),
                                        backgroundColor: Colors.red,
                                      ),
                                    );
                                    return;
                                  }
                                  if (!hasChanges()) {
                                    Navigator.pop(ctx);
                                    return;
                                  }
                                  final conflict = _findScheduleConflict(
                                    vm,
                                    slots,
                                    excludeId: schedule.id,
                                  );
                                  if (conflict != null) {
                                    ScaffoldMessenger.of(ctx).showSnackBar(
                                      SnackBar(
                                        content: Text(
                                          'Conflicts with $conflict',
                                        ),
                                        backgroundColor: Colors.red,
                                      ),
                                    );
                                    return;
                                  }
                                  try {
                                    await vm.updateLearningSchedule(
                                      schedule.id,
                                      label: label.trim(),
                                      slots: slots
                                          .map(
                                            (s) => ScheduleSlot(
                                              day: s.day,
                                              time: _formatTimeStatic(s.time),
                                              durationMinutes:
                                                  s.durationMinutes,
                                            ),
                                          )
                                          .toList(),
                                    );
                                    if (ctx.mounted) {
                                      Navigator.pop(ctx);
                                      ScaffoldMessenger.of(
                                        context,
                                      ).showSnackBar(
                                        const SnackBar(
                                          content: Text('Schedule updated'),
                                          backgroundColor: Colors.green,
                                        ),
                                      );
                                    }
                                  } catch (e) {
                                    if (ctx.mounted) {
                                      ScaffoldMessenger.of(ctx).showSnackBar(
                                        SnackBar(
                                          content: Text(
                                            'Failed to save: ${_friendlyErrorMessage(e)}',
                                          ),
                                          backgroundColor: Colors.red,
                                        ),
                                      );
                                    }
                                  }
                                },
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: AppColors.primary,
                                  foregroundColor: Colors.white,
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  padding: const EdgeInsets.symmetric(
                                    vertical: 12,
                                  ),
                                ),
                                child: const Text('Save'),
                              ),
                            ),
                          ],
                        ),
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildReadOnlySlotRow(_SlotData slot) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textColor = Theme.of(context).textTheme.bodyMedium?.color;
    final subColor = isDark
        ? AppColors.secondaryTextDark
        : AppColors.secondaryTextLight;

    return Container(
      margin: const EdgeInsets.only(bottom: 6), // reduced from 10
      padding: const EdgeInsets.symmetric(
        horizontal: 10,
        vertical: 6,
      ), // reduced
      decoration: BoxDecoration(
        color: isDark ? AppColors.cardElevatedDark : Colors.grey.shade50,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: isDark ? AppColors.borderDark : AppColors.borderLight,
        ),
      ),
      child: Row(
        children: [
          // Day chip – smaller
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: AppColors.primary.withOpacity(0.12),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              fullDayNames[slot.day],
              style: const TextStyle(
                fontWeight: FontWeight.w600,
                fontSize: 11,
                color: AppColors.primary,
              ),
            ),
          ),
          const SizedBox(width: 8), // reduced
          // Time and duration – now tightly packed
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.access_time, size: 14, color: AppColors.primary),
              const SizedBox(width: 4),
              Text(
                slot.time.format(context),
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                  color: textColor,
                ),
              ),
              const SizedBox(width: 12), // reduced separator
              const Icon(
                Icons.timer_outlined,
                size: 14,
                color: AppColors.primary,
              ),
              const SizedBox(width: 4),
              Text(
                '${slot.durationMinutes} min',
                style: TextStyle(fontSize: 12, color: subColor),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildEditableSlotRow(
    _SlotData slot,
    StateSetter setSheetState,
    List<_SlotData> slots,
  ) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textColor = Theme.of(context).textTheme.bodyMedium?.color;
    final bgColor = isDark ? AppColors.cardElevatedDark : Colors.grey.shade50;
    final borderColor = isDark ? AppColors.borderDark : AppColors.borderLight;

    return Container(
      margin: const EdgeInsets.only(bottom: 4), // tight gap between tiles
      padding: const EdgeInsets.symmetric(
        horizontal: 10,
        vertical: 6,
      ), // minimal padding
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: borderColor),
      ),
      child: Row(
        children: [
          // Day label
          Text(
            fullDayNames[slot.day],
            style: TextStyle(
              fontWeight: FontWeight.w600,
              fontSize: 13,
              color: AppColors.primary,
            ),
          ),
          const SizedBox(width: 12),
          // Time – tappable
          GestureDetector(
            onTap: () async {
              final picked = await showTimePicker(
                context: context,
                initialTime: slot.time,
              );
              if (picked != null) setSheetState(() => slot.time = picked);
            },
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.access_time,
                  size: 14,
                  color: AppColors.primary,
                ),
                const SizedBox(width: 4),
                Text(
                  slot.time.format(context),
                  style: TextStyle(fontSize: 13, color: textColor),
                ),
              ],
            ),
          ),
          const SizedBox(width: 16),
          // Duration – tappable
          GestureDetector(
            onTap: () async {
              int temp = slot.durationMinutes;
              await showModalBottomSheet(
                context: context,
                backgroundColor: isDark ? AppColors.cardDark : Colors.white,
                builder: (_) => StatefulBuilder(
                  builder: (dCtx, setDurationState) => Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'Duration',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: textColor,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            IconButton(
                              icon: const Icon(Icons.remove),
                              color: textColor,
                              onPressed: () => setDurationState(
                                () => temp = (temp - 15).clamp(15, 480),
                              ),
                            ),
                            Text(
                              '$temp min',
                              style: TextStyle(fontSize: 20, color: textColor),
                            ),
                            IconButton(
                              icon: const Icon(Icons.add),
                              color: textColor,
                              onPressed: () => setDurationState(
                                () => temp = (temp + 15).clamp(15, 480),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        ElevatedButton(
                          onPressed: () => Navigator.pop(dCtx),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppColors.primary,
                            foregroundColor: Colors.white,
                          ),
                          child: const Text('Set'),
                        ),
                      ],
                    ),
                  ),
                ),
              );
              setSheetState(() => slot.durationMinutes = temp);
            },
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.timer_outlined,
                  size: 14,
                  color: AppColors.primary,
                ),
                const SizedBox(width: 4),
                Text(
                  '${slot.durationMinutes} min',
                  style: TextStyle(fontSize: 13, color: textColor),
                ),
              ],
            ),
          ),
          const Spacer(),
          // Delete icon – small
          IconButton(
            icon: const Icon(Icons.close, size: 16, color: Colors.red),
            onPressed: () => setSheetState(
              () => slots.removeWhere((s) => s.day == slot.day),
            ),
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
          ),
        ],
      ),
    );
  }

  // ==================== CONFLICT DETECTION ====================
  String? _findScheduleConflict(
    SettingsViewModel vm,
    List<_SlotData> slots, {
    String? excludeId,
  }) {
    for (final existing in vm.settings.learningSchedules) {
      if (existing.id == excludeId) continue;
      for (final exSlot in existing.slots) {
        final exTime = _parseTimeStatic(exSlot.time);
        for (final newSlot in slots) {
          if (newSlot.day != exSlot.day) continue;
          if (_slotsOverlap(
            newSlot.time,
            newSlot.durationMinutes,
            exTime,
            exSlot.durationMinutes,
          )) {
            return '"${existing.label}" on ${fullDayNames[newSlot.day]} at ${exTime.format(context)}';
          }
        }
      }
    }
    return null;
  }

  bool _slotsOverlap(TimeOfDay aStart, int aDur, TimeOfDay bStart, int bDur) {
    final aStartMin = aStart.hour * 60 + aStart.minute;
    final aEndMin = aStartMin + aDur;
    final bStartMin = bStart.hour * 60 + bStart.minute;
    final bEndMin = bStartMin + bDur;
    return aStartMin < bEndMin && bStartMin < aEndMin;
  }

  TimeOfDay _parseTimeStatic(String timeStr) {
    final parts = timeStr.split(':');
    return TimeOfDay(hour: int.parse(parts[0]), minute: int.parse(parts[1]));
  }

  String _formatTimeStatic(TimeOfDay time) {
    return '${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}';
  }

  // ==================== HELPER WIDGETS ====================
  Widget _buildSheetHandle(bool isDark) {
    return Center(
      child: Container(
        margin: const EdgeInsets.only(top: 12),
        width: 40,
        height: 4,
        decoration: BoxDecoration(
          color: isDark ? AppColors.borderDark : AppColors.borderLight,
          borderRadius: BorderRadius.circular(2),
        ),
      ),
    );
  }

  Widget _buildSaveCancelButtons(
    BuildContext ctx, {
    required VoidCallback onSave,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      child: Row(
        children: [
          Expanded(
            child: OutlinedButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel'),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: ElevatedButton(
              onPressed: onSave,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.primary,
              ),
              child: const Text('Save'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTimePickerTile({
    required String label,
    required TimeOfDay time,
    required Function(TimeOfDay) onChanged,
  }) {
    return InkWell(
      onTap: () async {
        final picked = await showTimePicker(
          context: context,
          initialTime: time,
          builder: (context, child) => Theme(
            data: Theme.of(context).copyWith(
              timePickerTheme: TimePickerThemeData(
                backgroundColor: Theme.of(context).brightness == Brightness.dark
                    ? AppColors.cardDark
                    : Colors.white,
              ),
            ),
            child: child!,
          ),
        );
        if (picked != null) onChanged(picked);
      },
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 12),
        decoration: BoxDecoration(
          border: Border.all(color: Colors.grey.shade300),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            Icon(Icons.access_time, size: 18, color: AppColors.primary),
            const SizedBox(width: 8),
            Text(label),
            const Spacer(),
            Text(
              _formatTimeOfDay(time),
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ],
        ),
      ),
    );
  }

  // ==================== UTILITIES ====================
  String _formatTimeOfDay(TimeOfDay time) {
    final hour = time.hourOfPeriod == 0 ? 12 : time.hourOfPeriod;
    final minute = time.minute.toString().padLeft(2, '0');
    final period = time.period == DayPeriod.am ? 'AM' : 'PM';
    return '$hour:$minute $period';
  }

  String _friendlyErrorMessage(Object error) {
    final raw = error.toString();
    final cleaned = raw.replaceFirst(RegExp(r'^(Exception:|Error:)\s*'), '');
    final lower = cleaned.toLowerCase();
    if (lower.contains('linked to an active learning plan') ||
        lower.contains('active learning plan')) {
      return 'This schedule is linked to an active learning plan. Pause, complete, or delete that plan before changing its times.';
    }
    return cleaned;
  }

  // ==================== GENERIC BOTTOM SHEETS ====================
  void _showOptionsSheet({
    required String title,
    required List<String> options,
    required String selected,
    required List<String> labels,
    required List<IconData> icons,
    required ValueChanged<String> onSelect,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bg = isDark ? AppColors.cardDark : Colors.white;
    final primaryText = isDark
        ? AppColors.primaryTextDark
        : AppColors.primaryTextLight;
    final secondaryText = isDark
        ? AppColors.secondaryTextDark
        : AppColors.secondaryTextLight;
    final border = isDark ? AppColors.borderDark : AppColors.borderLight;

    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (_) => Container(
        decoration: BoxDecoration(
          color: bg,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        ),
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: border,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Text(
              title,
              style: AppTextStyles.logo.copyWith(
                fontSize: 17,
                color: primaryText,
              ),
            ),
            const SizedBox(height: 16),
            ...List.generate(options.length, (i) {
              final isSelected = options[i] == selected;
              return InkWell(
                onTap: () {
                  Navigator.pop(context);
                  onSelect(options[i]);
                },
                borderRadius: BorderRadius.circular(12),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 180),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 14,
                    vertical: 12,
                  ),
                  margin: const EdgeInsets.only(bottom: 6),
                  decoration: BoxDecoration(
                    color: isSelected
                        ? AppColors.primary.withOpacity(0.1)
                        : Colors.transparent,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: isSelected
                          ? AppColors.primary.withOpacity(0.4)
                          : Colors.transparent,
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        icons[i],
                        size: 20,
                        color: isSelected ? AppColors.primary : secondaryText,
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Text(
                          labels[i],
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: isSelected
                                ? FontWeight.w700
                                : FontWeight.w400,
                            color: isSelected ? AppColors.primary : primaryText,
                          ),
                        ),
                      ),
                      if (isSelected)
                        const Icon(
                          Icons.check_circle_rounded,
                          color: AppColors.primary,
                          size: 18,
                        ),
                    ],
                  ),
                ),
              );
            }),
          ],
        ),
      ),
    );
  }

  void _showDurationPicker({
    required String title,
    required int currentValue,
    required List<int> options,
    required String unit,
    required ValueChanged<int> onSelect,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bg = isDark ? AppColors.cardDark : Colors.white;
    final primaryText = isDark
        ? AppColors.primaryTextDark
        : AppColors.primaryTextLight;
    final border = isDark ? AppColors.borderDark : AppColors.borderLight;

    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (_) => Container(
        decoration: BoxDecoration(
          color: bg,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        ),
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: border,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Text(
              title,
              style: AppTextStyles.logo.copyWith(
                fontSize: 17,
                color: primaryText,
              ),
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: options.map((o) {
                final isSelected = o == currentValue;
                return GestureDetector(
                  onTap: () {
                    Navigator.pop(context);
                    onSelect(o);
                  },
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 180),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 20,
                      vertical: 10,
                    ),
                    decoration: BoxDecoration(
                      color: isSelected
                          ? AppColors.primary
                          : (isDark
                                ? AppColors.cardElevatedDark
                                : const Color(0xFFF3F4F6)),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: isSelected ? AppColors.primary : border,
                      ),
                    ),
                    child: Text(
                      '$o $unit',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: isSelected ? Colors.white : primaryText,
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }

  void _showConfirmDialog({
    required String title,
    required String message,
    required String confirmLabel,
    required Color confirmColor,
    required Future<void> Function() onConfirm,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bg = isDark ? AppColors.cardDark : Colors.white;
    final primaryText = isDark
        ? AppColors.primaryTextDark
        : AppColors.primaryTextLight;
    final secondaryText = isDark
        ? AppColors.secondaryTextDark
        : AppColors.secondaryTextLight;

    showDialog(
      context: context,
      builder: (dialogContext) => Dialog(
        backgroundColor: bg,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  color: confirmColor.withOpacity(0.1),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.warning_amber_rounded,
                  color: confirmColor,
                  size: 26,
                ),
              ),
              const SizedBox(height: 16),
              Text(
                title,
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                  color: primaryText,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                message,
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 13,
                  color: secondaryText,
                  height: 1.5,
                ),
              ),
              const SizedBox(height: 24),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () => Navigator.pop(dialogContext),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: primaryText,
                        side: BorderSide(
                          color: isDark
                              ? AppColors.borderDark
                              : AppColors.borderLight,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        padding: const EdgeInsets.symmetric(vertical: 12),
                      ),
                      child: const Text('Cancel'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton(
                      onPressed: () async {
                        Navigator.pop(dialogContext);
                        await onConfirm();
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: confirmColor,
                        foregroundColor: Colors.white,
                        elevation: 0,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        padding: const EdgeInsets.symmetric(vertical: 12),
                      ),
                      child: Text(confirmLabel),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SlotData {
  final int day;
  TimeOfDay time;
  int durationMinutes;

  _SlotData({
    required this.day,
    required this.time,
    required this.durationMinutes,
  });
}

class _NewSlotData {
  final int day;
  TimeOfDay? time;
  int? durationMinutes;

  _NewSlotData({
    required this.day,
    // this.time, this.durationMinutes
  });
}

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
                  content: Text('Failed to update theme: $e'),
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
        enabled: settings.notificationsEnabled, // 👈 ADD THIS LINE
        onToggle: (v) async => vm.updatePushNotificationsEnabled(v),
      ),
      SettingTileData(
        icon: Icons.email_outlined,
        iconColor: const Color(0xFFF59E0B),
        label: 'Email Notifications',
        subtitle: 'Summaries sent to your email',
        toggleValue: settings.emailNotificationsEnabled,
        enabled: settings.notificationsEnabled, // 👈 ADD THIS LINE
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
                            content: Text('Logout failed: $e'),
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
                            content: Text('Account deletion failed: $e'),
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
                              content: Text('Failed to save: $e'),
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
        return StatefulBuilder(
          builder: (ctx, setSheetState) {
            return Container(
              decoration: BoxDecoration(
                color: isDark ? Colors.grey[900] : Colors.white,
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
                        const Text(
                          'Learning Schedules',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.add),
                          onPressed: () async {
                            await vm.createLearningSchedule('New Schedule', [
                              ScheduleSlot(
                                day: 0,
                                time: '09:00',
                                durationMinutes: 60,
                              ),
                            ]);
                            setSheetState(() {});
                          },
                        ),
                      ],
                    ),
                  ),
                  if (vm.settings.learningSchedules.isEmpty)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 40),
                      child: Column(
                        children: [
                          Icon(Icons.schedule, size: 48, color: Colors.grey),
                          SizedBox(height: 12),
                          Text(
                            'No learning schedules',
                            style: TextStyle(color: Colors.grey),
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
                        itemCount: vm.settings.learningSchedules.length,
                        itemBuilder: (_, idx) => _EditableScheduleTile(
                          schedule: vm.settings.learningSchedules[idx],
                          vm: vm,
                          onRefresh: () => setSheetState(() {}),
                          isDark: isDark,
                        ),
                      ),
                    ),
                ],
              ),
            );
          },
        );
      },
    );
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
    final hour = time.hourOfPeriod;
    final minute = time.minute.toString().padLeft(2, '0');
    final period = time.period == DayPeriod.am ? 'AM' : 'PM';
    return '$hour:$minute $period';
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

class _EditableScheduleTile extends StatefulWidget {
  final LearningSchedule schedule;
  final SettingsViewModel vm;
  final VoidCallback onRefresh;
  final bool isDark;

  const _EditableScheduleTile({
    required this.schedule,
    required this.vm,
    required this.onRefresh,
    required this.isDark,
  });

  @override
  State<_EditableScheduleTile> createState() => _EditableScheduleTileState();
}

class _EditableScheduleTileState extends State<_EditableScheduleTile> {
  late String label;
  late List<_SlotData> slots; // List of slot data for selected days
  final List<String> fullDayNames = [
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
    label = widget.schedule.label;

    // Initialize slots from existing schedule slots
    slots = widget.schedule.slots.map((s) {
      final time = _parseTime(s.time);
      return _SlotData(
        day: s.day,
        time: time,
        durationMinutes: s.durationMinutes,
      );
    }).toList();

    // If no slots exist, add a default slot for Monday (day 0) as a starting point
    if (slots.isEmpty) {
      slots.add(
        _SlotData(
          day: 0,
          time: const TimeOfDay(hour: 9, minute: 0),
          durationMinutes: 60,
        ),
      );
    }
  }

  TimeOfDay _parseTime(String timeStr) {
    final parts = timeStr.split(':');
    return TimeOfDay(hour: int.parse(parts[0]), minute: int.parse(parts[1]));
  }

  String _formatTime(TimeOfDay time) {
    return '${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}';
  }

  // Toggle a day: add or remove a slot
  void _toggleDay(int day, bool selected) {
    setState(() {
      if (selected) {
        // Add a default slot if not already present
        if (!slots.any((s) => s.day == day)) {
          slots.add(
            _SlotData(
              day: day,
              time: const TimeOfDay(hour: 9, minute: 0),
              durationMinutes: 60,
            ),
          );
        }
      } else {
        slots.removeWhere((s) => s.day == day);
      }
    });
  }

  bool _isDaySelected(int day) {
    return slots.any((s) => s.day == day);
  }

  void _updateSlotTime(int day, TimeOfDay newTime) {
    setState(() {
      final index = slots.indexWhere((s) => s.day == day);
      if (index != -1) {
        slots[index].time = newTime;
      }
    });
  }

  void _updateSlotDuration(int day, int newDuration) {
    setState(() {
      final index = slots.indexWhere((s) => s.day == day);
      if (index != -1) {
        slots[index].durationMinutes = newDuration;
      }
    });
  }

  void _removeSlot(int day) {
    setState(() {
      slots.removeWhere((s) => s.day == day);
    });
  }

  @override
  Widget build(BuildContext context) {
    final labelController = TextEditingController(text: label);

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      color: widget.isDark ? Colors.grey[850] : Colors.grey[50],
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ---- Label row ----
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: labelController,
                    decoration: const InputDecoration(
                      hintText: 'Schedule label',
                      border: InputBorder.none,
                    ),
                    onChanged: (value) => label = value,
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.delete_outline, color: Colors.red),
                  onPressed: () async {
                    await widget.vm.deleteLearningSchedule(widget.schedule.id);
                    widget.onRefresh();
                  },
                ),
              ],
            ),
            const SizedBox(height: 8),

            // ---- Day selection chips ----
            const Text(
              'Select days',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: List.generate(7, (day) {
                final isSelected = _isDaySelected(day);
                return FilterChip(
                  label: Text(fullDayNames[day]),
                  selected: isSelected,
                  onSelected: (selected) => _toggleDay(day, selected),
                );
              }),
            ),
            const SizedBox(height: 12),

            // ---- Slots for selected days ----
            if (slots.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 12),
                child: Text('Select at least one day above'),
              )
            else
              Column(
                children: slots.map((slot) {
                  return _buildSlotRow(slot);
                }).toList(),
              ),
            const SizedBox(height: 12),

            // ---- Save button ----
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () async {
                  // Build list of ScheduleSlot from the slots data
                  final scheduleSlots = slots.map((s) {
                    return ScheduleSlot(
                      day: s.day,
                      time: _formatTime(s.time),
                      durationMinutes: s.durationMinutes,
                    );
                  }).toList();

                  await widget.vm.updateLearningSchedule(
                    widget.schedule.id,
                    label: label,
                    slots: scheduleSlots,
                  );
                  widget.onRefresh();
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Schedule updated')),
                  );
                },
                child: const Text('Save Changes'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // Build a single slot row with day label, time picker, duration picker, and remove button
  Widget _buildSlotRow(_SlotData slot) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: widget.isDark ? Colors.grey[800] : Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: Row(
        children: [
          // Day label (fixed width)
          SizedBox(
            width: 70,
            child: Text(
              fullDayNames[slot.day],
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
          const SizedBox(width: 8),

          // Time picker
          Flexible(
            flex: 1,
            child: InkWell(
              onTap: () async {
                final picked = await showTimePicker(
                  context: context,
                  initialTime: slot.time,
                );
                if (picked != null) {
                  _updateSlotTime(slot.day, picked);
                }
              },
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 8),
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.grey.shade300),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.access_time, size: 16),
                    const SizedBox(width: 4),
                    Text(slot.time.format(context)),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),

          // Duration picker
          Flexible(
            flex: 1,
            child: InkWell(
              onTap: () => _showDurationPickerForSlot(slot),
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 8),
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.grey.shade300),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.timer_outlined, size: 16),
                    const SizedBox(width: 4),
                    Text('${slot.durationMinutes} min'),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(width: 4),
          // Remove this slot button
          IconButton(
            icon: const Icon(Icons.close, size: 18),
            onPressed: () => _removeSlot(slot.day),
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
            color: Colors.red,
          ),
        ],
      ),
    );
  }

  void _showDurationPickerForSlot(_SlotData slot) {
    int temp = slot.durationMinutes;
    showModalBottomSheet(
      context: context,
      builder: (_) => StatefulBuilder(
        builder: (ctx, setState) => Container(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'Duration',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 20),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  IconButton(
                    icon: const Icon(Icons.remove),
                    onPressed: () =>
                        setState(() => temp = (temp - 15).clamp(15, 480)),
                  ),
                  Text('$temp min', style: const TextStyle(fontSize: 24)),
                  IconButton(
                    icon: const Icon(Icons.add),
                    onPressed: () =>
                        setState(() => temp = (temp + 15).clamp(15, 480)),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: () {
                  _updateSlotDuration(slot.day, temp);
                  Navigator.pop(ctx);
                },
                child: const Text('Set'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

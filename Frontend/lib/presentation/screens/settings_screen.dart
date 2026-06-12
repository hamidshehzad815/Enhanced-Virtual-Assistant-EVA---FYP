import 'package:flutter/material.dart';
import '../../core/theme/app_colours.dart';
import '../../core/theme/app_text_style.dart';
import '../../data/models/setting_model.dart';
import '../widgets/settings_widgets.dart';
import 'package:provider/provider.dart';
import '../providers/theme_provider.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late SettingsModel _settings;

  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';

  @override
  void initState() {
    super.initState();
    _settings = SettingsModel();
    _searchController.addListener(() {
      setState(() => _searchQuery = _searchController.text.toLowerCase());
    });

    WidgetsBinding.instance.addPostFrameCallback((_) {
      final themeProvider = context.read<ThemeProvider>();

      setState(() {
        if (themeProvider.themeMode == ThemeMode.dark) {
          _settings.theme = 'dark';
        } else if (themeProvider.themeMode == ThemeMode.light) {
          _settings.theme = 'light';
        } else {
          _settings.theme = 'system';
        }
      });
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _save() {
    debugPrint('Settings saved: ${_settings.toJson()}');
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: SafeArea(
        child: Column(
          children: [
            _buildHeader(isDark),
            SettingsSearchBar(
              controller: _searchController,
              searchQuery: _searchQuery,
              onClear: () {
                _searchController.clear();
                setState(() => _searchQuery = '');
              },
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
                children: [
                  SettingsProfileCard(
                    isDark: isDark,
                    searchQuery: _searchQuery,
                  ),
                  const SizedBox(height: 20),
                  SettingsSection(
                    isDark: isDark,
                    icon: Icons.tune_rounded,
                    iconColor: const Color(0xFF3B82F6),
                    title: 'App Preferences',
                    tiles: _appPreferenceTiles(isDark),
                    searchQuery: _searchQuery,
                  ),
                  const SizedBox(height: 20),
                  SettingsSection(
                    isDark: isDark,
                    icon: Icons.notifications_outlined,
                    iconColor: const Color(0xFFF59E0B),
                    title: 'Notifications',
                    tiles: _notificationTiles(isDark),
                    searchQuery: _searchQuery,
                  ),
                  const SizedBox(height: 20),
                  SettingsSection(
                    isDark: isDark,
                    icon: Icons.school_outlined,
                    iconColor: const Color(0xFF8B5CF6),
                    title: 'Tasks Scheduling',
                    tiles: _learningTiles(isDark),
                    searchQuery: _searchQuery,
                  ),
                  const SizedBox(height: 20),
                  SettingsSection(
                    isDark: isDark,
                    icon: Icons.assignment_rounded,
                    iconColor: const Color.fromARGB(255, 187, 91, 104),
                    title: 'Learning Scheduling',
                    tiles: _scheduleTiles(isDark),
                    searchQuery: _searchQuery,
                  ),
                  const SizedBox(height: 20),
                  SettingsSection(
                    isDark: isDark,
                    icon: Icons.lock_outline_rounded,
                    iconColor: const Color(0xFF22C55E),
                    title: 'Privacy & Social',
                    tiles: _privacyTiles(isDark),
                    searchQuery: _searchQuery,
                  ),
                  const SizedBox(height: 20),
                  SettingsSection(
                    isDark: isDark,
                    icon: Icons.info_outline_rounded,
                    iconColor: const Color(0xFF6B7280),
                    title: 'About',
                    tiles: _aboutTiles(isDark),
                    searchQuery: _searchQuery,
                  ),
                  const SizedBox(height: 20),
                  _buildDangerZone(isDark),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ========================= HEADER =========================
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

  // ========================= APP PREFERENCES =========================
  List<SettingTileData> _appPreferenceTiles(bool isDark) => [
    SettingTileData(
      icon: Icons.palette_outlined,
      iconColor: const Color(0xFF3B82F6),
      label: 'Theme',
      subtitle: 'Controls app appearance',
      valueBadge:
          _settings.theme[0].toUpperCase() + _settings.theme.substring(1),
      onTap: () => _showOptionsSheet(
        title: 'Theme',
        options: const ['light', 'dark', 'system'],
        selected: _settings.theme,
        labels: const ['Light', 'Dark', 'System default'],
        icons: const [
          Icons.light_mode_rounded,
          Icons.dark_mode_rounded,
          Icons.phone_android_rounded,
        ],
        onSelect: (v) {
          setState(() {
            _settings.theme = v;
          });

          _save();

          Provider.of<ThemeProvider>(context, listen: false).setTheme(v);
        },
      ),
    ),
    SettingTileData(
      icon: Icons.sync_rounded,
      iconColor: const Color(0xFF3B82F6),
      label: 'Google Calendar Sync',
      subtitle: 'Sync tasks to Google Calendar',
      toggleValue: _settings.googleCalendarSyncEnabled,
      onToggle: (v) => setState(() {
        _settings.googleCalendarSyncEnabled = v;
        _save();
      }),
    ),
    SettingTileData(
      icon: Icons.show_chart_outlined,
      iconColor: const Color(0xFF3B82F6),
      label: 'Allow Behavioural Insights',
      subtitle: 'Let Eva analyze your learning patterns',
      toggleValue: _settings.behavioralAnalyticsEnabled,
      onToggle: (v) => setState(() {
        _settings.behavioralAnalyticsEnabled = v;
        _save();
      }),
    ),
  ];

  // ========================= NOTIFICATIONS =========================
  List<SettingTileData> _notificationTiles(bool isDark) {
    final tiles = [
      SettingTileData(
        icon: Icons.notifications_active_outlined,
        iconColor: const Color(0xFFF59E0B),
        label: 'All Notifications',
        subtitle: 'Master toggle for all alerts',
        toggleValue: _settings.notificationsEnabled,
        onToggle: (v) => setState(() {
          _settings.notificationsEnabled = v;
          _save();
        }),
      ),
      SettingTileData(
        icon: Icons.phone_android_rounded,
        iconColor: const Color(0xFFF59E0B),
        label: 'Push Notifications',
        subtitle: 'Alerts on your device',
        toggleValue: _settings.pushNotificationsEnabled,
        onToggle: (v) => setState(() {
          _settings.pushNotificationsEnabled = v;
          _save();
        }),
      ),
      SettingTileData(
        icon: Icons.email_outlined,
        iconColor: const Color(0xFFF59E0B),
        label: 'Email Notifications',
        subtitle: 'Summaries sent to your email',
        toggleValue: _settings.emailNotificationsEnabled,
        onToggle: (v) => setState(() {
          _settings.emailNotificationsEnabled = v;
          _save();
        }),
      ),
      // Master toggle for Quiet Hours
      SettingTileData(
        icon: Icons.bedtime_outlined,
        iconColor: const Color(0xFFF59E0B),
        label: 'Quiet Hours',
        subtitle: 'Silence notifications during defined intervals',
        toggleValue: _settings.quietHoursEnabled,
        onToggle: (v) => setState(() {
          _settings.quietHoursEnabled = v;
          _save();
        }),
      ),
    ];

    // Show management tile only if quiet hours are enabled
    if (_settings.quietHoursEnabled) {
      tiles.add(
        SettingTileData(
          icon: Icons.edit_calendar_rounded,
          iconColor: const Color(0xFFF59E0B),
          label: 'Manage Quiet Hours',
          subtitle: 'Add or remove intervals',
          valueBadge: '${_settings.quietHours.length} interval(s)',
          onTap: () => _showQuietHoursManager(),
        ),
      );
    }

    return tiles;
  }

  // ========================= TASKS SCHEDULING =========================
  List<SettingTileData> _learningTiles(bool isDark) => [
    SettingTileData(
      icon: Icons.alarm_rounded,
      iconColor: const Color(0xFF8B5CF6),
      label: 'Default Reminder',
      subtitle: 'Before tasks & exams',
      valueBadge: '${_settings.defaultReminderMinutes} min',
      onTap: () => _showDurationPicker(
        title: 'Default Reminder Time',
        currentValue: _settings.defaultReminderMinutes,
        options: const [5, 10, 15, 30, 60, 120],
        unit: 'min',
        onSelect: (v) => setState(() {
          _settings.defaultReminderMinutes = v;
          _save();
        }),
      ),
    ),
    SettingTileData(
      icon: Icons.timer_outlined,
      iconColor: const Color(0xFF8B5CF6),
      label: 'Default Task Duration',
      valueBadge: '${_settings.defaultTaskDuration} min',
      onTap: () => _showDurationPicker(
        title: 'Default Task Duration',
        currentValue: _settings.defaultTaskDuration,
        options: const [30, 60, 90, 120, 180, 240],
        unit: 'min',
        onSelect: (v) => setState(() {
          _settings.defaultTaskDuration = v;
          _save();
        }),
      ),
    ),
  ];

  // ========================= LEARNING SCHEDULING (MULTI-SLOT) =========================
  List<SettingTileData> _scheduleTiles(bool isDark) => [
    SettingTileData(
      icon: Icons.schedule_rounded,
      iconColor: const Color.fromARGB(255, 187, 91, 104),
      label: 'Learning Schedules',
      subtitle: 'Define multiple study slots',
      valueBadge: '${_settings.learningSchedules.length} learning schedule',
      onTap: () => _showLearningSchedulesManager(),
    ),
    SettingTileData(
      icon: Icons.menu_book_rounded,
      iconColor: const Color.fromARGB(255, 187, 91, 104),
      label: 'Learning Reminder Time',
      subtitle: 'Before study sessions',
      valueBadge: '${_settings.defaultTopicReminderMinutes} min',
      onTap: () => _showDurationPicker(
        title: 'Reminder Time',
        currentValue: _settings.defaultTopicReminderMinutes,
        options: const [5, 10, 15, 30, 60],
        unit: 'min',
        onSelect: (v) => setState(() {
          _settings.defaultTopicReminderMinutes = v;
          _save();
        }),
      ),
    ),
  ];

  // ========================= PRIVACY & SOCIAL =========================
  List<SettingTileData> _privacyTiles(bool isDark) => [
    SettingTileData(
      icon: Icons.group,
      iconColor: const Color(0xFF22C55E),
      label: 'Allow Friends Request',
      toggleValue: _settings.allowFriendRequests,
      onToggle: (v) => setState(() {
        _settings.allowFriendRequests = v;
        _save();
      }),
    ),
    // SettingTileData(
    //   icon: Icons.access_time_rounded,
    //   iconColor: const Color(0xFF22C55E),
    //   label: 'Show Last Active',
    //   subtitle: 'Let others see when you were online',
    //   toggleValue: _settings.showLastActive,
    //   onToggle: (v) => setState(() {
    //     _settings.showLastActive = v;
    //     _save();
    //   }),
    // ),
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
  Widget _buildDangerZone(bool isDark) {
    if (_searchQuery.isNotEmpty) return const SizedBox.shrink();

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
                  onConfirm: () {},
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
                  onConfirm: () {},
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

  // ========================= HELPER WIDGETS =========================
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

  Widget _buildDurationPickerTile({
    required int minutes,
    required ValueChanged<int> onChanged,
  }) {
    return InkWell(
      onTap: () => _showDurationPickerForSchedule(
        title: 'Duration',
        currentValue: minutes,
        onSelect: onChanged,
      ),
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 12),
        decoration: BoxDecoration(
          border: Border.all(color: Colors.grey.shade300),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            Icon(Icons.timer_outlined, size: 18, color: AppColors.primary),
            const SizedBox(width: 8),
            const Text('Duration'),
            const Spacer(),
            Text(
              '$minutes min',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ],
        ),
      ),
    );
  }

  // ========================= QUIET HOURS MANAGER =========================
  void _showQuietHoursManager() {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final List<QuietHourInterval> tempList = List.from(_settings.quietHours);

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
                          onPressed: () =>
                              _addQuietHour(ctx, setSheetState, tempList),
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
                        ),
                      ),
                    ),
                  _buildSaveCancelButtons(
                    ctx,
                    onSave: () {
                      setState(() {
                        _settings.quietHours = tempList;
                        _save();
                      });
                      Navigator.pop(ctx);
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

  void _addQuietHour(
    BuildContext ctx,
    StateSetter setSheetState,
    List<QuietHourInterval> list,
  ) {
    setSheetState(() {
      list.add(
        QuietHourInterval(
          label: 'New Interval',
          startTime: const TimeOfDay(hour: 22, minute: 0),
          endTime: const TimeOfDay(hour: 7, minute: 0),
          enabled: true, // explicit
        ),
      );
    });
  }

  Widget _buildQuietHourTile(
    BuildContext ctx,
    int index,
    List<QuietHourInterval> list,
    StateSetter setSheetState,
  ) {
    final interval = list[index];
    final isDark = Theme.of(context).brightness == Brightness.dark;
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
                Expanded(
                  child: TextField(
                    controller: controller,
                    textDirection: TextDirection.ltr,
                    textAlign: TextAlign.start,
                    decoration: const InputDecoration(
                      hintText: 'Label (e.g., Sleeping)',
                      hintTextDirection: TextDirection.ltr,
                      border: InputBorder.none,
                      isDense: true,
                    ),
                    style: const TextStyle(fontWeight: FontWeight.w500),
                    onChanged: (value) {
                      interval.label = value;
                    },
                  ),
                ),
                // Per-interval toggle
                Switch(
                  value: interval.enabled,
                  onChanged: (val) =>
                      setSheetState(() => interval.enabled = val),
                  activeColor: AppColors.primary,
                ),
                IconButton(
                  icon: const Icon(Icons.delete_outline, size: 20),
                  onPressed: () {
                    setSheetState(() {
                      list.removeAt(index);
                    });
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

  // ========================= LEARNING SCHEDULES MANAGER =========================
  void _showLearningSchedulesManager() {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final List<LearningSchedule> tempList = List.from(
      _settings.learningSchedules,
    );

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
                          'Learning Schedules',
                          style: AppTextStyles.logo.copyWith(fontSize: 18),
                        ),
                        IconButton(
                          icon: const Icon(Icons.add_circle_outline),
                          onPressed: () => _addLearningSchedule(
                            ctx,
                            setSheetState,
                            tempList,
                          ),
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
                            Icons.schedule_rounded,
                            size: 48,
                            color: Colors.grey.shade400,
                          ),
                          const SizedBox(height: 12),
                          Text(
                            'No learning schedules defined',
                            style: TextStyle(color: Colors.grey.shade500),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'Tap + to add a schedule',
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
                        itemBuilder: (_, idx) => _buildLearningScheduleTile(
                          ctx,
                          idx,
                          tempList,
                          setSheetState,
                        ),
                      ),
                    ),
                  _buildSaveCancelButtons(
                    ctx,
                    onSave: () {
                      setState(() {
                        _settings.learningSchedules = tempList;
                        _save();
                      });
                      Navigator.pop(ctx);
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

  void _addLearningSchedule(
    BuildContext ctx,
    StateSetter setSheetState,
    List<LearningSchedule> list,
  ) {
    setSheetState(() {
      list.add(
        LearningSchedule(
          label: 'New Schedule',
          days: ['monday', 'wednesday', 'friday'],
          startTime: const TimeOfDay(hour: 9, minute: 0),
          durationMinutes: 60,
        ),
      );
    });
  }

  Widget _buildLearningScheduleTile(
    BuildContext ctx,
    int index,
    List<LearningSchedule> list,
    StateSetter setSheetState,
  ) {
    final schedule = list[index];
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final allDays = [
      'monday',
      'tuesday',
      'wednesday',
      'thursday',
      'friday',
      'saturday',
      'sunday',
    ];
    final Map<String, String> dayLabels = {
      'monday': 'Monday',
      'tuesday': 'Tuesday',
      'wednesday': 'Wednesday',
      'thursday': 'Thursday',
      'friday': 'Friday',
      'saturday': 'Saturday',
      'sunday': 'Sunday',
    };

    final controller = TextEditingController(text: schedule.label);

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      color: isDark ? AppColors.cardElevatedDark : Colors.grey.shade50,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: controller,
                    textDirection: TextDirection.ltr,
                    textAlign: TextAlign.start,
                    decoration: const InputDecoration(
                      hintText: 'Slot label (e.g., Morning Study)',
                      hintTextDirection: TextDirection.ltr,
                      border: InputBorder.none,
                    ),
                    onChanged: (value) {
                      schedule.label = value;
                    },
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.delete_outline),
                  onPressed: () {
                    setSheetState(() {
                      list.removeAt(index);
                    });
                    controller.dispose();
                  },
                  color: Colors.red.shade400,
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Days',
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: allDays.map((day) {
                final isSelected = schedule.days.contains(day);
                return FilterChip(
                  label: Text(dayLabels[day]!),
                  selected: isSelected,
                  onSelected: (selected) {
                    setSheetState(() {
                      if (selected) {
                        schedule.days.add(day);
                      } else {
                        schedule.days.remove(day);
                      }
                    });
                  },
                  backgroundColor: Colors.transparent,
                  selectedColor: AppColors.primary.withOpacity(0.2),
                  checkmarkColor: AppColors.primary,
                );
              }).toList(),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _buildTimePickerTile(
                    label: 'Start',
                    time: schedule.startTime,
                    onChanged: (t) =>
                        setSheetState(() => schedule.startTime = t),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildDurationPickerTile(
                    minutes: schedule.durationMinutes,
                    onChanged: (mins) =>
                        setSheetState(() => schedule.durationMinutes = mins),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Ends at: ${_computeEndTime(schedule.startTime, schedule.durationMinutes)}',
              style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
            ),
          ],
        ),
      ),
    );
  }

  void _showDurationPickerForSchedule({
    required String title,
    required int currentValue,
    required ValueChanged<int> onSelect,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    int tempValue = currentValue;
    showModalBottomSheet(
      context: context,
      builder: (_) => StatefulBuilder(
        builder: (ctx, setSheetState) => Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: isDark ? AppColors.cardDark : Colors.white,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                title,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 20),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  IconButton(
                    icon: const Icon(Icons.remove_circle_outline),
                    onPressed: () => setSheetState(
                      () => tempValue = (tempValue - 15).clamp(15, 480),
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 20,
                      vertical: 10,
                    ),
                    child: Text(
                      '$tempValue min',
                      style: const TextStyle(fontSize: 20),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.add_circle_outline),
                    onPressed: () => setSheetState(
                      () => tempValue = (tempValue + 15).clamp(15, 480),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: () {
                  onSelect(tempValue);
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

  // ========================= UTILITIES =========================
  String _formatTimeOfDay(TimeOfDay time) {
    final hour = time.hourOfPeriod;
    final minute = time.minute.toString().padLeft(2, '0');
    final period = time.period == DayPeriod.am ? 'AM' : 'PM';
    return '$hour:$minute $period';
  }

  String _computeEndTime(TimeOfDay start, int minutes) {
    final totalMinutes = start.hour * 60 + start.minute + minutes;
    final endHour = (totalMinutes ~/ 60) % 24;
    final endMinute = totalMinutes % 60;
    final period = endHour >= 12 ? 'PM' : 'AM';
    final displayHour = endHour > 12
        ? endHour - 12
        : (endHour == 0 ? 12 : endHour);
    return '$displayHour:${endMinute.toString().padLeft(2, '0')} $period';
  }

  // ========================= GENERIC BOTTOM SHEETS =========================
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
    required VoidCallback onConfirm,
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
      builder: (_) => Dialog(
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
                      onPressed: () => Navigator.pop(context),
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
                      onPressed: () {
                        Navigator.pop(context);
                        onConfirm();
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

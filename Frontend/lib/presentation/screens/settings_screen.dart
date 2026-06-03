import 'package:flutter/material.dart';
// Fonts centralized in AppTextStyles
import '../../core/theme/app_colours.dart';
import '../../core/theme/app_text_style.dart';
import '../../data/models/setting_model.dart';
import '../widgets/settings_widgets.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  // Load from API — using placeholder defaults for now
  late SettingsModel _settings;

  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';

  @override
  void initState() {
    super.initState();
    // TODO: replace with real API call
    // e.g. _settings = SettingsModel.fromJson(apiResponse);
    _settings = SettingsModel();
    _searchController.addListener(() {
      setState(() => _searchQuery = _searchController.text.toLowerCase());
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  // Called after every toggle/change — hook up PATCH API call here
  void _save() {
    // TODO: await ApiService.patchSettings(_settings.toJson());
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

  // ─────────────────────────────────────────────────────────────────────────
  //  HEADER
  // ─────────────────────────────────────────────────────────────────────────
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

  // ─────────────────────────────────────────────────────────────────────────
  //  TILES — App Preferences
  // ─────────────────────────────────────────────────────────────────────────
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
        onSelect: (v) => setState(() {
          _settings.theme = v;
          _save();
        }),
      ),
    ),
    SettingTileData(
      icon: Icons.language_rounded,
      iconColor: const Color(0xFF3B82F6),
      label: 'Language',
      valueBadge: _settings.language.toUpperCase(),
      onTap: () => _showOptionsSheet(
        title: 'Language',
        options: const ['en', 'ar', 'ur'],
        selected: _settings.language,
        labels: const ['English', 'العربية', 'اردو'],
        icons: const [
          Icons.language_rounded,
          Icons.language_rounded,
          Icons.language_rounded,
        ],
        onSelect: (v) => setState(() {
          _settings.language = v;
          _save();
        }),
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
  ];

  // ─────────────────────────────────────────────────────────────────────────
  //  TILES — Notifications
  // ─────────────────────────────────────────────────────────────────────────
  List<SettingTileData> _notificationTiles(bool isDark) => [
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
    SettingTileData(
      icon: Icons.bedtime_outlined,
      iconColor: const Color(0xFFF59E0B),
      label: 'Quiet Hours',
      subtitle: 'Silence notifications at night',
      toggleValue: _settings.quietHoursEnabled,
      onToggle: (v) => setState(() {
        _settings.quietHoursEnabled = v;
        _save();
      }),
    ),
    SettingTileData(
      icon: Icons.alarm_rounded,
      iconColor: const Color(0xFFF59E0B),
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
      icon: Icons.menu_book_rounded,
      iconColor: const Color(0xFFF59E0B),
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

  // ─────────────────────────────────────────────────────────────────────────
  //  TILES — Learning & Tasks
  // ─────────────────────────────────────────────────────────────────────────
  List<SettingTileData> _learningTiles(bool isDark) => [
    SettingTileData(
      icon: Icons.flag_outlined,
      iconColor: const Color(0xFF8B5CF6),
      label: 'Default Task Priority',
      valueBadge:
          _settings.defaultTaskPriority[0].toUpperCase() +
          _settings.defaultTaskPriority.substring(1),
      onTap: () => _showOptionsSheet(
        title: 'Default Priority',
        options: const ['low', 'medium', 'high'],
        selected: _settings.defaultTaskPriority,
        labels: const ['Low', 'Medium', 'High'],
        icons: const [
          Icons.keyboard_arrow_down_rounded,
          Icons.remove_rounded,
          Icons.keyboard_arrow_up_rounded,
        ],
        onSelect: (v) => setState(() {
          _settings.defaultTaskPriority = v;
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
    SettingTileData(
      icon: Icons.wb_sunny_outlined,
      iconColor: const Color(0xFF8B5CF6),
      label: 'Preferred Learning Time',
      valueBadge:
          _settings.preferredLearningTime[0].toUpperCase() +
          _settings.preferredLearningTime.substring(1),
      onTap: () => _showOptionsSheet(
        title: 'Best Learning Time',
        options: const ['morning', 'afternoon', 'evening', 'night'],
        selected: _settings.preferredLearningTime,
        labels: const ['Morning', 'Afternoon', 'Evening', 'Night'],
        icons: const [
          Icons.wb_sunny_rounded,
          Icons.light_mode_rounded,
          Icons.wb_twilight_rounded,
          Icons.nightlight_round,
        ],
        onSelect: (v) => setState(() {
          _settings.preferredLearningTime = v;
          _save();
        }),
      ),
    ),
  ];

  String _getLearningScheduleSummary() {
    final days = _settings.preferredLearningDaysList;
    if (days.isEmpty) return 'Not set';
    final dayNames = days.map((d) => _dayAbbreviation(d)).toList();
    final time = _settings.learningStartTime;
    final timeStr = time != null ? _formatTimeOfDay(time) : 'No time';
    return '${dayNames.join(', ')} at $timeStr';
  }

  String _dayAbbreviation(String day) {
    switch (day.toLowerCase()) {
      case 'monday':
        return 'Mon';
      case 'tuesday':
        return 'Tue';
      case 'wednesday':
        return 'Wed';
      case 'thursday':
        return 'Thu';
      case 'friday':
        return 'Fri';
      case 'saturday':
        return 'Sat';
      case 'sunday':
        return 'Sun';
      default:
        return day;
    }
  }

  String _formatTimeOfDay(TimeOfDay time) {
    final hour = time.hourOfPeriod;
    final minute = time.minute.toString().padLeft(2, '0');
    final period = time.period == DayPeriod.am ? 'AM' : 'PM';
    return '$hour:$minute $period';
  }

  void _showDayTimePicker() {
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
    final dayLabels = {
      'monday': 'Monday',
      'tuesday': 'Tuesday',
      'wednesday': 'Wednesday',
      'thursday': 'Thursday',
      'friday': 'Friday',
      'saturday': 'Saturday',
      'sunday': 'Sunday',
    };

    // Local copies to modify during the flow
    List<String> tempSelectedDays = List.from(
      _settings.preferredLearningDaysList,
    );
    TimeOfDay? tempTime = _settings.learningStartTime;

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
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Drag handle
                  Center(
                    child: Container(
                      width: 40,
                      height: 4,
                      decoration: BoxDecoration(
                        color: isDark
                            ? AppColors.borderDark
                            : AppColors.borderLight,
                        borderRadius: BorderRadius.circular(2),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Select Learning Days & Time',
                    style: AppTextStyles.logo.copyWith(fontSize: 18),
                  ),
                  const SizedBox(height: 20),

                  // Day multi‑selection (scrollable)
                  ConstrainedBox(
                    constraints: const BoxConstraints(maxHeight: 300),
                    child: ListView.separated(
                      shrinkWrap: true,
                      itemCount: allDays.length,
                      separatorBuilder: (_, __) => const Divider(height: 1),
                      itemBuilder: (_, idx) {
                        final day = allDays[idx];
                        final isSelected = tempSelectedDays.contains(day);
                        return CheckboxListTile(
                          title: Text(dayLabels[day]!),
                          value: isSelected,
                          onChanged: (selected) {
                            setSheetState(() {
                              if (selected == true) {
                                tempSelectedDays.add(day);
                              } else {
                                tempSelectedDays.remove(day);
                              }
                            });
                          },
                          activeColor: AppColors.primary,
                          contentPadding: EdgeInsets.zero,
                          controlAffinity: ListTileControlAffinity.leading,
                        );
                      },
                    ),
                  ),

                  const SizedBox(height: 20),

                  // Time picker button (clock style)
                  ListTile(
                    onTap: () async {
                      final picked = await showTimePicker(
                        context: ctx,
                        initialTime:
                            tempTime ?? const TimeOfDay(hour: 17, minute: 0),
                        builder: (context, child) {
                          return Theme(
                            data: Theme.of(context).copyWith(
                              timePickerTheme: TimePickerThemeData(
                                backgroundColor: isDark
                                    ? AppColors.cardDark
                                    : Colors.white,
                                hourMinuteColor: MaterialStateColor.resolveWith(
                                  (states) =>
                                      AppColors.primary.withOpacity(0.1),
                                ),
                                dayPeriodColor: MaterialStateColor.resolveWith(
                                  (states) => AppColors.primary,
                                ),
                              ),
                            ),
                            child: child!,
                          );
                        },
                      );
                      if (picked != null) {
                        setSheetState(() {
                          tempTime = picked;
                        });
                      }
                    },
                    leading: Icon(
                      Icons.access_time_rounded,
                      color: AppColors.primary,
                    ),
                    title: const Text('Learning start time'),
                    subtitle: Text(
                      tempTime != null
                          ? _formatTimeOfDay(tempTime!)
                          : 'Not set',
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        color: AppColors.primary,
                      ),
                    ),
                    trailing: const Icon(Icons.chevron_right_rounded),
                  ),

                  const SizedBox(height: 24),

                  // Save button
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          onPressed: () => Navigator.pop(ctx),
                          style: OutlinedButton.styleFrom(
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                          ),
                          child: const Text('Cancel'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: ElevatedButton(
                          onPressed: () {
                            setState(() {
                              _settings.preferredLearningDaysList =
                                  tempSelectedDays;
                              _settings.learningStartTime = tempTime;
                              _save(); // persist via API
                            });
                            Navigator.pop(ctx);
                          },
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppColors.primary,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                          ),
                          child: const Text('Save'),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  List<SettingTileData> _scheduleTiles(bool isDark) => [
    SettingTileData(
      icon: Icons.calendar_today_rounded,
      iconColor: const Color.fromARGB(255, 187, 91, 104),
      label: 'Preferred Learning Days & Time',
      valueBadge: _getLearningScheduleSummary(),
      onTap: () => _showDayTimePicker(),
    ),
  ];

  // ─────────────────────────────────────────────────────────────────────────
  //  TILES — Privacy & Social
  // ─────────────────────────────────────────────────────────────────────────
  List<SettingTileData> _privacyTiles(bool isDark) => [
    SettingTileData(
      icon: Icons.people_outline_rounded,
      iconColor: const Color(0xFF22C55E),
      label: 'Allow Friend Requests',
      valueBadge:
          _settings.allowFriendRequests[0].toUpperCase() +
          _settings.allowFriendRequests.substring(1),
      onTap: () => _showOptionsSheet(
        title: 'Who Can Send Friend Requests',
        options: const ['everyone', 'friends', 'nobody'],
        selected: _settings.allowFriendRequests,
        labels: const ['Everyone', 'Friends of friends', 'Nobody'],
        icons: const [
          Icons.public_rounded,
          Icons.people_rounded,
          Icons.lock_rounded,
        ],
        onSelect: (v) => setState(() {
          _settings.allowFriendRequests = v;
          _save();
        }),
      ),
    ),
    SettingTileData(
      icon: Icons.access_time_rounded,
      iconColor: const Color(0xFF22C55E),
      label: 'Show Last Active',
      subtitle: 'Let others see when you were online',
      toggleValue: _settings.showLastActive,
      onToggle: (v) => setState(() {
        _settings.showLastActive = v;
        _save();
      }),
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

  // ─────────────────────────────────────────────────────────────────────────
  //  TILES — About
  // ─────────────────────────────────────────────────────────────────────────
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

  // ─────────────────────────────────────────────────────────────────────────
  //  DANGER ZONE
  // ─────────────────────────────────────────────────────────────────────────
  Widget _buildDangerZone(bool isDark) {
    if (_searchQuery.isNotEmpty) return const SizedBox.shrink();

    final bg = isDark ? AppColors.cardDark : Colors.white;
    // final border = isDark ? AppColors.borderDark : AppColors.borderLight;
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
              // Log out
              InkWell(
                onTap: () => _showConfirmDialog(
                  title: 'Log Out',
                  message: 'Are you sure you want to log out?',
                  confirmLabel: 'Log Out',
                  confirmColor: const Color(0xFFEF4444),
                  onConfirm: () {
                    // TODO: clear auth and navigate to welcome
                    // context.go('/welcome');
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

              // Delete account
              InkWell(
                onTap: () => _showConfirmDialog(
                  title: 'Delete Account',
                  message:
                      'This will permanently delete your account and all data. This cannot be undone.',
                  confirmLabel: 'Delete Forever',
                  confirmColor: const Color(0xFFEF4444),
                  onConfirm: () {
                    // TODO: call delete API
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

  // ─────────────────────────────────────────────────────────────────────────
  //  BOTTOM SHEETS
  // ─────────────────────────────────────────────────────────────────────────

  // Options picker (theme, language, priority etc.)
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
            // Handle
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

  // Duration / number picker
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

  // Confirm dialog (logout / delete)
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

// ═════════════════════════════════════════════════════════════════════════════
//  SETTING TILE DATA CLASS
// ═════════════════════════════════════════════════════════════════════════════

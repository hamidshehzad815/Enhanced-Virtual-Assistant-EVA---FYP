import 'dart:async';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/theme/app_text_style.dart';
import '../../core/theme/app_colours.dart';
import '../../data/models/roadmap_model.dart';
import '../../data/models/schedule_date_model.dart';
import 'package:table_calendar/table_calendar.dart';

class SessionPopup extends StatefulWidget {
  final Session session;
  final bool isDark;
  final Future<Session> Function(String) fetchLatestSession;
  final Function(Session) onUpdate;
  final Function(String, String) onReschedule;
  final Function(String) onComplete;
  final Function(String) onSkip;
  final Future<ScheduleDatesResponse> Function() fetchScheduleDates;

  const SessionPopup({
    super.key,
    required this.session,
    required this.isDark,
    required this.fetchLatestSession,
    required this.fetchScheduleDates,
    required this.onUpdate,
    required this.onReschedule,
    required this.onComplete,
    required this.onSkip,
  });

  @override
  State<SessionPopup> createState() => _SessionPopupState();
}

class _SessionPopupState extends State<SessionPopup> {
  late Session _session;
  Timer? _uiTimer;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _session = widget.session;
    _uiTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (mounted) setState(() {});
    });
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 60),
      (_) => _refreshSession(),
    );
    _refreshSession();
  }

  @override
  void dispose() {
    _uiTimer?.cancel();
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _refreshSession() async {
    try {
      final updated = await widget.fetchLatestSession(_session.id);
      if (mounted) {
        setState(() {
          _session = updated;
        });
      }
    } catch (e) {
      // ignore
    }
  }

  bool get _canAct {
    return _session.isCurrent &&
        _session.status != 'completed' &&
        _session.status != 'skipped' &&
        _session.sessionState != 'locked';
  }

  String _getTimeRemaining() {
    final unlockAt = _session.unlockAt!;
    final diff = unlockAt.difference(DateTime.now());
    if (diff.isNegative) return 'Unlocked!';
    final hours = diff.inHours;
    final minutes = diff.inMinutes.remainder(60);
    final seconds = diff.inSeconds.remainder(60);
    return '${hours}h ${minutes}m ${seconds}s';
  }

  @override
  Widget build(BuildContext context) {
    final isDark = widget.isDark;
    final bg = isDark ? const Color(0xFF1C1C1E) : Colors.white;
    final textClr = isDark ? Colors.white : const Color(0xFF1C1C1E);
    final subClr = isDark ? Colors.white70 : Colors.black54;

    return AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      backgroundColor: bg,
      titlePadding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
      contentPadding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
      constraints: BoxConstraints(
        maxWidth: 480,
        maxHeight: MediaQuery.of(context).size.height * 0.85,
      ),
      title: Row(
        children: [
          Icon(Icons.school_rounded, color: AppColors.primary, size: 22),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              _session.title,
              style: AppTextStyles.headline.copyWith(
                fontSize: 17,
                fontWeight: FontWeight.w700,
                color: textClr,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: _getSessionStateColor(
                _session.sessionState,
              ).withOpacity(0.15),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              _session.sessionState.toUpperCase(),
              style: AppTextStyles.body.copyWith(
                fontSize: 8,
                fontWeight: FontWeight.w700,
                color: _getSessionStateColor(_session.sessionState),
              ),
            ),
          ),
        ],
      ),
      content: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            // ─── DETAILS ──────────────────────────────────────────────────
            _buildSectionTitle('Details', isDark),
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: isDark ? Colors.white10 : Colors.grey.shade50,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: isDark ? Colors.white12 : Colors.grey.shade200,
                ),
              ),
              child: Column(
                children: [
                  _buildDetailRow('Topic', _session.title, isDark),
                  _buildDivider(isDark),
                  _buildDetailRow(
                    'Schedule',
                    _session.scheduledDate != null
                        ? DateFormat(
                            'MMM d, y • h:mm a',
                          ).format(_session.scheduledDate!.toLocal())
                        : 'Not scheduled',
                    isDark,
                  ),
                  _buildDivider(isDark),
                  _buildDetailRow(
                    'Duration',
                    '${_session.estimatedDuration} min',
                    isDark,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),

            // ─── TIMER ──────────────────────────────────────────────────────
            if (_session.sessionState == 'locked' &&
                _session.unlockAt != null) ...[
              _buildSectionTitle('Unlock Timer', isDark),
              const SizedBox(height: 6),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.orange.withOpacity(0.10),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.orange.withOpacity(0.2)),
                ),
                child: Row(
                  children: [
                    Icon(Icons.timer_rounded, color: Colors.orange, size: 24),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Unlocks in:',
                            style: AppTextStyles.body.copyWith(
                              fontSize: 11,
                              color: subClr,
                            ),
                          ),
                          Text(
                            _getTimeRemaining(),
                            style: AppTextStyles.headline.copyWith(
                              fontSize: 20,
                              fontWeight: FontWeight.w700,
                              color: Colors.orange,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],

            // ─── ACTIONS ──────────────────────────────────────────────────
            if (_canAct) ...[
              const SizedBox(height: 14),
              _buildSectionTitle('Actions', isDark),
              const SizedBox(height: 6),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: isDark ? Colors.white10 : Colors.grey.shade50,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: isDark ? Colors.white12 : Colors.grey.shade200,
                  ),
                ),
                child: _buildActionDropdown(),
              ),
            ],

            // ─── RESOURCES ──────────────────────────────────────────────────
            if (_session.resources.isNotEmpty) ...[
              const SizedBox(height: 14),
              _buildSectionTitle('Resources', isDark),
              const SizedBox(height: 6),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: isDark ? Colors.white10 : Colors.grey.shade50,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: isDark ? Colors.white12 : Colors.grey.shade200,
                  ),
                ),
                child: Column(
                  children: _session.resources
                      .map((r) => _buildResourceTile(r, isDark))
                      .toList(),
                ),
              ),
            ] else ...[
              const SizedBox(height: 14),
              _buildSectionTitle('Resources', isDark),
              const SizedBox(height: 6),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: isDark ? Colors.white10 : Colors.grey.shade50,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: isDark ? Colors.white12 : Colors.grey.shade200,
                  ),
                ),
                child: Center(
                  child: Text(
                    'No resources available',
                    style: AppTextStyles.body.copyWith(
                      fontSize: 12,
                      color: subClr,
                    ),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(
            'Close',
            style: TextStyle(color: isDark ? Colors.white70 : Colors.black54),
          ),
        ),
      ],
    );
  }

  // ─── Helper Widgets ──────────────────────────────────────────────────
  Widget _buildSectionTitle(String title, bool isDark) {
    return Text(
      title,
      style: AppTextStyles.subtitleMedium.copyWith(
        fontSize: 12,
        fontWeight: FontWeight.w700,
        color: isDark ? Colors.white70 : Colors.black54,
        letterSpacing: 0.5,
      ),
    );
  }

  Widget _buildDetailRow(String label, String value, bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '$label: ',
            style: AppTextStyles.body.copyWith(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: isDark ? Colors.white60 : Colors.black54,
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: AppTextStyles.body.copyWith(
                fontSize: 13,
                color: isDark ? Colors.white : Colors.black87,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDivider(bool isDark) =>
      Divider(height: 8, color: isDark ? Colors.white12 : Colors.grey.shade200);

  // ─── Action Dropdown ──────────────────────────────────────────────────
  Widget _buildActionDropdown() {
    final actions = <String>[];

    if (_session.sessionState == 'ongoing' ||
        _session.sessionState == 'overdue') {
      actions.add('Complete');
    }
    if (_session.sessionState == 'unlocked_future') {
      actions.add('Skip');
    }
    if (_session.sessionState != 'locked' &&
        _session.sessionState != 'completed' &&
        _session.sessionState != 'skipped') {
      actions.add('Reschedule');
    }

    if (actions.isEmpty) {
      return Center(
        child: Text(
          'No actions available',
          style: AppTextStyles.body.copyWith(color: Colors.grey, fontSize: 12),
        ),
      );
    }

    return DropdownButtonFormField<String>(
      value: null,
      hint: Text(
        'Select Action',
        style: TextStyle(
          color: widget.isDark ? Colors.white70 : Colors.grey.shade600,
          fontSize: 13,
        ),
      ),
      isExpanded: true,
      decoration: InputDecoration(
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(
            color: widget.isDark ? Colors.white24 : Colors.grey.shade300,
          ),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        filled: true,
        fillColor: widget.isDark ? Colors.white10 : Colors.grey.shade50,
      ),
      dropdownColor: widget.isDark ? const Color(0xFF2C2C2E) : Colors.white,
      style: TextStyle(
        color: widget.isDark ? Colors.white : Colors.black87,
        fontSize: 13,
      ),
      items: actions.map((action) {
        IconData icon;
        Color iconColor;
        if (action == 'Complete') {
          icon = Icons.check_circle_rounded;
          iconColor = Colors.green;
        } else if (action == 'Skip') {
          icon = Icons.skip_next_rounded;
          iconColor = Colors.orange;
        } else {
          icon = Icons.calendar_today_rounded;
          iconColor = AppColors.primary;
        }
        return DropdownMenuItem<String>(
          value: action,
          child: Row(
            children: [
              Icon(icon, size: 18, color: iconColor),
              const SizedBox(width: 8),
              Text(action),
            ],
          ),
        );
      }).toList(),
      onChanged: (value) async {
        if (value == null) return;
        if (value == 'Complete') {
          widget.onComplete(_session.id);
          if (context.mounted) Navigator.pop(context);
        } else if (value == 'Skip') {
          widget.onSkip(_session.id);
          if (context.mounted) Navigator.pop(context);
        } else if (value == 'Reschedule') {
          try {
            final response = await widget.fetchScheduleDates();
            if (!mounted) return;
            _showSchedulePicker(context, response);
          } catch (e) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('Failed to load available dates: $e')),
            );
          }
        }
      },
    );
  }

  void _showSchedulePicker(
    BuildContext context,
    ScheduleDatesResponse response,
  ) {
    if (response.dates.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No available dates to reschedule.')),
      );
      return;
    }

    // ─── Build date map ──────────────────────────────────────────────────
    final dateMap = <String, ScheduleDate>{};
    for (var slot in response.dates) {
      dateMap[slot.date] = slot;
    }

    final from = DateTime.parse(response.range.from);
    final to = DateTime.parse(response.range.to);

    // ─── Format helper for time ────────────────────────────────────────
    String _formatTime(String? scheduledDatetime, String? fallbackTime) {
      if (scheduledDatetime != null && scheduledDatetime.isNotEmpty) {
        try {
          final dt = DateTime.parse(scheduledDatetime);
          return DateFormat('h:mm a').format(dt);
        } catch (_) {}
      }
      return fallbackTime ?? '';
    }

    showDialog(
      context: context,
      builder: (context) {
        DateTime focusedDay = from;

        return StatefulBuilder(
          builder: (context, setState) {
            // ─── Unified disabled palette (theme-aware) ──────────────────
            final Color disabledBg =
                widget.isDark ? Colors.white10 : Colors.grey.shade100;
            final Color disabledText =
                widget.isDark ? Colors.white30 : Colors.grey.shade400;

            // ─── Shared cell: one consistent look for every day ──────────
            // Available learning-schedule days are highlighted + tappable.
            // Everything else (past, out-of-range, and in-range non-learning
            // days) gets the same disabled treatment so the grid reads as one.
            Widget buildDayCell(
              BuildContext cellContext,
              DateTime day,
              DateTime focused, {
              required bool isAvailable,
            }) {
              // outsideDaysVisible is false, but guard cross-month cells too.
              if (day.month != focused.month || day.year != focused.year) {
                return const SizedBox.shrink();
              }

              final dateStr = DateFormat('yyyy-MM-dd').format(day);
              final slot = dateMap[dateStr];

              String timeDisplay = '';
              if (isAvailable && slot != null) {
                timeDisplay = _formatTime(slot.scheduledDatetime, slot.time);
              }

              return GestureDetector(
                onTap: isAvailable
                    ? () {
                        Navigator.pop(cellContext);
                        widget.onReschedule(_session.id, dateStr);
                      }
                    : null,
                child: Container(
                  margin: const EdgeInsets.all(2),
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: isAvailable
                        ? AppColors.primary.withOpacity(0.12)
                        : disabledBg,
                    borderRadius: BorderRadius.circular(8),
                    border: isAvailable
                        ? Border.all(
                            color: AppColors.primary.withOpacity(0.4),
                            width: 1,
                          )
                        : null,
                  ),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        '${day.day}',
                        style: TextStyle(
                          color:
                              isAvailable ? AppColors.primary : disabledText,
                          fontWeight: isAvailable
                              ? FontWeight.bold
                              : FontWeight.normal,
                          fontSize: 14,
                        ),
                      ),
                      if (isAvailable && timeDisplay.isNotEmpty)
                        Text(
                          timeDisplay,
                          style: TextStyle(
                            fontSize: 8,
                            color: AppColors.primary.withOpacity(0.7),
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                    ],
                  ),
                ),
              );
            }

            return AlertDialog(
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(20),
              ),
              titlePadding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
              contentPadding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
              title: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Select a new date',
                    style: AppTextStyles.headline.copyWith(fontSize: 20),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Available slots (${DateFormat('MMM d, y').format(from)} – ${DateFormat('MMM d, y').format(to)})',
                    style: AppTextStyles.body.copyWith(
                      fontSize: 13,
                      color: Colors.grey,
                    ),
                  ),
                ],
              ),
              content: SizedBox(
                width: double.maxFinite,
                height: 400, // Increased height to prevent overflow
                child: TableCalendar<ScheduleDate>(
                  firstDay: from,
                  lastDay: to,
                  focusedDay: focusedDay,
                  calendarFormat: CalendarFormat.month,
                  headerStyle: const HeaderStyle(
                    formatButtonVisible: false,
                    titleCentered: true,
                    leftChevronIcon: Icon(Icons.chevron_left_rounded),
                    rightChevronIcon: Icon(Icons.chevron_right_rounded),
                    titleTextStyle: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  daysOfWeekStyle: DaysOfWeekStyle(
                    weekdayStyle: TextStyle(
                      color: Colors.grey.shade600,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                    weekendStyle: TextStyle(
                      color: Colors.grey.shade600,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  calendarStyle: const CalendarStyle(
                    // Every day cell is drawn by calendarBuilders below, so the
                    // only thing that matters here is hiding outside days.
                    outsideDaysVisible: false,
                  ),
                  eventLoader: (day) {
                    final dateStr = DateFormat('yyyy-MM-dd').format(day);
                    final slot = dateMap[dateStr];
                    return slot != null ? [slot] : [];
                  },
                  calendarBuilders: CalendarBuilders(
                    defaultBuilder: (context, day, focusedDay) => buildDayCell(
                      context,
                      day,
                      focusedDay,
                      isAvailable: dateMap.containsKey(
                        DateFormat('yyyy-MM-dd').format(day),
                      ),
                    ),
                    // Out-of-range days (before `from` / after `to`) now share
                    // the exact same disabled look as in-range non-slot days.
                    disabledBuilder: (context, day, focusedDay) => buildDayCell(
                      context,
                      day,
                      focusedDay,
                      isAvailable: false,
                    ),
                    // Today follows the same rule: highlighted only if it is an
                    // available slot, otherwise disabled like every other day.
                    todayBuilder: (context, day, focusedDay) => buildDayCell(
                      context,
                      day,
                      focusedDay,
                      isAvailable: dateMap.containsKey(
                        DateFormat('yyyy-MM-dd').format(day),
                      ),
                    ),
                  ),
                  onPageChanged: (day) {
                    setState(() {
                      focusedDay = day;
                    });
                  },
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Cancel'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  // ─── Resource Tile ────────────────────────────────────────────────────
  Widget _buildResourceTile(Resource resource, bool isDark) {
    final textClr = isDark ? Colors.white : Colors.black87;
    final subClr = isDark ? Colors.white54 : Colors.black54;

    // ─── Resources clickable only when active or terminal ──────────────
    final bool isAccessible =
        _session.sessionState == 'ongoing' ||
        _session.sessionState == 'overdue' ||
        _session.status == 'completed' ||
        _session.status == 'skipped';

    return Opacity(
      opacity: isAccessible ? 1.0 : 0.5,
      child: InkWell(
        onTap: isAccessible
            ? () async {
                final uri = Uri.parse(resource.url);
                if (await canLaunchUrl(uri)) {
                  await launchUrl(uri, mode: LaunchMode.externalApplication);
                } else {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Cannot open link')),
                  );
                }
              }
            : null,
        borderRadius: BorderRadius.circular(10),
        child: Container(
          margin: const EdgeInsets.only(bottom: 6),
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: isDark ? Colors.white10 : Colors.grey.shade50,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: isDark ? Colors.white12 : Colors.grey.shade200,
            ),
          ),
          child: Row(
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(6),
                child: resource.thumbnail != null
                    ? Image.network(
                        resource.thumbnail!,
                        width: 80,
                        height: 56,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => Container(
                          width: 80,
                          height: 56,
                          color: isDark ? Colors.white12 : Colors.grey.shade200,
                          child: Icon(
                            Icons.play_circle_filled_rounded,
                            color: Colors.red,
                            size: 30,
                          ),
                        ),
                      )
                    : Container(
                        width: 80,
                        height: 56,
                        color: isDark ? Colors.white12 : Colors.grey.shade200,
                        child: Icon(
                          Icons.play_circle_filled_rounded,
                          color: Colors.red,
                          size: 30,
                        ),
                      ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      resource.title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: AppTextStyles.body.copyWith(
                        fontSize: 13,
                        fontWeight: FontWeight.w500,
                        color: textClr,
                      ),
                    ),
                    if (resource.channelName != null)
                      Text(
                        resource.channelName!,
                        style: AppTextStyles.body.copyWith(
                          fontSize: 11,
                          color: subClr,
                        ),
                      ),
                  ],
                ),
              ),
              Icon(
                Icons.open_in_new_rounded,
                size: 16,
                color: isAccessible ? Colors.grey : Colors.grey.shade400,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Color _getSessionStateColor(String state) {
    switch (state) {
      case 'locked':
        return Colors.grey;
      case 'unlocked_future':
        return Colors.orange;
      case 'ongoing':
        return Colors.blue;
      case 'overdue':
        return Colors.red;
      case 'completed':
        return Colors.green;
      case 'skipped':
        return Colors.grey.shade500;
      case 'upcoming':
        return Colors.grey.shade400;
      default:
        return Colors.grey;
    }
  }
}

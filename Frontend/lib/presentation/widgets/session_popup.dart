import 'dart:async';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/theme/app_text_style.dart';
import '../../core/theme/app_colours.dart';
import '../../data/models/roadmap_model.dart';

class SessionPopup extends StatefulWidget {
  final Session session;
  final bool isDark;
  final Function(Session) onUpdate;
  final Function(String, String) onReschedule;
  final Function(String) onComplete;
  final Function(String) onSkip;

  const SessionPopup({
    super.key,
    required this.session,
    required this.isDark,
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
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _session = widget.session;
    if (_session.sessionState == 'locked' && _session.unlockAt != null) {
      _startTimer();
    }
  }

  void _startTimer() {
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  bool get _isActive {
    return _session.sessionState == 'ongoing' ||
        _session.sessionState == 'overdue';
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
              color: _getStatusColor(_session.status).withOpacity(0.15),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              _session.status.toUpperCase(),
              style: AppTextStyles.body.copyWith(
                fontSize: 8,
                fontWeight: FontWeight.w700,
                color: _getStatusColor(_session.status),
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

            // ─── ACTIONS (single dropdown) ──────────────────────────────────
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

  // ─── Single Action Dropdown ──────────────────────────────────────────
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
          final date = await showDatePicker(
            context: context,
            initialDate: _session.scheduledDate ?? DateTime.now(),
            firstDate: DateTime(2024),
            lastDate: DateTime(2027),
          );
          if (date != null) {
            final formatted = DateFormat('yyyy-MM-dd').format(date);
            widget.onReschedule(_session.id, formatted);
            if (context.mounted) Navigator.pop(context);
          }
        }
      },
    );
  }

  // ─── Resource Tile ────────────────────────────────────────────────────
  Widget _buildResourceTile(Resource resource, bool isDark) {
    final textClr = isDark ? Colors.white : Colors.black87;
    final subClr = isDark ? Colors.white54 : Colors.black54;
    final bool isActive =
        _session.sessionState == 'ongoing' ||
        _session.sessionState == 'overdue';

    return Opacity(
      opacity: isActive ? 1.0 : 0.5,
      child: InkWell(
        onTap: isActive
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
                color: isActive ? Colors.grey : Colors.grey.shade400,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'completed':
        return Colors.green;
      case 'ongoing':
        return Colors.blue;
      case 'pending':
        return Colors.orange;
      case 'skipped':
        return Colors.grey;
      default:
        return Colors.grey;
    }
  }
}

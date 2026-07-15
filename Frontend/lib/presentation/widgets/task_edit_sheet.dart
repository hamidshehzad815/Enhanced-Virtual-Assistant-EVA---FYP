import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/theme/app_colours.dart';
import '../../core/theme/app_text_style.dart';
import '../../data/models/calendar_task_model.dart';
import '../providers/calendar_viewmodel.dart';

Future<void> showTaskEditSheet(
  BuildContext context, {
  required CalendarViewModel viewModel,
  required CalendarTask task,
  VoidCallback? onSaved,
}) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (sheetContext) => _TaskEditSheet(
      viewModel: viewModel,
      task: task,
      onSaved: onSaved,
    ),
  );
}

class _TaskEditSheet extends StatefulWidget {
  final CalendarViewModel viewModel;
  final CalendarTask task;
  final VoidCallback? onSaved;

  const _TaskEditSheet({
    required this.viewModel,
    required this.task,
    this.onSaved,
  });

  @override
  State<_TaskEditSheet> createState() => _TaskEditSheetState();
}

class _TaskEditSheetState extends State<_TaskEditSheet> {
  late CalendarTask _editedTask;
  late final TextEditingController _titleController;
  late final TextEditingController _descriptionController;
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _editedTask = widget.task.copyWith();
    _titleController = TextEditingController(text: _editedTask.title);
    _descriptionController = TextEditingController(
      text: _editedTask.description ?? '',
    );
  }

  @override
  void dispose() {
    _titleController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  bool get _isComplete => _editedTask.status == TaskStatus.completed;

  Color _priorityColor(TaskPriority priority) {
    switch (priority) {
      case TaskPriority.high:
        return const Color(0xFFEF4444);
      case TaskPriority.medium:
        return const Color(0xFFF59E0B);
      case TaskPriority.low:
        return const Color(0xFF22C55E);
    }
  }

  InputDecoration _fieldDecoration({
    required bool isDark,
    required String label,
    String? hint,
    Widget? prefixIcon,
  }) {
    final borderColor = isDark ? AppColors.borderDark : AppColors.borderLight;
    final fill = isDark ? AppColors.inputFillDark : AppColors.inputFillLight;
    final labelColor = isDark
        ? AppColors.secondaryTextDark
        : AppColors.secondaryTextLight;

    return InputDecoration(
      labelText: label,
      hintText: hint,
      prefixIcon: prefixIcon,
      labelStyle: TextStyle(color: labelColor, fontSize: 13),
      hintStyle: TextStyle(
        color: isDark ? AppColors.hintDark : AppColors.secondaryTextLight,
      ),
      filled: true,
      fillColor: fill,
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: BorderSide(color: borderColor),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: BorderSide(color: borderColor),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: AppColors.primary, width: 1.5),
      ),
    );
  }

  void _showSnack(String message, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError ? const Color(0xFFDC2626) : const Color(0xFF16A34A),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    );
  }

  Future<void> _pickDate() async {
    final date = await showDatePicker(
      context: context,
      initialDate: _editedTask.dueDateTime,
      firstDate: DateTime(2024),
      lastDate: DateTime(2027),
      builder: (context, child) {
        return Theme(
          data: Theme.of(context).copyWith(
            colorScheme: Theme.of(context).colorScheme.copyWith(
              primary: AppColors.primary,
            ),
          ),
          child: child!,
        );
      },
    );
    if (date == null || !mounted) return;
    setState(() {
      _editedTask = _editedTask.copyWith(
        dueDateTime: DateTime(
          date.year,
          date.month,
          date.day,
          _editedTask.dueDateTime.hour,
          _editedTask.dueDateTime.minute,
        ),
      );
    });
  }

  Future<void> _pickTime() async {
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(_editedTask.dueDateTime),
      builder: (context, child) {
        return Theme(
          data: Theme.of(context).copyWith(
            colorScheme: Theme.of(context).colorScheme.copyWith(
              primary: AppColors.primary,
            ),
          ),
          child: child!,
        );
      },
    );
    if (time == null || !mounted) return;
    setState(() {
      final current = _editedTask.dueDateTime;
      _editedTask = _editedTask.copyWith(
        dueDateTime: DateTime(
          current.year,
          current.month,
          current.day,
          time.hour,
          time.minute,
        ),
      );
    });
  }

  void _adjustDuration(int delta) {
    final next = (_editedTask.durationMinutes + delta).clamp(5, 1440);
    setState(() => _editedTask = _editedTask.copyWith(durationMinutes: next));
  }

  Future<void> _save() async {
    final title = _titleController.text.trim();
    if (title.isEmpty) {
      _showSnack('Title cannot be empty', isError: true);
      return;
    }
    if (_editedTask.durationMinutes < 5) {
      _showSnack('Duration must be at least 5 minutes', isError: true);
      return;
    }

    final description = _descriptionController.text.trim();
    final taskToSave = _editedTask.copyWith(
      title: title,
      description: description.isEmpty ? null : description,
    );

    setState(() => _isSaving = true);
    try {
      await widget.viewModel.updateTask(taskToSave);
      if (!mounted) return;
      final messenger = ScaffoldMessenger.of(context);
      Navigator.of(context).pop();
      widget.onSaved?.call();
      messenger.showSnackBar(
        SnackBar(
          content: const Text('Task updated successfully'),
          backgroundColor: const Color(0xFF16A34A),
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      _showSnack('Failed to save task: $e', isError: true);
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  Widget _sectionLabel(String text, bool isDark) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        text,
        style: AppTextStyles.subtitleMedium.copyWith(
          color: isDark
              ? AppColors.secondaryTextDark
              : AppColors.secondaryTextLight,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  Widget _pickerTile({
    required bool isDark,
    required IconData icon,
    required String label,
    required String value,
    required VoidCallback onTap,
  }) {
    final bg = isDark ? AppColors.inputFillDark : AppColors.inputFillLight;
    final border = isDark ? AppColors.borderDark : AppColors.borderLight;
    final text = isDark ? AppColors.primaryTextDark : AppColors.primaryTextLight;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Ink(
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: border),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
            child: Row(
              children: [
                Icon(icon, color: AppColors.primary, size: 20),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        label,
                        style: AppTextStyles.subtitleSmall.copyWith(
                          color: isDark
                              ? AppColors.secondaryTextDark
                              : AppColors.secondaryTextLight,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        value,
                        style: AppTextStyles.body.copyWith(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: text,
                        ),
                      ),
                    ],
                  ),
                ),
                Icon(
                  Icons.chevron_right_rounded,
                  color: isDark
                      ? AppColors.secondaryTextDark
                      : AppColors.secondaryTextLight,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final sheetBg = isDark ? AppColors.cardDark : Colors.white;
    final titleColor = isDark
        ? AppColors.primaryTextDark
        : AppColors.primaryTextLight;
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;

    return Padding(
      padding: EdgeInsets.only(bottom: bottomInset),
      child: Container(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.of(context).size.height * 0.92,
        ),
        decoration: BoxDecoration(
          color: sheetBg,
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
              padding: const EdgeInsets.fromLTRB(20, 14, 8, 0),
              child: Row(
                children: [
                  Icon(Icons.edit_note_rounded, color: AppColors.primary),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Edit Task',
                      style: AppTextStyles.titleMedium.copyWith(
                        fontSize: 22,
                        color: titleColor,
                      ),
                    ),
                  ),
                  IconButton(
                    onPressed: _isSaving ? null : () => Navigator.pop(context),
                    icon: Icon(
                      Icons.close_rounded,
                      color: isDark
                          ? AppColors.secondaryTextDark
                          : AppColors.secondaryTextLight,
                    ),
                  ),
                ],
              ),
            ),
            Flexible(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    TextField(
                      controller: _titleController,
                      style: TextStyle(color: titleColor),
                      decoration: _fieldDecoration(
                        isDark: isDark,
                        label: 'Title',
                        hint: 'Enter task title',
                      ),
                      textInputAction: TextInputAction.next,
                    ),
                    const SizedBox(height: 18),
                    _sectionLabel('Priority', isDark),
                    Row(
                      children: TaskPriority.values.map((priority) {
                        final selected = _editedTask.priority == priority;
                        final color = _priorityColor(priority);
                        return Expanded(
                          child: Padding(
                            padding: EdgeInsets.only(
                              right: priority != TaskPriority.high ? 8 : 0,
                            ),
                            child: Material(
                              color: Colors.transparent,
                              child: InkWell(
                                onTap: () => setState(
                                  () => _editedTask = _editedTask.copyWith(
                                    priority: priority,
                                  ),
                                ),
                                borderRadius: BorderRadius.circular(12),
                                child: AnimatedContainer(
                                  duration: const Duration(milliseconds: 180),
                                  padding: const EdgeInsets.symmetric(
                                    vertical: 12,
                                  ),
                                  decoration: BoxDecoration(
                                    color: selected
                                        ? color.withOpacity(isDark ? 0.22 : 0.14)
                                        : (isDark
                                              ? AppColors.inputFillDark
                                              : AppColors.inputFillLight),
                                    borderRadius: BorderRadius.circular(12),
                                    border: Border.all(
                                      color: selected
                                          ? color
                                          : (isDark
                                                ? AppColors.borderDark
                                                : AppColors.borderLight),
                                      width: selected ? 1.5 : 1,
                                    ),
                                  ),
                                  child: Column(
                                    children: [
                                      Icon(
                                        priority == TaskPriority.high
                                            ? Icons.priority_high_rounded
                                            : priority == TaskPriority.medium
                                            ? Icons.flag_rounded
                                            : Icons.flag_outlined,
                                        size: 18,
                                        color: color,
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        priority.name[0].toUpperCase() +
                                            priority.name.substring(1),
                                        style: AppTextStyles.subtitleMedium
                                            .copyWith(
                                              color: selected
                                                  ? color
                                                  : (isDark
                                                        ? AppColors
                                                              .secondaryTextDark
                                                        : AppColors
                                                              .secondaryTextLight),
                                              fontWeight: selected
                                                  ? FontWeight.w700
                                                  : FontWeight.w500,
                                            ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                    const SizedBox(height: 18),
                    _sectionLabel('Duration', isDark),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 10,
                      ),
                      decoration: BoxDecoration(
                        color: isDark
                            ? AppColors.inputFillDark
                            : AppColors.inputFillLight,
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(
                          color: isDark
                              ? AppColors.borderDark
                              : AppColors.borderLight,
                        ),
                      ),
                      child: Row(
                        children: [
                          _durationButton(
                            icon: Icons.remove_rounded,
                            onTap: () => _adjustDuration(-15),
                            isDark: isDark,
                          ),
                          Expanded(
                            child: Column(
                              children: [
                                Text(
                                  '${_editedTask.durationMinutes}',
                                  style: AppTextStyles.headerLarge.copyWith(
                                    fontSize: 24,
                                    color: titleColor,
                                  ),
                                ),
                                Text(
                                  'minutes',
                                  style: AppTextStyles.subtitleSmall.copyWith(
                                    color: isDark
                                        ? AppColors.secondaryTextDark
                                        : AppColors.secondaryTextLight,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          _durationButton(
                            icon: Icons.add_rounded,
                            onTap: () => _adjustDuration(15),
                            isDark: isDark,
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 18),
                    TextField(
                      controller: _descriptionController,
                      style: TextStyle(color: titleColor),
                      maxLines: 3,
                      decoration: _fieldDecoration(
                        isDark: isDark,
                        label: 'Description',
                        hint: 'Add details (optional)',
                      ),
                    ),
                    const SizedBox(height: 18),
                    _sectionLabel('Schedule', isDark),
                    _pickerTile(
                      isDark: isDark,
                      icon: Icons.calendar_today_rounded,
                      label: 'Date',
                      value: DateFormat('EEE, MMM d, y').format(
                        _editedTask.dueDateTime.toLocal(),
                      ),
                      onTap: _pickDate,
                    ),
                    const SizedBox(height: 10),
                    _pickerTile(
                      isDark: isDark,
                      icon: Icons.schedule_rounded,
                      label: 'Time',
                      value: DateFormat('h:mm a').format(
                        _editedTask.dueDateTime.toLocal(),
                      ),
                      onTap: _pickTime,
                    ),
                    const SizedBox(height: 18),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 14,
                        vertical: 10,
                      ),
                      decoration: BoxDecoration(
                        color: isDark
                            ? AppColors.inputFillDark
                            : AppColors.inputFillLight,
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(
                          color: isDark
                              ? AppColors.borderDark
                              : AppColors.borderLight,
                        ),
                      ),
                      child: Row(
                        children: [
                          Icon(
                            _isComplete
                                ? Icons.check_circle_rounded
                                : Icons.radio_button_unchecked_rounded,
                            color: _isComplete
                                ? const Color(0xFF22C55E)
                                : AppColors.primary,
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Mark as complete',
                                  style: AppTextStyles.body.copyWith(
                                    fontSize: 14,
                                    fontWeight: FontWeight.w600,
                                    color: titleColor,
                                  ),
                                ),
                                Text(
                                  _isComplete
                                      ? 'Task is completed'
                                      : 'Task is ${_editedTask.displayStatus}',
                                  style: AppTextStyles.subtitleSmall.copyWith(
                                    color: isDark
                                        ? AppColors.secondaryTextDark
                                        : AppColors.secondaryTextLight,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          Switch.adaptive(
                            value: _isComplete,
                            activeTrackColor: const Color(0xFF22C55E).withValues(alpha: 0.5),
                            activeThumbColor: const Color(0xFF22C55E),
                            onChanged: (value) {
                              setState(() {
                                _editedTask = _editedTask.copyWith(
                                  status: value
                                      ? TaskStatus.completed
                                      : TaskStatus.pending,
                                  displayStatus: value ? 'complete' : 'pending',
                                );
                              });
                            },
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
              child: Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: _isSaving ? null : () => Navigator.pop(context),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: isDark
                            ? AppColors.primaryTextDark
                            : AppColors.primaryTextLight,
                        side: BorderSide(
                          color: isDark
                              ? AppColors.borderDark
                              : AppColors.borderLight,
                        ),
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(14),
                        ),
                      ),
                      child: const Text('Cancel'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton(
                      onPressed: _isSaving ? null : _save,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.primary,
                        foregroundColor: Colors.white,
                        disabledBackgroundColor: AppColors.primary.withOpacity(
                          0.5,
                        ),
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(14),
                        ),
                      ),
                      child: _isSaving
                          ? const SizedBox(
                              width: 22,
                              height: 22,
                              child: CircularProgressIndicator(
                                strokeWidth: 2.2,
                                color: Colors.white,
                              ),
                            )
                          : const Text('Save'),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _durationButton({
    required IconData icon,
    required VoidCallback onTap,
    required bool isDark,
  }) {
    return Material(
      color: isDark ? AppColors.cardElevatedDark : const Color(0xFFF3F4F6),
      borderRadius: BorderRadius.circular(10),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: SizedBox(
          width: 44,
          height: 44,
          child: Icon(icon, color: AppColors.primary),
        ),
      ),
    );
  }
}


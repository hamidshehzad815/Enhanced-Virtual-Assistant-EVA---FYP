import 'package:flutter/material.dart';
import '../../core/theme/app_colours.dart';

/// Demo Chat Bubble - For demo/greeting screens (not real messages)
/// Single responsibility: Display demo chat messages with optional bold text
class DemoChatBubble extends StatelessWidget {
  final String text;
  final bool isEva;
  final String? boldPart;
  final String? userInitial;

  const DemoChatBubble({
    super.key,
    required this.text,
    required this.isEva,
    this.boldPart,
    this.userInitial,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final evaBubbleBg = isDark
        ? AppColors.cardElevatedDark
        : const Color.fromARGB(255, 198, 193, 193);
    final evaTextColor = isDark ? AppColors.primaryTextDark : Colors.black87;

    return Row(
      mainAxisAlignment: isEva
          ? MainAxisAlignment.start
          : MainAxisAlignment.end,
      children: [
        // EVA avatar (left side)
        if (isEva) ...[
          CircleAvatar(
            radius: 14,
            backgroundColor: AppColors.primary,
            child: const Text(
              'E',
              style: TextStyle(
                color: Colors.white,
                fontSize: 12,
                fontStyle: FontStyle.italic,
              ),
            ),
          ),
          const SizedBox(width: 8),
        ],

        // Bubble
        Flexible(
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: isEva ? evaBubbleBg : AppColors.primary,
              borderRadius: BorderRadius.only(
                topLeft: const Radius.circular(18),
                topRight: const Radius.circular(18),
                bottomLeft: Radius.circular(isEva ? 4 : 18),
                bottomRight: Radius.circular(isEva ? 18 : 4),
              ),
            ),
            child: boldPart != null
                ? _buildBoldText(text, boldPart!, isEva, evaTextColor)
                : Text(
                    text,
                    style: TextStyle(
                      color: isEva ? evaTextColor : Colors.white,
                      fontSize: 13.5,
                      height: 1.4,
                    ),
                  ),
          ),
        ),

        // User avatar (right side)
        if (!isEva) ...[
          const SizedBox(width: 8),
          CircleAvatar(
            radius: 14,
            backgroundColor: AppColors.primary,
            child: const Text(
              'A',
              style: TextStyle(
                color: Colors.white,
                fontSize: 12,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ],
    );
  }

  /// Build text with bold part highlighted
  Widget _buildBoldText(
    String text,
    String boldPart,
    bool isEva,
    Color evaTextColor,
  ) {
    final parts = text.split(boldPart);
    List<TextSpan> spans = [];

    for (int i = 0; i < parts.length; i++) {
      if (parts[i].isNotEmpty) {
        spans.add(
          TextSpan(
            text: parts[i],
            style: TextStyle(fontWeight: FontWeight.normal),
          ),
        );
      }
      if (i < parts.length - 1) {
        spans.add(
          TextSpan(
            text: boldPart,
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
        );
      }
    }

    return RichText(
      text: TextSpan(
        style: TextStyle(
          color: isEva ? evaTextColor : Colors.white,
          fontSize: 13.5,
          height: 1.4,
        ),
        children: spans,
      ),
    );
  }
}

import 'package:flutter/material.dart';
import '../../core/theme/app_colours.dart';
import '../../core/theme/app_text_style.dart';

class SettingsSearchBar extends StatelessWidget {
  final TextEditingController controller;
  final String searchQuery;
  final VoidCallback? onClear;

  const SettingsSearchBar({
    required this.controller,
    required this.searchQuery,
    this.onClear,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bg = isDark ? AppColors.cardDark : Colors.white;
    final border = isDark ? AppColors.borderDark : AppColors.borderLight;
    final hint = isDark ? AppColors.hintDark : AppColors.secondaryTextLight;
    final text = isDark
        ? AppColors.primaryTextDark
        : AppColors.primaryTextLight;

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
      child: Container(
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: border),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(isDark ? 0.2 : 0.04),
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: TextField(
          controller: controller,
          style: TextStyle(color: text, fontSize: 14),
          decoration: InputDecoration(
            hintText: 'Search settings...',
            hintStyle: TextStyle(color: hint, fontSize: 14),
            prefixIcon: Icon(Icons.search_rounded, color: hint, size: 20),
            suffixIcon: searchQuery.isNotEmpty
                ? IconButton(
                    icon: Icon(Icons.close_rounded, color: hint, size: 18),
                    onPressed:
                        onClear ??
                        () {
                          controller.clear();
                          FocusScope.of(context).unfocus();
                        },
                  )
                : null,
            border: InputBorder.none,
            enabledBorder: InputBorder.none,
            focusedBorder: InputBorder.none,
            filled: false,
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 16,
              vertical: 12,
            ),
          ),
        ),
      ),
    );
  }
}

class SettingsProfileCard extends StatelessWidget {
  final bool isDark;
  final String searchQuery;

  const SettingsProfileCard({
    required this.isDark,
    required this.searchQuery,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    if (searchQuery.isNotEmpty) return const SizedBox.shrink();

    final bg = isDark ? AppColors.cardDark : Colors.white;
    final border = isDark ? AppColors.borderDark : AppColors.borderLight;
    final primary = isDark
        ? AppColors.primaryTextDark
        : AppColors.primaryTextLight;
    final secondary = isDark
        ? AppColors.secondaryTextDark
        : AppColors.secondaryTextLight;

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: border),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(isDark ? 0.25 : 0.05),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          Stack(
            children: [
              Container(
                width: 62,
                height: 62,
                decoration: BoxDecoration(
                  color: AppColors.primary,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.primary.withOpacity(0.35),
                      blurRadius: 12,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: const Center(
                  child: Text(
                    'A',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 26,
                      fontWeight: FontWeight.bold,
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                ),
              ),
              Positioned(
                right: 0,
                bottom: 0,
                child: Container(
                  width: 20,
                  height: 20,
                  decoration: BoxDecoration(
                    color: isDark ? AppColors.cardElevatedDark : Colors.white,
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: isDark
                          ? AppColors.borderDark
                          : AppColors.borderLight,
                    ),
                  ),
                  child: Icon(
                    Icons.edit_rounded,
                    size: 11,
                    color: AppColors.primary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Areej',
                  style: AppTextStyles.subtitleMedium.copyWith(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: primary,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  'areej@example.com',
                  style: TextStyle(fontSize: 12, color: AppColors.primary),
                ),
              ],
            ),
          ),
          Icon(Icons.chevron_right_rounded, color: secondary, size: 20),
        ],
      ),
    );
  }
}

class SettingsSection extends StatelessWidget {
  final bool isDark;
  final IconData icon;
  final Color iconColor;
  final String title;
  final List<SettingTileData> tiles;
  final String searchQuery;

  const SettingsSection({
    required this.isDark,
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.tiles,
    required this.searchQuery,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    final filteredTiles = searchQuery.isEmpty
        ? tiles
        : tiles
              .where((tile) => tile.label.toLowerCase().contains(searchQuery))
              .toList();

    if (filteredTiles.isEmpty) return const SizedBox.shrink();

    final bg = isDark ? AppColors.cardDark : Colors.white;
    final border = isDark ? AppColors.borderDark : AppColors.borderLight;
    final primary = isDark
        ? AppColors.primaryTextDark
        : AppColors.primaryTextLight;
    final secondary = isDark
        ? AppColors.secondaryTextDark
        : AppColors.secondaryTextLight;
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
                  color: iconColor.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(icon, size: 15, color: iconColor),
              ),
              const SizedBox(width: 10),
              Text(
                title,
                style: AppTextStyles.subtitleMedium.copyWith(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.3,
                  color: secondary,
                ),
              ),
            ],
          ),
        ),
        Container(
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: border),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(isDark ? 0.2 : 0.04),
                blurRadius: 12,
                offset: const Offset(0, 3),
              ),
            ],
          ),
          child: Column(
            children: List.generate(filteredTiles.length, (i) {
              final tile = filteredTiles[i];
              final isLast = i == filteredTiles.length - 1;
              return Column(
                children: [
                  _SettingsTileRow(tile: tile, isDark: isDark),
                  if (!isLast)
                    Divider(
                      height: 1,
                      color: divider,
                      indent: 16,
                      endIndent: 16,
                    ),
                ],
              );
            }),
          ),
        ),
      ],
    );
  }
}

class _SettingsTileRow extends StatelessWidget {
  final SettingTileData tile;
  final bool isDark;

  const _SettingsTileRow({required this.tile, required this.isDark, super.key});

  @override
  Widget build(BuildContext context) {
    final primary = isDark
        ? AppColors.primaryTextDark
        : AppColors.primaryTextLight;
    final secondary = isDark
        ? AppColors.secondaryTextDark
        : AppColors.secondaryTextLight;

    return InkWell(
      onTap: tile.onTap,
      borderRadius: BorderRadius.circular(18),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
        child: Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: tile.iconColor.withOpacity(0.1),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(tile.icon, size: 18, color: tile.iconColor),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    tile.label,
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                      color: primary,
                    ),
                  ),
                  if (tile.subtitle != null) ...[
                    const SizedBox(height: 2),
                    Text(
                      tile.subtitle!,
                      style: TextStyle(fontSize: 11, color: secondary),
                    ),
                  ],
                ],
              ),
            ),
            if (tile.toggleValue != null)
              Switch(
                value: tile.toggleValue!,
                onChanged: tile.onToggle,
                activeColor: AppColors.primary,
                inactiveTrackColor: isDark
                    ? AppColors.borderDark
                    : const Color(0xFFE5E7EB),
              )
            else if (tile.valueBadge != null)
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: isDark
                          ? AppColors.cardElevatedDark
                          : const Color(0xFFF3F4F6),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                        color: isDark
                            ? AppColors.borderDark
                            : AppColors.borderLight,
                      ),
                    ),
                    child: Text(
                      tile.valueBadge!,
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: AppColors.primary,
                      ),
                    ),
                  ),
                  const SizedBox(width: 4),
                  Icon(Icons.chevron_right_rounded, size: 18, color: secondary),
                ],
              )
            else
              Icon(Icons.chevron_right_rounded, size: 18, color: secondary),
          ],
        ),
      ),
    );
  }
}

class SettingTileData {
  final IconData icon;
  final Color iconColor;
  final String label;
  final String? subtitle;
  final bool? toggleValue;
  final ValueChanged<bool>? onToggle;
  final String? valueBadge;
  final VoidCallback? onTap;

  const SettingTileData({
    required this.icon,
    required this.iconColor,
    required this.label,
    this.subtitle,
    this.toggleValue,
    this.onToggle,
    this.valueBadge,
    this.onTap,
  });
}

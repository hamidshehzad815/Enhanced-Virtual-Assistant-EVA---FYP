import 'package:flutter/material.dart';
import '../../core/theme/app_colours.dart';
import '../../core/theme/app_text_style.dart';
import '../../data/models/user_profile.dart';

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
  final UserProfile? profile;
  final VoidCallback? onEditProfile;

  const SettingsProfileCard({
    required this.isDark,
    required this.searchQuery,
    this.profile,
    this.onEditProfile,
  });

  @override
  Widget build(BuildContext context) {
    if (searchQuery.isNotEmpty) return const SizedBox.shrink();

    return Container(
      // your existing styling
      child: Row(
        children: [
          CircleAvatar(
            radius: 32,
            backgroundImage: profile?.profilePicture != null
                ? NetworkImage(profile!.profilePicture!)
                : null,
            child: profile?.profilePicture == null
                ? Text(profile?.initial ?? '?')
                : null,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  profile?.name ?? 'User Name',
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
                // Optionally show email if you have it
                // Text(profile?.email ?? ''),
              ],
            ),
          ),
          if (onEditProfile != null)
            IconButton(icon: const Icon(Icons.edit), onPressed: onEditProfile),
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
    final border = isDark ? AppColors.borderDark : Colors.grey;
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

  const _SettingsTileRow({required this.tile, required this.isDark});

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
                value: tile.toggleValue ?? false,
                onChanged: tile.enabled ? tile.onToggle : null,
                activeThumbColor: AppColors.primary,
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
  final bool enabled;
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
    this.enabled = true,
    this.subtitle,
    this.toggleValue,
    this.onToggle,
    this.valueBadge,
    this.onTap,
  });
}

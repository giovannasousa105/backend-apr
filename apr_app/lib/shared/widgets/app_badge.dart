import 'package:flutter/material.dart';

import '../../app/theme/app_colors.dart';
import '../../app/theme/app_radius.dart';

enum AppBadgeTone { neutral, info, success, warning, danger }

class AppBadge extends StatelessWidget {
  const AppBadge({
    super.key,
    required this.label,
    this.tone = AppBadgeTone.neutral,
  });

  final String label;
  final AppBadgeTone tone;

  @override
  Widget build(BuildContext context) {
    final palette = switch (tone) {
      AppBadgeTone.neutral => (
        AppColors.surfaceElevated,
        AppColors.textSoft,
        AppColors.border,
      ),
      AppBadgeTone.info => (
        AppColors.infoSoft,
        AppColors.primaryDeep,
        AppColors.primary.withValues(alpha: 0.2),
      ),
      AppBadgeTone.success => (
        AppColors.successSoft,
        AppColors.success,
        AppColors.success.withValues(alpha: 0.2),
      ),
      AppBadgeTone.warning => (
        AppColors.warningSoft,
        AppColors.warning,
        AppColors.warning.withValues(alpha: 0.2),
      ),
      AppBadgeTone.danger => (
        AppColors.dangerSoft,
        AppColors.danger,
        AppColors.danger.withValues(alpha: 0.2),
      ),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: palette.$1,
        borderRadius: BorderRadius.circular(AppRadius.pill),
        border: Border.all(color: palette.$3),
      ),
      child: Text(
        label,
        style: Theme.of(
          context,
        ).textTheme.labelMedium?.copyWith(color: palette.$2),
      ),
    );
  }
}

class AppChip extends StatelessWidget {
  const AppChip({
    super.key,
    required this.label,
    this.selected = false,
    this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: selected ? AppColors.primarySoft : AppColors.surfaceElevated,
          borderRadius: BorderRadius.circular(AppRadius.pill),
          border: Border.all(
            color: selected
                ? AppColors.primary.withValues(alpha: 0.3)
                : AppColors.border,
          ),
        ),
        child: Text(
          label,
          style: Theme.of(context).textTheme.labelMedium?.copyWith(
            color: selected ? AppColors.primaryDeep : AppColors.textSoft,
          ),
        ),
      ),
    );
  }
}

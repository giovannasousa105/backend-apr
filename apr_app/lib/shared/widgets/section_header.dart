import 'package:flutter/material.dart';

import '../../app/theme/app_colors.dart';
import '../../app/theme/app_spacing.dart';

class SectionHeader extends StatelessWidget {
  const SectionHeader({
    super.key,
    required this.title,
    this.eyebrow,
    this.subtitle,
    this.action,
  });

  final String title;
  final String? eyebrow;
  final String? subtitle;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              if (eyebrow != null) ...<Widget>[
                Text(
                  eyebrow!.toUpperCase(),
                  style: theme.textTheme.labelMedium?.copyWith(
                    color: AppColors.primaryDeep,
                  ),
                ),
                const SizedBox(height: AppSpacing.xs),
              ],
              Text(title, style: theme.textTheme.headlineSmall),
              if (subtitle != null) ...<Widget>[
                const SizedBox(height: AppSpacing.xs),
                Text(
                  subtitle!,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: AppColors.textSoft,
                  ),
                ),
              ],
            ],
          ),
        ),
        if (action != null) ...<Widget>[
          const SizedBox(width: AppSpacing.md),
          action!,
        ],
      ],
    );
  }
}

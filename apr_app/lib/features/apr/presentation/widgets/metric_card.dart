import 'package:flutter/material.dart';

import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_spacing.dart';
import '../../../../shared/widgets/app_badge.dart';
import '../../../../shared/widgets/app_panel.dart';

class MetricCard extends StatelessWidget {
  const MetricCard({
    super.key,
    required this.label,
    required this.value,
    required this.detail,
    this.tone = AppBadgeTone.info,
  });

  final String label;
  final String value;
  final String detail;
  final AppBadgeTone tone;

  @override
  Widget build(BuildContext context) {
    return AppPanel(
      radius: 24,
      backgroundColor: AppColors.surfaceElevated,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          AppBadge(label: label, tone: tone),
          const SizedBox(height: AppSpacing.lg),
          Text(value, style: Theme.of(context).textTheme.displaySmall),
          const SizedBox(height: AppSpacing.xs),
          Text(
            detail,
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: AppColors.textSoft),
          ),
        ],
      ),
    );
  }
}

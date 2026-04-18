import 'package:flutter/material.dart';

import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_spacing.dart';
import '../../../../shared/widgets/app_badge.dart';
import '../../../../shared/widgets/app_panel.dart';
import '../../domain/entities/apr_models.dart';

class WorkflowChrome extends StatelessWidget {
  const WorkflowChrome({
    super.key,
    required this.activeStage,
    required this.status,
    required this.onStageTap,
  });

  final WorkflowStage activeStage;
  final AprStatus status;
  final ValueChanged<WorkflowStage> onStageTap;

  @override
  Widget build(BuildContext context) {
    return AppPanel(
      radius: 28,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              const AppBadge(
                label: 'Workflow corporativo',
                tone: AppBadgeTone.info,
              ),
              const Spacer(),
              Text(
                _statusLabel(status),
                style: Theme.of(
                  context,
                ).textTheme.labelLarge?.copyWith(color: AppColors.textSoft),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.xl),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: WorkflowStage.values.map((stage) {
              final selected = stage == activeStage;
              return GestureDetector(
                onTap: () => onStageTap(stage),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 160),
                  width: 210,
                  padding: const EdgeInsets.all(AppSpacing.md),
                  decoration: BoxDecoration(
                    color: selected
                        ? AppColors.primarySoft
                        : AppColors.surfaceElevated,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: selected
                          ? AppColors.primary.withValues(alpha: 0.32)
                          : AppColors.border,
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        '${stage.index + 1}'.padLeft(2, '0'),
                        style: Theme.of(context).textTheme.labelMedium
                            ?.copyWith(color: AppColors.textMuted),
                      ),
                      const SizedBox(height: AppSpacing.xs),
                      Text(
                        stage.label,
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          color: selected
                              ? AppColors.primaryDeep
                              : AppColors.text,
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  String _statusLabel(AprStatus status) {
    switch (status) {
      case AprStatus.submitted:
        return 'Em aprovacao';
      case AprStatus.approved:
        return 'Aprovada';
      case AprStatus.inProgress:
        return 'Em execucao';
      case AprStatus.paused:
        return 'Pausada';
      case AprStatus.finished:
        return 'Finalizada';
      case AprStatus.archived:
        return 'Arquivada';
      case AprStatus.rejected:
        return 'Reprovada';
      default:
        return 'Rascunho';
    }
  }
}

import 'package:flutter/material.dart';

import '../../app/theme/app_colors.dart';
import '../../app/theme/app_spacing.dart';
import 'app_button.dart';
import 'app_panel.dart';

enum _FeedbackKind { loading, empty, error, note }

class AppFeedbackState extends StatelessWidget {
  const AppFeedbackState._({
    super.key,
    required this.title,
    required this.message,
    required _FeedbackKind kind,
    this.actionLabel,
    this.onAction,
  }) : _kind = kind;

  const AppFeedbackState.inlineLoading({
    Key? key,
    required String title,
    required String message,
  }) : this._(
         key: key,
         title: title,
         message: message,
         kind: _FeedbackKind.loading,
       );

  const AppFeedbackState.inlineEmpty({
    Key? key,
    required String title,
    required String message,
    String? actionLabel,
    VoidCallback? onAction,
  }) : this._(
         key: key,
         title: title,
         message: message,
         kind: _FeedbackKind.empty,
         actionLabel: actionLabel,
         onAction: onAction,
       );

  const AppFeedbackState.inlineError({
    Key? key,
    required String title,
    required String message,
    String? actionLabel,
    VoidCallback? onAction,
  }) : this._(
         key: key,
         title: title,
         message: message,
         kind: _FeedbackKind.error,
         actionLabel: actionLabel,
         onAction: onAction,
       );

  const AppFeedbackState.inlineNote({
    Key? key,
    required String title,
    required String message,
  }) : this._(
         key: key,
         title: title,
         message: message,
         kind: _FeedbackKind.note,
       );

  final String title;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;
  final _FeedbackKind _kind;

  @override
  Widget build(BuildContext context) {
    final icon = switch (_kind) {
      _FeedbackKind.loading => Icons.blur_circular_rounded,
      _FeedbackKind.empty => Icons.inbox_rounded,
      _FeedbackKind.error => Icons.error_outline_rounded,
      _FeedbackKind.note => Icons.info_outline_rounded,
    };
    final tone = switch (_kind) {
      _FeedbackKind.loading => AppColors.infoSoft,
      _FeedbackKind.empty => AppColors.surfaceElevated,
      _FeedbackKind.error => AppColors.dangerSoft,
      _FeedbackKind.note => AppColors.infoSoft,
    };
    final foreground = switch (_kind) {
      _FeedbackKind.error => AppColors.danger,
      _FeedbackKind.loading => AppColors.primaryDeep,
      _FeedbackKind.empty => AppColors.textSoft,
      _FeedbackKind.note => AppColors.primaryDeep,
    };

    return AppPanel(
      backgroundColor: tone,
      borderColor: Colors.transparent,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          if (_kind == _FeedbackKind.loading)
            SizedBox(
              width: 22,
              height: 22,
              child: CircularProgressIndicator(
                strokeWidth: 2.2,
                color: foreground,
              ),
            )
          else
            Icon(icon, color: foreground, size: 22),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  title,
                  style: Theme.of(
                    context,
                  ).textTheme.titleSmall?.copyWith(color: AppColors.text),
                ),
                const SizedBox(height: AppSpacing.xxs),
                Text(
                  message,
                  style: Theme.of(
                    context,
                  ).textTheme.bodyMedium?.copyWith(color: AppColors.textSoft),
                ),
                if (actionLabel != null && onAction != null) ...<Widget>[
                  const SizedBox(height: AppSpacing.md),
                  AppButton(
                    label: actionLabel!,
                    expanded: false,
                    tone: _kind == _FeedbackKind.error
                        ? AppButtonTone.danger
                        : AppButtonTone.secondary,
                    onPressed: onAction,
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

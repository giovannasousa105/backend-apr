import 'package:flutter/material.dart';

import '../../app/theme/app_colors.dart';
import '../../app/theme/app_radius.dart';
import '../../app/theme/app_spacing.dart';

enum AppButtonTone { primary, secondary, subtle, success, danger }

class AppButton extends StatefulWidget {
  const AppButton({
    super.key,
    required this.label,
    this.icon,
    this.tone = AppButtonTone.primary,
    this.onPressed,
    this.expanded = true,
  });

  final String label;
  final IconData? icon;
  final AppButtonTone tone;
  final VoidCallback? onPressed;
  final bool expanded;

  @override
  State<AppButton> createState() => _AppButtonState();
}

class _AppButtonState extends State<AppButton> {
  bool _hovered = false;
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    final enabled = widget.onPressed != null;
    final scheme = _scheme(
      widget.tone,
      enabled: enabled,
      hovered: _hovered,
      pressed: _pressed,
    );
    final child = AnimatedScale(
      scale: _pressed ? 0.985 : 1,
      duration: const Duration(milliseconds: 120),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        curve: Curves.easeOutCubic,
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
        decoration: BoxDecoration(
          color: scheme.background,
          borderRadius: BorderRadius.circular(AppRadius.md),
          border: Border.all(color: scheme.border),
          boxShadow: scheme.shadow == null
              ? const <BoxShadow>[]
              : <BoxShadow>[
                  BoxShadow(
                    color: scheme.shadow!,
                    blurRadius: 30,
                    offset: const Offset(0, 16),
                    spreadRadius: -20,
                  ),
                ],
        ),
        child: Row(
          mainAxisSize: widget.expanded ? MainAxisSize.max : MainAxisSize.min,
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            if (widget.icon != null) ...<Widget>[
              Icon(widget.icon, size: 18, color: scheme.foreground),
              const SizedBox(width: AppSpacing.xs),
            ],
            Flexible(
              child: Text(
                widget.label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(
                  context,
                ).textTheme.labelLarge?.copyWith(color: scheme.foreground),
              ),
            ),
          ],
        ),
      ),
    );

    return MouseRegion(
      cursor: enabled ? SystemMouseCursors.click : SystemMouseCursors.basic,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() {
        _hovered = false;
        _pressed = false;
      }),
      child: GestureDetector(
        onTapDown: enabled ? (_) => setState(() => _pressed = true) : null,
        onTapCancel: enabled ? () => setState(() => _pressed = false) : null,
        onTapUp: enabled ? (_) => setState(() => _pressed = false) : null,
        onTap: widget.onPressed,
        child: widget.expanded ? child : IntrinsicWidth(child: child),
      ),
    );
  }

  _ButtonScheme _scheme(
    AppButtonTone tone, {
    required bool enabled,
    required bool hovered,
    required bool pressed,
  }) {
    if (!enabled) {
      return const _ButtonScheme(
        background: AppColors.surfaceMuted,
        foreground: AppColors.textMuted,
        border: AppColors.border,
      );
    }
    switch (tone) {
      case AppButtonTone.primary:
        return _ButtonScheme(
          background: pressed
              ? AppColors.primaryDeep
              : hovered
              ? AppColors.primaryHover
              : AppColors.primary,
          foreground: Colors.white,
          border: Colors.transparent,
          shadow: AppColors.primary.withValues(alpha: 0.35),
        );
      case AppButtonTone.secondary:
        return const _ButtonScheme(
          background: AppColors.surface,
          foreground: AppColors.text,
          border: AppColors.borderStrong,
        );
      case AppButtonTone.subtle:
        return _ButtonScheme(
          background: hovered
              ? AppColors.primarySoft
              : AppColors.surfaceElevated,
          foreground: hovered ? AppColors.primaryDeep : AppColors.textSoft,
          border: hovered
              ? AppColors.primary.withValues(alpha: 0.28)
              : AppColors.border,
        );
      case AppButtonTone.success:
        return _ButtonScheme(
          background: AppColors.success,
          foreground: Colors.white,
          border: Colors.transparent,
          shadow: AppColors.success.withValues(alpha: 0.26),
        );
      case AppButtonTone.danger:
        return _ButtonScheme(
          background: AppColors.danger,
          foreground: Colors.white,
          border: Colors.transparent,
          shadow: AppColors.danger.withValues(alpha: 0.24),
        );
    }
  }
}

class _ButtonScheme {
  const _ButtonScheme({
    required this.background,
    required this.foreground,
    required this.border,
    this.shadow,
  });

  final Color background;
  final Color foreground;
  final Color border;
  final Color? shadow;
}

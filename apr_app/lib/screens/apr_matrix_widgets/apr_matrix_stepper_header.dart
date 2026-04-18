import 'package:flutter/material.dart';

class AprMatrixStepperHeader extends StatelessWidget {
  final int activeStep;

  const AprMatrixStepperHeader({super.key, required this.activeStep});

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        _StepPill(index: 0, label: 'Criar', activeStep: activeStep),
        _StepPill(index: 1, label: 'Matriz', activeStep: activeStep),
        _StepPill(index: 2, label: 'Controles', activeStep: activeStep),
        _StepPill(index: 3, label: 'Aprovacao', activeStep: activeStep),
        _StepPill(index: 4, label: 'Relatorio', activeStep: activeStep),
      ],
    );
  }
}

class _StepPill extends StatelessWidget {
  final int index;
  final String label;
  final int activeStep;

  const _StepPill({
    required this.index,
    required this.label,
    required this.activeStep,
  });

  @override
  Widget build(BuildContext context) {
    final done = index < activeStep;
    final isActive = index == activeStep;

    final bg = isActive
        ? const Color(0xFFE7F0FF)
        : (done ? const Color(0xFFEAFBF1) : const Color(0xFFF8FAFC));
    final border = isActive
        ? const Color(0xFF0B3C5D)
        : (done ? const Color(0xFF22C55E) : const Color(0xFFDCE3EE));
    final fg = isActive
        ? const Color(0xFF0B3C5D)
        : (done ? const Color(0xFF166534) : const Color(0xFF475569));

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: border),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (done)
            const Icon(Icons.check, size: 14, color: Color(0xFF16A34A))
          else
            Text(
              '${index + 1}',
              style: TextStyle(
                fontSize: 12,
                color: fg,
                fontWeight: FontWeight.w700,
              ),
            ),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              color: fg,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

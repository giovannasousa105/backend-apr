import 'package:flutter/material.dart';

class AprMatrixSummaryPanel extends StatelessWidget {
  final String elaborationDateLabel;
  final int validSteps;
  final int riskValue;
  final int stepScoreTotal;
  final int stepScoreMax;
  final String classification;
  final Color riskColor;
  final Map<String, int> buckets;
  final List<String> appliedControls;
  final List<String> blockingIssues;
  final bool autosaving;
  final bool saving;
  final bool canAdvance;
  final VoidCallback onSave;
  final VoidCallback onAdvance;

  const AprMatrixSummaryPanel({
    super.key,
    required this.elaborationDateLabel,
    required this.validSteps,
    required this.riskValue,
    required this.stepScoreTotal,
    required this.stepScoreMax,
    required this.classification,
    required this.riskColor,
    required this.buckets,
    required this.appliedControls,
    required this.blockingIssues,
    required this.autosaving,
    required this.saving,
    required this.canAdvance,
    required this.onSave,
    required this.onAdvance,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.zero,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: const BorderSide(color: Color(0xFFDCE5F2)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Resumo & Regras',
              style: TextStyle(
                fontWeight: FontWeight.w700,
                color: Color(0xFF0B3C5D),
              ),
            ),
            const SizedBox(height: 6),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                color: const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFFDCE3EE)),
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.calendar_month_outlined,
                    size: 14,
                    color: Color(0xFF475569),
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      'Data de elaboracao: $elaborationDateLabel',
                      style: const TextStyle(
                        fontSize: 12.5,
                        fontWeight: FontWeight.w600,
                        color: Color(0xFF334155),
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 4),
            const Text(
              'PxS Total (Obrigatorio)',
              style: TextStyle(fontSize: 12.5, color: Color(0xFF334155)),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: [
                _summaryChip(
                  'Baixo',
                  buckets['low'] ?? 0,
                  const Color(0xFF16A34A),
                ),
                _summaryChip(
                  'Medio',
                  buckets['medium'] ?? 0,
                  const Color(0xFFD97706),
                ),
                _summaryChip(
                  'Alto',
                  buckets['high'] ?? 0,
                  const Color(0xFFDC2626),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              validSteps == 0
                  ? 'Sem risco calculado.'
                  : 'Matriz: $riskValue ($classification) | Passos: $stepScoreTotal | Pico: $stepScoreMax',
              style: TextStyle(
                fontSize: 12.5,
                fontWeight: FontWeight.w600,
                color: validSteps == 0 ? const Color(0xFF64748B) : riskColor,
              ),
            ),
            const SizedBox(height: 6),
            const Row(
              children: [
                Icon(Icons.info_outline, size: 14, color: Color(0xFF64748B)),
                SizedBox(width: 6),
                Text(
                  'NRs / ISO / OSHA',
                  style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                ),
              ],
            ),
            const SizedBox(height: 10),
            const Divider(height: 1),
            _sectionHeader('Controles sugeridos'),
            const Divider(height: 1),
            _sectionHeader('Controles aplicados'),
            const SizedBox(height: 8),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFFDCE3EE)),
              ),
              child: appliedControls.isEmpty
                  ? const Text(
                      'Nenhum controle aplicado ainda.',
                      style: TextStyle(
                        fontSize: 12.5,
                        color: Color(0xFF64748B),
                      ),
                    )
                  : Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: appliedControls
                          .take(6)
                          .map(
                            (control) => Padding(
                              padding: const EdgeInsets.symmetric(vertical: 2),
                              child: Row(
                                children: [
                                  const Icon(
                                    Icons.check_box_outline_blank_rounded,
                                    size: 16,
                                    color: Color(0xFF64748B),
                                  ),
                                  const SizedBox(width: 6),
                                  Expanded(
                                    child: Text(
                                      control,
                                      style: const TextStyle(fontSize: 12.5),
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          )
                          .toList(),
                    ),
            ),
            const SizedBox(height: 10),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton(
                onPressed: (autosaving || saving) ? null : onSave,
                child: Text(autosaving ? 'Salvando...' : 'Salvar'),
              ),
            ),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: canAdvance ? onAdvance : null,
                icon: const Icon(Icons.arrow_forward_rounded),
                label: Text(saving ? 'Salvando...' : 'Avancar para Aprovacao'),
              ),
            ),
            const SizedBox(height: 8),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(
                  Icons.info_outline,
                  size: 14,
                  color: Color(0xFF334155),
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    blockingIssues.isEmpty
                        ? 'Resumo gerado com base no PxS da matriz e de todos os passos.'
                        : blockingIssues.first,
                    style: TextStyle(
                      fontSize: 12,
                      color: blockingIssues.isEmpty
                          ? const Color(0xFF334155)
                          : const Color(0xFFB45309),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _sectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Expanded(
            child: Text(
              title,
              style: const TextStyle(
                fontWeight: FontWeight.w700,
                color: Color(0xFF334155),
              ),
            ),
          ),
          const Icon(Icons.chevron_right_rounded, color: Color(0xFF64748B)),
        ],
      ),
    );
  }

  Widget _summaryChip(String label, int count, Color tone) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: tone.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: tone.withValues(alpha: 0.35)),
      ),
      child: Text(
        '$label: $count',
        style: TextStyle(
          color: tone,
          fontSize: 12,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

import 'package:flutter/material.dart';

import 'apr_matrix_step_view_data.dart';

class AprMatrixStepCard extends StatelessWidget {
  final AprMatrixStepViewData step;
  final VoidCallback onEdit;
  final VoidCallback onDuplicate;
  final VoidCallback onRemove;
  final VoidCallback onSelectEvidence;
  final VoidCallback onGenerateEvidenceIa;

  const AprMatrixStepCard({
    super.key,
    required this.step,
    required this.onEdit,
    required this.onDuplicate,
    required this.onRemove,
    required this.onSelectEvidence,
    required this.onGenerateEvidenceIa,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(top: 10),
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
            Row(
              children: [
                Container(
                  width: 28,
                  height: 28,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: const Color(0xFF0B3C5D),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    '${step.index + 1}',
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    step.title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                ),
                Text(
                  '${step.riskLevel} - PxS ${step.riskScore}',
                  style: TextStyle(
                    fontSize: 11,
                    color: step.riskColor,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              step.hazards.isEmpty ? 'Sem perigos' : 'Perigos: ${step.hazards}',
            ),
            const SizedBox(height: 4),
            Text(
              step.consequences.isEmpty
                  ? 'Sem consequencias'
                  : 'Consequencias: ${step.consequences}',
            ),
            const SizedBox(height: 4),
            Text(
              step.safeguards.isEmpty
                  ? 'Sem salvaguardas'
                  : 'Salvaguardas: ${step.safeguards}',
            ),
            const SizedBox(height: 4),
            Text(step.epis.isEmpty ? 'Sem EPIs' : 'EPIs: ${step.epis}'),
            if (step.norms.trim().isNotEmpty) ...[
              const SizedBox(height: 4),
              Text('Normas: ${step.norms}'),
            ],
            const SizedBox(height: 8),
            if (step.evidencePreviewBytes != null) ...[
              Container(
                width: 84,
                height: 56,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFFBEE2D3)),
                ),
                clipBehavior: Clip.antiAlias,
                child: Image.memory(
                  step.evidencePreviewBytes!,
                  fit: BoxFit.cover,
                  gaplessPlayback: true,
                  errorBuilder: (_, error, stackTrace) => const ColoredBox(
                    color: Color(0xFFE2E8F0),
                    child: Icon(Icons.image_not_supported_outlined, size: 18),
                  ),
                ),
              ),
              const SizedBox(height: 8),
            ],
            Row(
              children: [
                Expanded(
                  child: Text(
                    step.evidenceName ?? 'Sem evidencia',
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                TextButton(
                  onPressed: onSelectEvidence,
                  child: Text(
                    step.hasEvidence ? 'Trocar foto' : 'Adicionar foto',
                  ),
                ),
                const SizedBox(width: 8),
                OutlinedButton.icon(
                  onPressed: step.generatingEvidence
                      ? null
                      : onGenerateEvidenceIa,
                  icon: step.generatingEvidence
                      ? const SizedBox(
                          width: 14,
                          height: 14,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.auto_awesome, size: 16),
                  label: Text(
                    step.generatingEvidence
                        ? 'Gerando IA...'
                        : 'Gerar imagem IA',
                  ),
                ),
              ],
            ),
            Wrap(
              spacing: 8,
              children: [
                OutlinedButton.icon(
                  onPressed: onEdit,
                  icon: const Icon(Icons.edit_outlined, size: 18),
                  label: const Text('Editar'),
                ),
                OutlinedButton.icon(
                  onPressed: onDuplicate,
                  icon: const Icon(Icons.copy_outlined, size: 18),
                  label: const Text('Duplicar'),
                ),
                IconButton(
                  onPressed: onRemove,
                  icon: const Icon(Icons.delete_outline),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

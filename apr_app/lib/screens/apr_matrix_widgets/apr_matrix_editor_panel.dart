import 'dart:typed_data';

import 'package:flutter/material.dart';

import 'apr_matrix_step_card.dart';
import 'apr_matrix_step_view_data.dart';

class AprMatrixEditorPanel extends StatelessWidget {
  static const Map<String, String> _frameworkLabels = {
    'ISO_45001': 'ISO 45001',
    'OSHA_1926': 'OSHA 1926',
    'ANSI_B11': 'ANSI B11',
  };

  final TextEditingController descricaoController;
  final VoidCallback onGenerateIa;
  final bool generatingIa;
  final VoidCallback onApplyModel;
  final VoidCallback onSelectEvidence;
  final Uint8List? selectedEvidenceBytes;
  final VoidCallback onAddStep;
  final List<AprMatrixStepViewData> steps;
  final ValueChanged<int> onEditStep;
  final ValueChanged<int> onDuplicateStep;
  final ValueChanged<int> onRemoveStep;
  final ValueChanged<int> onSelectStepEvidence;
  final ValueChanged<int> onGenerateStepEvidenceIa;
  final ReorderCallback onReorderSteps;
  final Map<String, bool> ferramentas;
  final Map<String, bool> episGerais;
  final ValueChanged<String> onToggleFerramenta;
  final ValueChanged<String> onToggleEpi;
  final Map<String, bool> optionalNormFrameworks;
  final bool loadingNormProfile;
  final bool savingNormProfile;
  final String riskEngineMode;
  final String resolvedNormScope;
  final ValueChanged<String> onToggleNormFramework;

  const AprMatrixEditorPanel({
    super.key,
    required this.descricaoController,
    required this.onGenerateIa,
    required this.generatingIa,
    required this.onApplyModel,
    required this.onSelectEvidence,
    required this.selectedEvidenceBytes,
    required this.onAddStep,
    required this.steps,
    required this.onEditStep,
    required this.onDuplicateStep,
    required this.onRemoveStep,
    required this.onSelectStepEvidence,
    required this.onGenerateStepEvidenceIa,
    required this.onReorderSteps,
    required this.ferramentas,
    required this.episGerais,
    required this.onToggleFerramenta,
    required this.onToggleEpi,
    required this.optionalNormFrameworks,
    required this.loadingNormProfile,
    required this.savingNormProfile,
    required this.riskEngineMode,
    required this.resolvedNormScope,
    required this.onToggleNormFramework,
  });

  @override
  Widget build(BuildContext context) {
    final sortedTools = ferramentas.keys.toList()..sort();
    final sortedEpis = episGerais.keys.toList()..sort();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Card(
          margin: EdgeInsets.zero,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
            side: const BorderSide(color: Color(0xFFDCE5F2)),
          ),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'IA e modelo tecnico',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF0B3C5D),
                  ),
                ),
                const SizedBox(height: 4),
                const Text(
                  'Gerar com IA e aplicar modelo para preencher os passos da atividade.',
                  style: TextStyle(fontSize: 12.5, color: Color(0xFF64748B)),
                ),
                const SizedBox(height: 10),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF8FAFC),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFDCE3EE)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Normas Ativas',
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          color: Color(0xFF0B3C5D),
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        loadingNormProfile
                            ? 'Carregando perfil normativo...'
                            : 'NR fixa (obrigatoria) + frameworks opcionais para orientar a IA.',
                        style: const TextStyle(
                          fontSize: 12.5,
                          color: Color(0xFF64748B),
                        ),
                      ),
                      const SizedBox(height: 8),
                      _normRow(
                        label: 'NR (base obrigatoria)',
                        value: true,
                        enabled: false,
                        onChanged: null,
                      ),
                      const SizedBox(height: 4),
                      ..._frameworkLabels.entries.map((entry) {
                        final frameworkId = entry.key;
                        return _normRow(
                          label: entry.value,
                          value: optionalNormFrameworks[frameworkId] ?? false,
                          enabled: !loadingNormProfile && !savingNormProfile,
                          onChanged: () => onToggleNormFramework(frameworkId),
                        );
                      }),
                      const SizedBox(height: 6),
                      Text(
                        'Modo: $riskEngineMode  •  Escopo: $resolvedNormScope',
                        style: const TextStyle(
                          fontSize: 11.5,
                          color: Color(0xFF64748B),
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: descricaoController,
                  minLines: 3,
                  maxLines: 5,
                  decoration: _fieldDecoration('Descricao da atividade'),
                ),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    ElevatedButton.icon(
                      onPressed: generatingIa ? null : onGenerateIa,
                      icon: const Icon(Icons.auto_awesome),
                      label: Text(
                        generatingIa ? 'Gerando IA...' : 'Gerar com IA',
                      ),
                    ),
                    OutlinedButton.icon(
                      onPressed: onApplyModel,
                      icon: const Icon(Icons.library_books),
                      label: const Text('Aplicar modelo'),
                    ),
                    OutlinedButton.icon(
                      onPressed: onSelectEvidence,
                      icon: const Icon(Icons.photo),
                      label: const Text('Evidencia tecnica'),
                    ),
                  ],
                ),
                if (selectedEvidenceBytes != null) ...[
                  const SizedBox(height: 10),
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: const Color(0xFFEFFAF5),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: const Color(0xFFBEE2D3)),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        ClipRRect(
                          borderRadius: BorderRadius.circular(6),
                          child: Image.memory(
                            selectedEvidenceBytes!,
                            width: 72,
                            height: 48,
                            fit: BoxFit.cover,
                            gaplessPlayback: true,
                            errorBuilder: (_, error, stackTrace) =>
                                const ColoredBox(
                                  color: Color(0xFFE2E8F0),
                                  child: SizedBox(
                                    width: 72,
                                    height: 48,
                                    child: Icon(
                                      Icons.image_not_supported_outlined,
                                      size: 18,
                                    ),
                                  ),
                                ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        const Text(
                          'Imagem pronta para IA',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: Color(0xFF166534),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            const Expanded(
              child: Text(
                'Passos & Salvaguardas',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                  color: Color(0xFF0B3C5D),
                ),
              ),
            ),
            FilledButton.icon(
              onPressed: onAddStep,
              icon: const Icon(Icons.add, size: 18),
              label: const Text('Adicionar passo'),
            ),
          ],
        ),
        const SizedBox(height: 8),
        if (steps.isNotEmpty)
          Card(
            margin: const EdgeInsets.only(bottom: 10),
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
                    'Resumo dos passos',
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      color: Color(0xFF0B3C5D),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    steps.length > 1
                        ? 'Arraste para ordenar e toque para editar.'
                        : 'Toque para editar o passo.',
                    style: const TextStyle(
                      fontSize: 12.5,
                      color: Color(0xFF64748B),
                    ),
                  ),
                  const SizedBox(height: 8),
                  ReorderableListView.builder(
                    shrinkWrap: true,
                    buildDefaultDragHandles: false,
                    physics: const NeverScrollableScrollPhysics(),
                    onReorder: onReorderSteps,
                    itemCount: steps.length,
                    itemBuilder: (context, index) {
                      final step = steps[index];
                      return Container(
                        key: ValueKey('step-summary-${step.keyId}'),
                        margin: const EdgeInsets.only(bottom: 6),
                        decoration: BoxDecoration(
                          color: const Color(0xFFF8FAFC),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: const Color(0xFFDCE3EE)),
                        ),
                        child: InkWell(
                          borderRadius: BorderRadius.circular(10),
                          onTap: () => onEditStep(index),
                          child: Padding(
                            padding: const EdgeInsets.all(10),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Container(
                                      width: 22,
                                      height: 22,
                                      alignment: Alignment.center,
                                      decoration: BoxDecoration(
                                        color: const Color(0xFF0B3C5D),
                                        borderRadius: BorderRadius.circular(
                                          999,
                                        ),
                                      ),
                                      child: Text(
                                        '${index + 1}',
                                        style: const TextStyle(
                                          color: Colors.white,
                                          fontWeight: FontWeight.w700,
                                          fontSize: 11,
                                        ),
                                      ),
                                    ),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: Text(
                                        'Passo ${index + 1} - ${step.title}',
                                        maxLines: 2,
                                        overflow: TextOverflow.ellipsis,
                                        style: const TextStyle(
                                          fontWeight: FontWeight.w700,
                                          color: Color(0xFF0F172A),
                                        ),
                                      ),
                                    ),
                                    const SizedBox(width: 8),
                                    Text(
                                      '${step.riskLevel} - PxS ${step.riskScore}',
                                      style: TextStyle(
                                        fontSize: 11,
                                        color: step.riskColor,
                                        fontWeight: FontWeight.w700,
                                      ),
                                    ),
                                    const SizedBox(width: 6),
                                    IconButton(
                                      onPressed: () => onEditStep(index),
                                      icon: const Icon(
                                        Icons.edit_outlined,
                                        size: 18,
                                      ),
                                      visualDensity: VisualDensity.compact,
                                      padding: EdgeInsets.zero,
                                      constraints: const BoxConstraints(
                                        minWidth: 30,
                                        minHeight: 30,
                                      ),
                                    ),
                                    ReorderableDragStartListener(
                                      index: index,
                                      child: const Icon(
                                        Icons.drag_indicator_rounded,
                                        color: Color(0xFF64748B),
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 6),
                                _summaryLine('Perigos', step.hazards),
                                const SizedBox(height: 3),
                                _summaryLine(
                                  'Consequencias',
                                  step.consequences,
                                ),
                                const SizedBox(height: 3),
                                _summaryLine('Salvaguardas', step.safeguards),
                                const SizedBox(height: 3),
                                _summaryLine('EPIs', step.epis),
                                if (step.norms.trim().isNotEmpty) ...[
                                  const SizedBox(height: 3),
                                  _summaryLine('Normas', step.norms),
                                ],
                              ],
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),
          ),
        if (steps.isEmpty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFFF8FAFC),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFFDCE3EE)),
            ),
            child: const Text(
              'Nenhum passo ainda. Gere por IA ou adicione manualmente.',
            ),
          )
        else
          ...steps.map(
            (step) => AprMatrixStepCard(
              step: step,
              onEdit: () => onEditStep(step.index),
              onDuplicate: () => onDuplicateStep(step.index),
              onRemove: () => onRemoveStep(step.index),
              onSelectEvidence: () => onSelectStepEvidence(step.index),
              onGenerateEvidenceIa: () => onGenerateStepEvidenceIa(step.index),
            ),
          ),
        const SizedBox(height: 12),
        Card(
          margin: EdgeInsets.zero,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
            side: const BorderSide(color: Color(0xFFDCE5F2)),
          ),
          child: Theme(
            data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
            child: ExpansionTile(
              initiallyExpanded: true,
              title: const Text(
                'Controles sugeridos',
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF0B3C5D),
                ),
              ),
              subtitle: const Text('Ferramentas, EPIs e energias'),
              childrenPadding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
              children: [
                ...sortedTools.map(
                  (tool) => CheckboxListTile(
                    title: Text(tool),
                    value: ferramentas[tool],
                    dense: true,
                    visualDensity: VisualDensity.compact,
                    contentPadding: EdgeInsets.zero,
                    controlAffinity: ListTileControlAffinity.leading,
                    onChanged: (_) => onToggleFerramenta(tool),
                  ),
                ),
                const Divider(),
                ...sortedEpis.map(
                  (epi) => CheckboxListTile(
                    title: Text(epi),
                    value: episGerais[epi],
                    dense: true,
                    visualDensity: VisualDensity.compact,
                    contentPadding: EdgeInsets.zero,
                    controlAffinity: ListTileControlAffinity.leading,
                    onChanged: (_) => onToggleEpi(epi),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _summaryLine(String label, String value) {
    final normalized = value.trim().isEmpty ? 'Nao informado.' : value.trim();
    return Text.rich(
      TextSpan(
        children: [
          TextSpan(
            text: '$label: ',
            style: const TextStyle(fontWeight: FontWeight.w700),
          ),
          TextSpan(text: normalized),
        ],
      ),
      style: const TextStyle(color: Color(0xFF334155), height: 1.3),
    );
  }

  InputDecoration _fieldDecoration(String labelText, {String? hintText}) {
    return InputDecoration(
      labelText: labelText,
      hintText: hintText,
      filled: true,
      fillColor: Colors.white,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: Color(0xFFDCE3EE)),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: Color(0xFFDCE3EE)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: Color(0xFF0B3C5D), width: 1.4),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
    );
  }

  Widget _normRow({
    required String label,
    required bool value,
    required bool enabled,
    required VoidCallback? onChanged,
  }) {
    return Row(
      children: [
        Expanded(
          child: Text(
            label,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: enabled
                  ? const Color(0xFF1E293B)
                  : const Color(0xFF64748B),
            ),
          ),
        ),
        Switch.adaptive(
          value: value,
          onChanged: enabled ? (_) => onChanged?.call() : null,
        ),
      ],
    );
  }
}

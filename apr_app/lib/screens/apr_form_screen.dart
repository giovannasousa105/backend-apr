import 'package:flutter/material.dart';

import '../config/api_config.dart';
import '../services/api_service.dart';
import '../widgets/app_back_button.dart';

class AprFormScreen extends StatefulWidget {
  final VoidCallback? onBack;
  final VoidCallback? onOpenAprs;
  final VoidCallback? onOpenMatriz;
  final void Function(int legacyAprId, String atividade)? onOpenMatrizWithAprId;
  final VoidCallback? onOpenCatalogos;
  final String? initialAprId;

  const AprFormScreen({
    super.key,
    this.onBack,
    this.onOpenAprs,
    this.onOpenMatriz,
    this.onOpenMatrizWithAprId,
    this.onOpenCatalogos,
    this.initialAprId,
  });

  @override
  State<AprFormScreen> createState() => _AprFormScreenState();
}

class _AprFormScreenState extends State<AprFormScreen> {
  late final ApiService _api;

  final _areaSectorCtrl = TextEditingController();
  final _projectNameCtrl = TextEditingController();
  final _projectDescriptionCtrl = TextEditingController();

  final List<String> _siteOptions = <String>[
    'ARAGUARI',
    'CACHOEIRA DOURADA',
    'CAMPO VERDE',
    'CENTRO DE TREINAMENTO BAYER',
    'COXILHA',
  ];

  final List<String> _activityCharacteristicOptions = <String>[
    'BARRAGENS / PRESAS',
    'CALDEIRAS E VASOS DE PRESSAO',
    'CIVIL',
    'DRENAGEM',
    'ELETRICA E AUTOMACAO',
  ];

  final List<String> _evaluatorOptions = <String>[
    'Giovanna Sousa',
    'Otavio Campos',
    'Gleiser Goncalves',
    'Equipe Engesafety',
  ];

  String? _selectedSite;
  String? _selectedActivityCharacteristic;
  String? _selectedEvaluator;

  bool _saving = false;
  bool _creating = false;
  bool _loadingExisting = false;

  String? _aprId;
  String? _aprCode;
  String _status = 'draft';

  @override
  void initState() {
    super.initState();
    _api = ApiService(baseUrl: resolveBaseUrl());
    _loadInitialAprIfAny();
  }

  @override
  void dispose() {
    _areaSectorCtrl.dispose();
    _projectNameCtrl.dispose();
    _projectDescriptionCtrl.dispose();
    super.dispose();
  }

  String? _ensureOption(String value, List<String> options) {
    final normalized = value.trim();
    if (normalized.isEmpty) return null;
    if (!options.contains(normalized)) {
      options.insert(0, normalized);
    }
    return normalized;
  }

  String _extractLabeledValue(String raw, String label) {
    final normalizedLabel = label.toLowerCase();
    final parts = raw.split(RegExp(r'[\n|]'));
    for (final part in parts) {
      final trimmed = part.trim();
      if (trimmed.toLowerCase().startsWith(normalizedLabel)) {
        return trimmed.substring(label.length).trim();
      }
    }
    return '';
  }

  Future<void> _loadInitialAprIfAny() async {
    final initialAprId = widget.initialAprId?.trim();
    if (initialAprId == null || initialAprId.isEmpty) {
      return;
    }

    setState(() => _loadingExisting = true);
    try {
      final data = await _api.getAprMvpByExternalId(initialAprId);
      if (!mounted) return;

      final locationRaw = data['location']?.toString() ?? '';
      final activityRaw = data['activity']?.toString() ?? '';

      final site = _extractLabeledValue(locationRaw, 'Site:');
      final area = _extractLabeledValue(locationRaw, 'Area/Setor:');
      final characteristic = _extractLabeledValue(
        activityRaw,
        'Caracteristica da atividade:',
      );
      final description = _extractLabeledValue(
        activityRaw,
        'Descricao do projeto/atividade:',
      );
      final evaluators = _extractLabeledValue(
        activityRaw,
        'Elaboradores/Avaliadores:',
      );

      final fallbackArea = area.isEmpty && site.isEmpty
          ? locationRaw.trim()
          : '';
      final fallbackDescription =
          description.isEmpty && characteristic.isEmpty && evaluators.isEmpty
          ? activityRaw.trim()
          : '';

      setState(() {
        _aprId = data['id']?.toString() ?? initialAprId;
        _aprCode = data['code']?.toString();
        _status = (data['status']?.toString() ?? 'draft').toLowerCase();

        _projectNameCtrl.text = data['title']?.toString() ?? '';
        _areaSectorCtrl.text = area.isNotEmpty ? area : fallbackArea;
        _projectDescriptionCtrl.text = description.isNotEmpty
            ? description
            : fallbackDescription;

        _selectedSite = _ensureOption(site, _siteOptions);
        _selectedActivityCharacteristic = _ensureOption(
          characteristic,
          _activityCharacteristicOptions,
        );
        _selectedEvaluator = _ensureOption(evaluators, _evaluatorOptions);
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Falha ao carregar APR para edicao: $e')),
      );
    } finally {
      if (mounted) {
        setState(() => _loadingExisting = false);
      }
    }
  }

  String _buildLocation() {
    final parts = <String>[];
    if ((_selectedSite ?? '').trim().isNotEmpty) {
      parts.add('Site: ${_selectedSite!.trim()}');
    }
    final area = _areaSectorCtrl.text.trim();
    if (area.isNotEmpty) {
      parts.add('Area/Setor: $area');
    }
    return parts.join(' | ');
  }

  String _buildActivity() {
    final parts = <String>[];
    if ((_selectedActivityCharacteristic ?? '').trim().isNotEmpty) {
      parts.add(
        'Caracteristica da atividade: ${_selectedActivityCharacteristic!.trim()}',
      );
    }
    final description = _projectDescriptionCtrl.text.trim();
    if (description.isNotEmpty) {
      parts.add('Descricao do projeto/atividade: $description');
    }
    if ((_selectedEvaluator ?? '').trim().isNotEmpty) {
      parts.add('Elaboradores/Avaliadores: ${_selectedEvaluator!.trim()}');
    }
    return parts.join('\n');
  }

  bool _validateBeforeSave() {
    if ((_selectedSite ?? '').trim().isEmpty) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Selecione o site')));
      return false;
    }

    if ((_selectedActivityCharacteristic ?? '').trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Selecione a caracteristica da atividade'),
        ),
      );
      return false;
    }

    if (_projectNameCtrl.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Informe o nome do projeto')),
      );
      return false;
    }

    if ((_selectedEvaluator ?? '').trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Selecione elaboradores/avaliadores')),
      );
      return false;
    }

    return true;
  }

  Future<bool> _saveApr({bool silent = false}) async {
    if (!_validateBeforeSave()) return false;

    setState(() => _saving = true);
    try {
      final data = _aprId == null
          ? await _api.createAprMvp(
              title: _projectNameCtrl.text.trim(),
              location: _buildLocation(),
              activity: _buildActivity(),
              hazards: const [],
              controls: const [],
            )
          : await _api.updateAprMvp(
              aprId: _aprId!,
              title: _projectNameCtrl.text.trim(),
              location: _buildLocation(),
              activity: _buildActivity(),
              hazards: const [],
              controls: const [],
            );

      if (!mounted) return false;
      setState(() {
        _aprId = data['id']?.toString() ?? _aprId;
        _aprCode = data['code']?.toString() ?? _aprCode;
        _status = (data['status']?.toString() ?? 'draft').toLowerCase();
      });

      if (!silent) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('APR salva com sucesso')));
      }
      return true;
    } catch (e) {
      if (!mounted) return false;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Falha ao salvar APR. $e')));
      return false;
    } finally {
      if (mounted) {
        setState(() => _saving = false);
      }
    }
  }

  Future<void> _createApr() async {
    if (_creating) return;
    setState(() => _creating = true);

    try {
      final saved = await _saveApr(silent: true);
      if (!saved || _aprId == null || _aprId!.isEmpty || !mounted) {
        return;
      }

      if (_status.toLowerCase() != 'submitted') {
        final data = await _api.submitAprMvp(_aprId!);
        if (!mounted) return;
        setState(() => _status = data['status']?.toString() ?? 'submitted');
      }

      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('APR criada com sucesso')));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Falha ao criar APR. $e')));
    } finally {
      if (mounted) {
        setState(() => _creating = false);
      }
    }
  }

  Future<void> _openMatrizFromCurrentApr() async {
    if (widget.onOpenMatrizWithAprId == null) {
      debugPrint(
        '[AprFormScreen] open matrix without legacy resolver callback',
      );
      widget.onOpenMatriz?.call();
      return;
    }

    if (_aprId == null || _aprId!.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Salve ou crie a APR antes de abrir a matriz'),
        ),
      );
      return;
    }

    int? legacyAprId = int.tryParse(_aprId!);
    if (legacyAprId == null) {
      try {
        legacyAprId = await _api.resolveLegacyAprIdFromMvpId(_aprId!);
      } catch (e) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Falha ao localizar APR na Matriz: $e')),
        );
        return;
      }
    }

    if (!mounted) return;
    if (legacyAprId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Nao foi possivel localizar a APR salva')),
      );
      return;
    }

    final atividade = _projectNameCtrl.text.trim().isNotEmpty
        ? _projectNameCtrl.text.trim()
        : (_selectedActivityCharacteristic ?? 'APR');
    debugPrint(
      '[AprFormScreen] open matrix aprExternalId=$_aprId legacyAprId=$legacyAprId atividade="$atividade"',
    );
    widget.onOpenMatrizWithAprId!.call(legacyAprId, atividade);
  }

  Widget _buildDropdown({
    required String label,
    required String? value,
    required List<String> options,
    required ValueChanged<String?> onChanged,
    bool readOnly = false,
  }) {
    return DropdownButtonFormField<String>(
      key: ValueKey<String>('${label}_${value ?? 'empty'}'),
      initialValue: value,
      decoration: InputDecoration(
        labelText: label,
        border: const OutlineInputBorder(),
      ),
      isExpanded: true,
      items: options
          .map(
            (item) => DropdownMenuItem<String>(value: item, child: Text(item)),
          )
          .toList(),
      onChanged: readOnly ? null : onChanged,
    );
  }

  @override
  Widget build(BuildContext context) {
    final isSubmitted = _status.toLowerCase() == 'submitted';
    final isArchived = _status.toLowerCase() == 'archived';
    final readOnly = isSubmitted || isArchived || _loadingExisting;

    return Scaffold(
      appBar: AppBar(
        leading: AppBackButton(onFallback: widget.onBack),
        title: Text(
          widget.initialAprId == null ? 'Cadastrar APR' : 'Editar APR',
        ),
        actions: [
          if (widget.onOpenAprs != null)
            IconButton(
              tooltip: 'Ir para APRs',
              onPressed: widget.onOpenAprs,
              icon: const Icon(Icons.list),
            ),
          if (widget.onOpenMatriz != null ||
              widget.onOpenMatrizWithAprId != null)
            IconButton(
              tooltip: 'Ir para Matriz',
              onPressed: _openMatrizFromCurrentApr,
              icon: const Icon(Icons.grid_view),
            ),
          if (widget.onOpenCatalogos != null)
            IconButton(
              tooltip: 'Ir para Catalogos',
              onPressed: widget.onOpenCatalogos,
              icon: const Icon(Icons.menu_book_outlined),
            ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 760),
              child: Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Theme.of(context).dividerColor),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'CADASTRAR NOVA APR',
                      style: TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text('ID da APR: ${_aprCode ?? _aprId ?? '-'}'),
                    const SizedBox(height: 2),
                    Text('Status: ${_aprId == null ? 'nao salvo' : _status}'),
                    if (_loadingExisting) ...[
                      const SizedBox(height: 10),
                      const LinearProgressIndicator(),
                    ],
                    const SizedBox(height: 16),
                    _buildDropdown(
                      label: 'Site',
                      value: _selectedSite,
                      options: _siteOptions,
                      onChanged: (value) =>
                          setState(() => _selectedSite = value),
                      readOnly: readOnly,
                    ),
                    const SizedBox(height: 12),
                    _buildDropdown(
                      label: 'Caracteristicas da Atividade',
                      value: _selectedActivityCharacteristic,
                      options: _activityCharacteristicOptions,
                      onChanged: (value) => setState(
                        () => _selectedActivityCharacteristic = value,
                      ),
                      readOnly: readOnly,
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _areaSectorCtrl,
                      readOnly: readOnly,
                      decoration: const InputDecoration(
                        labelText: 'Area/Setor',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _projectNameCtrl,
                      readOnly: readOnly,
                      decoration: const InputDecoration(
                        labelText: 'Nome do Projeto/Atividade',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _projectDescriptionCtrl,
                      readOnly: readOnly,
                      minLines: 4,
                      maxLines: 8,
                      decoration: const InputDecoration(
                        labelText: 'Descricao do Projeto/Atividade',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),
                    _buildDropdown(
                      label: 'Elaboradores/Avaliadores',
                      value: _selectedEvaluator,
                      options: _evaluatorOptions,
                      onChanged: (value) =>
                          setState(() => _selectedEvaluator = value),
                      readOnly: readOnly,
                    ),
                    const SizedBox(height: 20),
                    Row(
                      children: [
                        Expanded(
                          child: SizedBox(
                            height: 48,
                            child: OutlinedButton(
                              onPressed: (_saving || _creating || readOnly)
                                  ? null
                                  : () => _saveApr(),
                              child: _saving
                                  ? const SizedBox(
                                      height: 20,
                                      width: 20,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                      ),
                                    )
                                  : const Text('Salvar APR'),
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: SizedBox(
                            height: 48,
                            child: FilledButton(
                              onPressed: (_saving || _creating || readOnly)
                                  ? null
                                  : _createApr,
                              child: _creating
                                  ? const SizedBox(
                                      height: 20,
                                      width: 20,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                      ),
                                    )
                                  : const Text('Criar APR'),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
          if (widget.onOpenMatriz != null ||
              widget.onOpenMatrizWithAprId != null) ...[
            const SizedBox(height: 10),
            Center(
              child: TextButton(
                onPressed: _openMatrizFromCurrentApr,
                child: const Text('Abrir Matriz de Risco'),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

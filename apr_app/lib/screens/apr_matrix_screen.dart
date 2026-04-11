import 'dart:async';
import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import '../models/apr.dart';
import '../config/api_config.dart';
import '../services/api_service.dart';
import '../text_normalizer.dart';
import '../widgets/app_back_button.dart';
import 'apr_matrix_widgets/apr_matrix_editor_panel.dart';
import 'apr_matrix_widgets/apr_matrix_step_view_data.dart';
import 'apr_matrix_widgets/apr_matrix_stepper_header.dart';
import 'apr_matrix_widgets/apr_matrix_summary_panel.dart';
import 'apr_approval_screen.dart';
import 'apr_templates_screen.dart';

class AprMatrixScreen extends StatefulWidget {
  final Apr apr;
  final VoidCallback? onBack;

  const AprMatrixScreen({super.key, required this.apr, this.onBack});

  @override
  State<AprMatrixScreen> createState() => _AprMatrixScreenState();
}

class _AprMatrixScreenState extends State<AprMatrixScreen> {
  static const Map<String, String> _normFrameworkLabels = {
    'ISO_45001': 'ISO 45001',
    'OSHA_1926': 'OSHA 1926',
    'ANSI_B11': 'ANSI B11',
  };

  late final ApiService _api;
  int? _aprId;
  bool _linkingApr = false;
  bool _autosaving = false;
  bool _generatingIa = false;
  Timer? _autosaveTimer;
  String? _lastAutosaveSignature;
  bool _saving = false;
  bool _summaryExpandedMobile = true;
  final Set<int> _generatingEvidenceStepKeys = <int>{};
  String? _atividadeSelecionada;
  String? _atividadeIdSelecionada;
  final Map<String, bool> _optionalNormFrameworks = {
    for (final id in _normFrameworkLabels.keys) id: false,
  };
  int? _normProfileId;
  String _normProfileMode = 'NR_BR';
  String _resolvedNormScope = 'company';
  bool _loadingNormProfile = false;
  bool _savingNormProfile = false;

  String get _atividadeAtual => _atividadeSelecionada ?? widget.apr.atividade;

  // ======================================================
  // IDENTIFICACAO
  // ======================================================
  DateTime? dataElaboracao;

  // ======================================================
  // EVIDENCIA TECNICA
  // ======================================================
  Uint8List? imagemBytes;

  Future<void> selecionarImagem() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.image,
      withData: true,
    );
    if (result != null && result.files.single.bytes != null) {
      setState(() => imagemBytes = result.files.single.bytes);
    }
  }

  Future<void> selecionarEvidenciaPasso(int index) async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.image,
      withData: true,
    );
    if (result != null && result.files.isNotEmpty) {
      setState(() => evidenciasPorPasso[index] = result.files.single);
    }
  }

  void removerEvidenciaPasso(int index) {
    setState(() => evidenciasPorPasso[index] = null);
  }

  String _shortForImage(String value, {int max = 240}) {
    final cleaned = TextNormalizer.normalize(
      value,
    ).replaceAll('\n', ' ').trim();
    if (cleaned.length <= max) return cleaned;
    return '${cleaned.substring(0, max).trim()}...';
  }

  Future<Uint8List> _buildStepEvidenceAiPng({
    required int stepNumber,
    required String title,
    required String hazards,
    required String safeguards,
    required int score,
    required Color riskColor,
  }) async {
    const width = 1280;
    const height = 720;
    final recorder = ui.PictureRecorder();
    final canvas = Canvas(
      recorder,
      Rect.fromLTWH(0, 0, width.toDouble(), height.toDouble()),
    );

    final background = Paint()
      ..shader = ui.Gradient.linear(
        const Offset(0, 0),
        Offset(width.toDouble(), height.toDouble()),
        const [Color(0xFF0B1F3A), Color(0xFF0F172A)],
      );
    canvas.drawRect(
      Rect.fromLTWH(0, 0, width.toDouble(), height.toDouble()),
      background,
    );

    final header = Paint()..color = riskColor.withValues(alpha: 0.24);
    canvas.drawRect(Rect.fromLTWH(0, 0, width.toDouble(), 96), header);

    void drawText(
      String text, {
      required double x,
      required double y,
      required double maxWidth,
      double fontSize = 26,
      FontWeight weight = FontWeight.w500,
      Color color = Colors.white,
      int? maxLines,
    }) {
      final painter = TextPainter(
        text: TextSpan(
          text: text,
          style: TextStyle(
            color: color,
            fontSize: fontSize,
            fontWeight: weight,
            height: 1.25,
          ),
        ),
        textDirection: TextDirection.ltr,
        maxLines: maxLines,
        ellipsis: maxLines == null ? null : '...',
      )..layout(maxWidth: maxWidth);
      painter.paint(canvas, Offset(x, y));
    }

    drawText(
      'Evidencia gerada por IA',
      x: 44,
      y: 26,
      maxWidth: 740,
      fontSize: 28,
      weight: FontWeight.w800,
    );
    drawText(
      'Passo $stepNumber  •  PxS $score',
      x: 980,
      y: 34,
      maxWidth: 250,
      fontSize: 20,
      weight: FontWeight.w700,
      color: riskColor,
    );
    drawText(
      _shortForImage(title, max: 420),
      x: 44,
      y: 132,
      maxWidth: 1188,
      fontSize: 34,
      weight: FontWeight.w700,
      maxLines: 2,
    );
    drawText(
      'Perigos: ${_shortForImage(hazards)}',
      x: 44,
      y: 258,
      maxWidth: 1188,
      fontSize: 22,
      weight: FontWeight.w500,
      color: const Color(0xFFE2E8F0),
      maxLines: 4,
    );
    drawText(
      'Salvaguardas: ${_shortForImage(safeguards)}',
      x: 44,
      y: 430,
      maxWidth: 1188,
      fontSize: 22,
      weight: FontWeight.w500,
      color: const Color(0xFFE2E8F0),
      maxLines: 5,
    );
    drawText(
      'HCS • Matriz APR',
      x: 44,
      y: 672,
      maxWidth: 400,
      fontSize: 16,
      weight: FontWeight.w600,
      color: const Color(0xFF93A9D8),
    );

    final picture = recorder.endRecording();
    final image = await picture.toImage(width, height);
    final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
    if (bytes == null) {
      throw Exception('Falha ao gerar imagem IA');
    }
    return bytes.buffer.asUint8List();
  }

  Future<void> gerarImagemIaPasso(int index) async {
    if (index < 0 || index >= passos.length) return;

    final stepKey = identityHashCode(passos[index]);
    setState(() => _generatingEvidenceStepKeys.add(stepKey));
    try {
      final bytes = await _buildStepEvidenceAiPng(
        stepNumber: index + 1,
        title: passos[index].text.trim().isEmpty
            ? 'Passo ${index + 1}'
            : passos[index].text.trim(),
        hazards: perigosERiscos[index].text.trim(),
        safeguards: salvaguardas[index].text.trim(),
        score: _stepScoreAt(index),
        riskColor: _stepRiskColor(index),
      );

      final filename =
          'ia_passo_${index + 1}_${DateTime.now().millisecondsSinceEpoch}.png';
      setState(() {
        evidenciasPorPasso[index] = PlatformFile(
          name: filename,
          size: bytes.length,
          bytes: bytes,
        );
        if (evidenciasCaption[index].text.trim().isEmpty) {
          evidenciasCaption[index].text =
              'Imagem gerada por IA para o passo ${index + 1}';
        }
      });
      _scheduleAutosave();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Imagem IA gerada para o passo ${index + 1}.')),
      );
    } catch (e) {
      if (!mounted) return;
      _alerta('Falha ao gerar imagem IA do passo ${index + 1}: $e');
    } finally {
      if (mounted) {
        setState(() => _generatingEvidenceStepKeys.remove(stepKey));
      } else {
        _generatingEvidenceStepKeys.remove(stepKey);
      }
    }
  }

  // ======================================================
  // DESCRICAO DA ATIVIDADE
  // ======================================================
  final TextEditingController descricaoAtividadeController =
      TextEditingController();

  // ======================================================
  // PASSO A PASSO (COMPLETO)
  // ======================================================
  final List<TextEditingController> passos = [];
  final List<TextEditingController> perigosERiscos = [];
  final List<TextEditingController> consequencias = [];
  final List<TextEditingController> salvaguardas = [];
  final List<TextEditingController> episPorPasso = [];
  final List<PlatformFile?> evidenciasPorPasso = [];
  final List<TextEditingController> evidenciasCaption = [];

  // ======================================================
  // EPIs GERAIS
  // ======================================================
  static const List<String> _fallbackEpis = <String>[
    'Capacete',
    'Oculos de protecao',
    'Luvas',
    'Botina de seguranca',
    'Protetor auricular',
    'Cinto de seguranca',
  ];
  final Map<String, bool> episGerais = {};
  final TextEditingController novoEpiController = TextEditingController();
  final List<String> episExtras = [];

  // ======================================================
  // FERRAMENTAS
  // ======================================================
  final Map<String, bool> ferramentas = {
    'Furadeira': false,
    'Esmerilhadeira': false,
    'Escada': false,
    'Talha': false,
    'Ferramentas manuais': false,
  };
  final TextEditingController novaFerramentaController =
      TextEditingController();
  final List<String> ferramentasExtras = [];

  // ======================================================
  // ENERGIAS PERIGOSAS (CHECKLIST CANONICO)
  // ======================================================
  final Map<String, bool> dangerousEnergiesChecklist = {
    'hydraulic': false,
    'residual': false,
    'kinetic': false,
    'mechanical': false,
    'electrical': false,
    'gravitational_potential': false,
    'thermal': false,
    'pneumatic': false,
  };

  static const Map<String, String> _energyLabels = {
    'hydraulic': 'Hidraulica',
    'residual': 'Residual',
    'kinetic': 'Cinetica',
    'mechanical': 'Mecanica',
    'electrical': 'Eletrica',
    'gravitational_potential': 'Potencial gravitacional',
    'thermal': 'Termica',
    'pneumatic': 'Pneumatica',
  };
  bool semEnergia = false;

  bool bloqueio = false;
  bool dissipacao = false;
  bool testeEnergiaZero = false;

  // ======================================================
  // MATRIZ DE RISCO
  // ======================================================
  int probabilidade = 1;
  int severidade = 1;

  int get risco => probabilidade * severidade;

  Color get corRisco {
    if (risco <= 4) return Colors.green;
    if (risco <= 9) return Colors.yellow.shade700;
    if (risco <= 16) return Colors.orange;
    return Colors.red;
  }

  String get classificacao {
    if (risco <= 4) return 'BAIXO';
    if (risco <= 9) return 'MEDIO';
    if (risco <= 16) return 'ALTO';
    return 'CRITICO';
  }

  @override
  void initState() {
    super.initState();
    _api = ApiService(baseUrl: resolveBaseUrl());
    _aprId = widget.apr.id;
    debugPrint(
      '[AprMatrixScreen] init aprId=${widget.apr.id} source=${widget.apr.source ?? "unknown"} '
      'atividade="${widget.apr.atividade}" atividadeId=${widget.apr.atividadeId ?? "-"}',
    );
    _atividadeIdSelecionada = widget.apr.atividadeId;
    if (descricaoAtividadeController.text.isEmpty) {
      descricaoAtividadeController.text = _atividadeAtual;
    }
    descricaoAtividadeController.addListener(_scheduleAutosave);
    adicionarPasso();
    _loadCatalogsFromBackend();
    _loadNormProfile();
    _ensureAprLinked();
  }

  @override
  void dispose() {
    _autosaveTimer?.cancel();
    descricaoAtividadeController.removeListener(_scheduleAutosave);
    descricaoAtividadeController.dispose();
    novoEpiController.dispose();
    novaFerramentaController.dispose();
    _disposeStepControllers();
    super.dispose();
  }

  void adicionarPasso() {
    final passoCtrl = TextEditingController()..addListener(_scheduleAutosave);
    final perigoCtrl = TextEditingController()..addListener(_scheduleAutosave);
    final consequenciaCtrl = TextEditingController()
      ..addListener(_scheduleAutosave);
    final salvaguardaCtrl = TextEditingController()
      ..addListener(_scheduleAutosave);
    final epiCtrl = TextEditingController()..addListener(_scheduleAutosave);
    final captionCtrl = TextEditingController()..addListener(_scheduleAutosave);

    passos.add(passoCtrl);
    perigosERiscos.add(perigoCtrl);
    consequencias.add(consequenciaCtrl);
    salvaguardas.add(salvaguardaCtrl);
    episPorPasso.add(epiCtrl);
    evidenciasPorPasso.add(null);
    evidenciasCaption.add(captionCtrl);
    _scheduleAutosave();
  }

  void removerPasso(int index) {
    if (passos.length <= 1) {
      _alerta('A APR precisa ter pelo menos um passo.');
      return;
    }
    passos[index].removeListener(_scheduleAutosave);
    perigosERiscos[index].removeListener(_scheduleAutosave);
    consequencias[index].removeListener(_scheduleAutosave);
    salvaguardas[index].removeListener(_scheduleAutosave);
    episPorPasso[index].removeListener(_scheduleAutosave);
    evidenciasCaption[index].removeListener(_scheduleAutosave);
    passos[index].dispose();
    perigosERiscos[index].dispose();
    consequencias[index].dispose();
    salvaguardas[index].dispose();
    episPorPasso[index].dispose();
    evidenciasCaption[index].dispose();

    passos.removeAt(index);
    perigosERiscos.removeAt(index);
    consequencias.removeAt(index);
    salvaguardas.removeAt(index);
    episPorPasso.removeAt(index);
    evidenciasPorPasso.removeAt(index);
    evidenciasCaption.removeAt(index);
    _scheduleAutosave();
  }

  void _disposeStepControllers() {
    for (final c in passos) {
      c.removeListener(_scheduleAutosave);
      c.dispose();
    }
    for (final c in perigosERiscos) {
      c.removeListener(_scheduleAutosave);
      c.dispose();
    }
    for (final c in consequencias) {
      c.removeListener(_scheduleAutosave);
      c.dispose();
    }
    for (final c in salvaguardas) {
      c.removeListener(_scheduleAutosave);
      c.dispose();
    }
    for (final c in episPorPasso) {
      c.removeListener(_scheduleAutosave);
      c.dispose();
    }
    for (final c in evidenciasCaption) {
      c.removeListener(_scheduleAutosave);
      c.dispose();
    }
    passos.clear();
    perigosERiscos.clear();
    consequencias.clear();
    salvaguardas.clear();
    episPorPasso.clear();
    evidenciasPorPasso.clear();
    evidenciasCaption.clear();
  }

  String _dateForApi(DateTime value) {
    final y = value.year.toString().padLeft(4, '0');
    final m = value.month.toString().padLeft(2, '0');
    final d = value.day.toString().padLeft(2, '0');
    return '$y-$m-$d';
  }

  String _dateForUi(DateTime value) {
    final d = value.day.toString().padLeft(2, '0');
    final m = value.month.toString().padLeft(2, '0');
    final y = value.year.toString().padLeft(4, '0');
    return '$d/$m/$y';
  }

  Future<void> _pickDataElaboracao() async {
    final now = DateTime.now();
    final initial = dataElaboracao ?? now;
    final picked = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(now.year - 5),
      lastDate: DateTime(now.year + 5),
      helpText: 'Selecionar data de elaboracao',
      locale: const Locale('pt', 'BR'),
    );
    if (picked == null) return;
    setState(() {
      dataElaboracao = DateTime(picked.year, picked.month, picked.day);
    });
    _scheduleAutosave();
  }

  Iterable<String> _readCatalogNames(Map<String, dynamic> payload) {
    final items = (payload['items'] as List<dynamic>? ?? <dynamic>[])
        .whereType<Map<String, dynamic>>();
    final loaded = <String>[];
    for (final item in items) {
      final raw = item['name']?.toString() ?? item['epi']?.toString() ?? '';
      final normalized = TextNormalizer.normalize(raw);
      if (normalized.trim().isNotEmpty) {
        loaded.add(normalized.trim());
      }
    }
    return loaded.toSet();
  }

  Future<void> _hydrateSelectionsFromExistingApr() async {
    final aprId = _aprId;
    if (aprId == null) return;

    try {
      final payload = await _api.getAprMvpByExternalId(aprId.toString());
      final controls = (payload['controls'] as List<dynamic>? ?? <dynamic>[])
          .whereType<Map<String, dynamic>>();
      final dateRaw = payload['date']?.toString();
      final parsedDate = dateRaw == null ? null : DateTime.tryParse(dateRaw);

      final episMarcados = <String>{};
      final ferramentasMarcadas = <String>{};
      final episAdicionais = <String>{};
      final ferramentasAdicionais = <String>{};

      for (final control in controls) {
        final name = TextNormalizer.normalize(
          control['name']?.toString() ?? '',
        );
        if (name.isEmpty) continue;
        final type = TextNormalizer.normalize(
          control['type']?.toString() ?? '',
        ).toLowerCase();
        final isEpi = type.contains('epi') || type.contains('ppe');
        final isFerramenta =
            type.contains('ferrament') || type.contains('tool');

        if (isEpi) {
          if (episGerais.containsKey(name)) {
            episMarcados.add(name);
          } else {
            episAdicionais.add(name);
          }
        } else if (isFerramenta) {
          if (ferramentas.containsKey(name)) {
            ferramentasMarcadas.add(name);
          } else {
            ferramentasAdicionais.add(name);
          }
        }
      }

      if (!mounted) return;
      setState(() {
        for (final epi in episMarcados) {
          episGerais[epi] = true;
        }
        for (final ferramenta in ferramentasMarcadas) {
          ferramentas[ferramenta] = true;
        }
        for (final epi in episAdicionais) {
          if (!episExtras.contains(epi)) {
            episExtras.add(epi);
          }
        }
        for (final ferramenta in ferramentasAdicionais) {
          if (!ferramentasExtras.contains(ferramenta)) {
            ferramentasExtras.add(ferramenta);
          }
        }
        if (dataElaboracao == null && parsedDate != null) {
          dataElaboracao = DateTime(
            parsedDate.year,
            parsedDate.month,
            parsedDate.day,
          );
        }
      });
    } catch (_) {
      // noop: hidratacao e best effort para nao bloquear edicao
    }
  }

  Future<void> _loadCatalogsFromBackend() async {
    try {
      final responses = await Future.wait<Map<String, dynamic>>([
        _api.getEpis(limit: 200),
        _api.getFerramentas(limit: 200),
      ]);
      final episLoaded = _readCatalogNames(responses[0]);
      final ferramentasLoaded = _readCatalogNames(responses[1]);

      if (!mounted) return;
      setState(() {
        final currentEpiState = Map<String, bool>.from(episGerais);
        final effectiveEpis = episLoaded.isEmpty ? _fallbackEpis : episLoaded;
        episGerais.clear();
        for (final epi in effectiveEpis) {
          episGerais[epi] = currentEpiState[epi] ?? false;
        }
        for (final ferramenta in ferramentasLoaded) {
          ferramentas.putIfAbsent(ferramenta, () => false);
        }
      });
      await _hydrateSelectionsFromExistingApr();
    } catch (_) {
      if (mounted && episGerais.isEmpty) {
        setState(() {
          for (final epi in _fallbackEpis) {
            episGerais.putIfAbsent(epi, () => false);
          }
        });
      }
    }
  }

  List<String> _selectedOptionalNormIds() {
    return _optionalNormFrameworks.entries
        .where((entry) => entry.value)
        .map((entry) => entry.key)
        .toList(growable: false);
  }

  String _resolvedScopeLabel(String scope) {
    switch (scope) {
      case 'contract':
        return 'contrato';
      case 'unit':
        return 'unidade';
      default:
        return 'empresa';
    }
  }

  void _applyNormProfilePayload(Map<String, dynamic> payload) {
    final optionals = (payload['optionals'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map((item) => item['id']?.toString() ?? '')
        .where((id) => id.isNotEmpty)
        .toSet();
    final profileId = int.tryParse(payload['id']?.toString() ?? '');
    final mode = payload['riskEngineMode']?.toString();
    final resolvedFrom = payload['resolvedFrom']?.toString();

    _normProfileId = profileId;
    _normProfileMode = (mode == null || mode.trim().isEmpty) ? 'NR_BR' : mode;
    if (resolvedFrom != null && resolvedFrom.trim().isNotEmpty) {
      _resolvedNormScope = resolvedFrom;
    }
    for (final frameworkId in _optionalNormFrameworks.keys) {
      _optionalNormFrameworks[frameworkId] = optionals.contains(frameworkId);
    }
  }

  Future<void> _loadNormProfile() async {
    if (_loadingNormProfile) {
      return;
    }
    if (mounted) {
      setState(() => _loadingNormProfile = true);
    } else {
      _loadingNormProfile = true;
    }
    try {
      final payload = await _api.resolveNormProfile();
      if (!mounted) {
        _applyNormProfilePayload(payload);
        return;
      }
      setState(() => _applyNormProfilePayload(payload));
    } catch (e) {
      if (mounted) {
        _alerta('Nao foi possivel carregar Normas Ativas: $e');
      }
    } finally {
      if (mounted) {
        setState(() => _loadingNormProfile = false);
      } else {
        _loadingNormProfile = false;
      }
    }
  }

  Future<void> _toggleNormFramework(String frameworkId) async {
    if (!_optionalNormFrameworks.containsKey(frameworkId)) {
      return;
    }
    if (_loadingNormProfile || _savingNormProfile) {
      return;
    }
    final previous = Map<String, bool>.from(_optionalNormFrameworks);
    setState(() {
      _optionalNormFrameworks[frameworkId] =
          !(_optionalNormFrameworks[frameworkId] ?? false);
      _savingNormProfile = true;
    });

    try {
      if (_normProfileId == null) {
        final resolved = await _api.resolveNormProfile();
        _applyNormProfilePayload(resolved);
      }
      final profileId = _normProfileId;
      if (profileId == null) {
        throw Exception('Perfil normativo nao disponivel');
      }
      final updated = await _api.updateNormProfile(
        profileId: profileId,
        optionalFrameworkIds: _selectedOptionalNormIds(),
      );
      if (mounted) {
        setState(() => _applyNormProfilePayload(updated));
      } else {
        _applyNormProfilePayload(updated);
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          for (final entry in previous.entries) {
            _optionalNormFrameworks[entry.key] = entry.value;
          }
        });
        _alerta('Nao foi possivel salvar Normas Ativas: $e');
      } else {
        for (final entry in previous.entries) {
          _optionalNormFrameworks[entry.key] = entry.value;
        }
      }
    } finally {
      if (mounted) {
        setState(() => _savingNormProfile = false);
      } else {
        _savingNormProfile = false;
      }
    }
  }

  String _buildAutosaveSignature() {
    final buffer = StringBuffer()
      ..write(_aprId?.toString() ?? '')
      ..write('|')
      ..write(descricaoAtividadeController.text.trim())
      ..write('|')
      ..write(_atividadeIdSelecionada ?? '')
      ..write('|')
      ..write(_atividadeAtual);

    for (var i = 0; i < passos.length; i++) {
      buffer
        ..write('|s')
        ..write(i)
        ..write(':')
        ..write(passos[i].text.trim())
        ..write('|h:')
        ..write(perigosERiscos[i].text.trim())
        ..write('|r:')
        ..write(consequencias[i].text.trim())
        ..write('|m:')
        ..write(salvaguardas[i].text.trim())
        ..write('|e:')
        ..write(episPorPasso[i].text.trim());
    }
    return buffer.toString();
  }

  List<Map<String, dynamic>> _toBulkStepsPayload() {
    final items = <Map<String, dynamic>>[];
    for (var i = 0; i < passos.length; i++) {
      final desc = passos[i].text.trim();
      final haz = perigosERiscos[i].text.trim();
      final risk = consequencias[i].text.trim();
      final measures = salvaguardas[i].text.trim();
      final epis = episPorPasso[i].text.trim();

      if (desc.isEmpty &&
          haz.isEmpty &&
          risk.isEmpty &&
          measures.isEmpty &&
          epis.isEmpty) {
        continue;
      }

      items.add({
        'step_order': i + 1,
        'description': desc.isEmpty ? 'Passo ${i + 1}' : desc,
        'hazards': haz.isEmpty ? <String>[] : <String>[haz],
        'risks': risk.isEmpty ? <String>[] : <String>[risk],
        'measures': measures.isEmpty ? <String>[] : <String>[measures],
        'epis': epis.isEmpty ? <String>[] : <String>[epis],
        'regulations': <String>[],
      });
    }
    return items;
  }

  Future<int?> _ensureAprLinked({bool silent = false}) async {
    if (_aprId != null) {
      return _aprId;
    }
    if (_linkingApr) {
      for (var i = 0; i < 20; i++) {
        await Future<void>.delayed(const Duration(milliseconds: 100));
        if (!_linkingApr) {
          return _aprId;
        }
      }
      return _aprId;
    }

    if (mounted) {
      setState(() => _linkingApr = true);
    } else {
      _linkingApr = true;
    }
    try {
      final now = DateTime.now();
      final atividade = _atividadeAtual.trim().isEmpty
          ? 'Atividade'
          : _atividadeAtual.trim();
      final descricao = descricaoAtividadeController.text.trim().isEmpty
          ? atividade
          : descricaoAtividadeController.text.trim();

      final created = await _api.createApr(
        obra: widget.apr.empresa.isEmpty ? 'Obra' : widget.apr.empresa,
        local: widget.apr.empresa.isEmpty ? 'Local' : widget.apr.empresa,
        responsavel: 'A definir',
        data: _dateForApi(dataElaboracao ?? now),
        atividadeId:
            (_atividadeIdSelecionada == null ||
                _atividadeIdSelecionada!.trim().isEmpty)
            ? 'manual'
            : _atividadeIdSelecionada!.trim(),
        atividadeNome: atividade,
        titulo: atividade,
        risco: classificacao,
        descricao: descricao,
      );

      final id = int.tryParse(created['id']?.toString() ?? '');
      if (id == null) {
        if (!silent && mounted) {
          _alerta('Falha ao criar APR automaticamente');
        }
        return null;
      }
      if (mounted) {
        setState(() => _aprId = id);
      } else {
        _aprId = id;
      }
      debugPrint(
        '[AprMatrixScreen] apr linked automatically -> legacyAprId=$id',
      );
      _scheduleAutosave();
      return id;
    } catch (e) {
      if (!silent && mounted) {
        _alerta('Falha ao vincular APR automaticamente: $e');
      }
      return null;
    } finally {
      if (mounted) {
        setState(() => _linkingApr = false);
      } else {
        _linkingApr = false;
      }
    }
  }

  void _scheduleAutosave() {
    _recalcularRiscoAutomatico();
    _autosaveTimer?.cancel();
    _autosaveTimer = Timer(const Duration(milliseconds: 900), () {
      _autoSaveDraft();
    });
  }

  Future<void> _autoSaveDraft() async {
    if (_saving || _autosaving) {
      return;
    }

    final aprId = await _ensureAprLinked(silent: true);
    if (aprId == null) {
      return;
    }

    final signature = _buildAutosaveSignature();
    if (_lastAutosaveSignature == signature) {
      return;
    }

    _autosaving = true;
    try {
      final payload = <String, dynamic>{
        'titulo': _atividadeAtual.trim().isEmpty
            ? 'APR'
            : _atividadeAtual.trim(),
        'descricao': descricaoAtividadeController.text.trim(),
        'activity_name': _atividadeAtual.trim().isEmpty
            ? 'Atividade'
            : _atividadeAtual.trim(),
        'dangerous_energies_checklist': Map<String, bool>.from(
          dangerousEnergiesChecklist,
        ),
      };
      if (_atividadeIdSelecionada != null &&
          _atividadeIdSelecionada!.trim().isNotEmpty) {
        payload['activity_id'] = _atividadeIdSelecionada!.trim();
      }
      if (dataElaboracao != null) {
        payload['date'] = _dateForApi(dataElaboracao!);
      }

      await _api.updateApr(aprId: aprId, payload: payload);
      await _api.replaceAprSteps(aprId: aprId, items: _toBulkStepsPayload());
      _lastAutosaveSignature = signature;
    } catch (_) {
      // Silent autosave: user can continue editing.
    } finally {
      _autosaving = false;
    }
  }

  String _joinList(dynamic value) {
    if (value == null) return '';
    if (value is List) {
      return value
          .map((e) => e.toString().trim())
          .where((e) => e.isNotEmpty)
          .join('; ');
    }
    return value.toString();
  }

  static const List<String> _termosSeveridade5 = [
    'morte',
    'fatal',
    'amputa\u00e7\u00e3o',
  ];
  static const List<String> _termosSeveridade4 = [
    'fratura',
    'queimadura',
    'choque',
  ];
  static const List<String> _termosSeveridade3 = ['afastamento'];
  static const List<String> _termosSeveridade2 = [
    'corte',
    'escoria\u00e7\u00e3o',
    'contus\u00e3o',
  ];
  static const List<String> _termosConsequenciaGrave = [
    'morte',
    'fatal',
    'amputa\u00e7\u00e3o',
    'choque',
  ];

  String _textoConsequenciasNormalizado() {
    final texto = consequencias.map((c) => c.text).join(' ');
    return TextNormalizer.normalize(texto).toLowerCase();
  }

  bool _containsAny(String texto, List<String> termos) {
    for (final termo in termos) {
      if (texto.contains(termo)) return true;
    }
    return false;
  }

  List<String> _selectedEnergyLabels() {
    final labels = <String>[];
    for (final entry in dangerousEnergiesChecklist.entries) {
      if (entry.value) {
        labels.add(_energyLabels[entry.key] ?? entry.key);
      }
    }
    if (labels.isEmpty && semEnergia) {
      labels.add('Sem uso de energia');
    }
    return labels;
  }

  bool _isElectricalSelected() =>
      dangerousEnergiesChecklist['electrical'] == true;

  // ======================================================
  // ======================================================
  // OPENAI - GERACAO AUTOMATICA
  // ======================================================
  void gerarComIA() async {
    if (_generatingIa) {
      return;
    }
    if (_savingNormProfile) {
      _alerta(
        'Aguarde o salvamento das Normas Ativas para gerar os passos com IA.',
      );
      return;
    }

    try {
      setState(() => _generatingIa = true);

      final aprId = await _ensureAprLinked();
      if (aprId == null) {
        return;
      }

      final atividade = descricaoAtividadeController.text.trim().isNotEmpty
          ? descricaoAtividadeController.text.trim()
          : _atividadeAtual;
      final resultado = await _api.gerarPassosIA(
        aprId: aprId,
        atividade: atividade,
        descricao: descricaoAtividadeController.text.trim(),
        ferramentas: _ferramentasSelecionadas(),
        energias: _selectedEnergyLabels(),
        dangerousEnergiesChecklist: Map<String, bool>.from(
          dangerousEnergiesChecklist,
        ),
        imageBytes: imagemBytes,
      );

      final validos = resultado.where(_hasUsableAiData).toList(growable: false);
      if (validos.isEmpty) {
        _alerta(
          'A IA nao retornou passos validos. Tente detalhar melhor a descricao da atividade ou anexar uma evidencia tecnica.',
        );
        return;
      }

      setState(() {
        _disposeStepControllers();

        for (final p in validos) {
          passos.add(
            TextEditingController(text: (p['passo'] ?? '').toString())
              ..addListener(_scheduleAutosave),
          );
          perigosERiscos.add(
            TextEditingController(text: (p['perigo'] ?? '').toString())
              ..addListener(_scheduleAutosave),
          );
          consequencias.add(
            TextEditingController(text: (p['consequencia'] ?? '').toString())
              ..addListener(_scheduleAutosave),
          );
          salvaguardas.add(
            TextEditingController(text: (p['salvaguarda'] ?? '').toString())
              ..addListener(_scheduleAutosave),
          );
          episPorPasso.add(
            TextEditingController(text: (p['epi'] ?? '').toString())
              ..addListener(_scheduleAutosave),
          );
          evidenciasPorPasso.add(null);
          evidenciasCaption.add(
            TextEditingController()..addListener(_scheduleAutosave),
          );
        }
      });

      sugerirSeveridadePorConsequencia();
      _scheduleAutosave();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('IA gerou ${validos.length} passo(s).')),
        );
      }
    } catch (e) {
      _alerta('Erro ao gerar com IA: $e');
    } finally {
      if (mounted) {
        setState(() => _generatingIa = false);
      }
    }
  }

  bool _hasUsableAiData(Map<String, dynamic> step) {
    final fields = [
      (step['passo'] ?? '').toString().trim(),
      (step['perigo'] ?? '').toString().trim(),
      (step['consequencia'] ?? '').toString().trim(),
      (step['salvaguarda'] ?? '').toString().trim(),
      (step['epi'] ?? '').toString().trim(),
    ];
    return fields.any((f) => f.isNotEmpty);
  }

  void _reorderStep(int oldIndex, int newIndex) {
    if (oldIndex < 0 ||
        newIndex < 0 ||
        oldIndex >= passos.length ||
        newIndex > passos.length) {
      return;
    }
    if (newIndex > oldIndex) {
      newIndex -= 1;
    }
    if (oldIndex == newIndex) {
      return;
    }

    final stepCtrl = passos.removeAt(oldIndex);
    passos.insert(newIndex, stepCtrl);

    final hazardCtrl = perigosERiscos.removeAt(oldIndex);
    perigosERiscos.insert(newIndex, hazardCtrl);

    final consequenceCtrl = consequencias.removeAt(oldIndex);
    consequencias.insert(newIndex, consequenceCtrl);

    final safeguardCtrl = salvaguardas.removeAt(oldIndex);
    salvaguardas.insert(newIndex, safeguardCtrl);

    final epiCtrl = episPorPasso.removeAt(oldIndex);
    episPorPasso.insert(newIndex, epiCtrl);

    final evidence = evidenciasPorPasso.removeAt(oldIndex);
    evidenciasPorPasso.insert(newIndex, evidence);

    final captionCtrl = evidenciasCaption.removeAt(oldIndex);
    evidenciasCaption.insert(newIndex, captionCtrl);

    _scheduleAutosave();
  }

  // ======================================================
  Future<void> aplicarModelo() async {
    final aprId = await _ensureAprLinked();
    if (aprId == null) {
      return;
    }
    if (!mounted) {
      return;
    }

    final selected = await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const AprTemplatesScreen()),
    );
    if (!mounted) {
      return;
    }

    if (selected == null || selected is! Map) {
      return;
    }

    final activityId = selected['id']?.toString();
    final activityName = selected['name']?.toString();

    if (activityId == null || activityId.isEmpty) {
      _alerta('Modelo invalido.');
      return;
    }

    setState(() {
      _atividadeIdSelecionada = activityId;
      if (activityName != null && activityName.isNotEmpty) {
        _atividadeSelecionada = activityName;
        descricaoAtividadeController.text = activityName;
      }
    });

    try {
      final data = await _api.getActivitySuggestions(activityId);
      final steps = (data['steps'] as List<dynamic>?) ?? [];
      if (steps.isEmpty) {
        _alerta('Modelo sem passos cadastrados.');
        return;
      }

      setState(() {
        _disposeStepControllers();

        for (final step in steps) {
          final map = step as Map<String, dynamic>;
          passos.add(
            TextEditingController(text: (map['description'] ?? '').toString())
              ..addListener(_scheduleAutosave),
          );
          perigosERiscos.add(
            TextEditingController(text: _joinList(map['hazards']))
              ..addListener(_scheduleAutosave),
          );
          consequencias.add(
            TextEditingController(text: _joinList(map['risks']))
              ..addListener(_scheduleAutosave),
          );
          salvaguardas.add(
            TextEditingController(text: _joinList(map['measures']))
              ..addListener(_scheduleAutosave),
          );
          episPorPasso.add(
            TextEditingController(text: _joinList(map['epis']))
              ..addListener(_scheduleAutosave),
          );
          evidenciasPorPasso.add(null);
          evidenciasCaption.add(
            TextEditingController()..addListener(_scheduleAutosave),
          );
        }
      });

      final payload = <String, dynamic>{'activity_id': activityId};
      if (activityName != null && activityName.isNotEmpty) {
        payload['activity_name'] = activityName;
        payload['titulo'] = activityName;
      }
      await _api.updateApr(aprId: aprId, payload: payload);

      sugerirSeveridadePorConsequencia();
      _scheduleAutosave();
    } catch (e) {
      _alerta('Erro ao aplicar modelo: $e');
    }
  }

  int _severityFromConsequences() {
    final texto = _textoConsequenciasNormalizado();
    if (_containsAny(texto, _termosSeveridade5)) return 5;
    if (_containsAny(texto, _termosSeveridade4)) return 4;
    if (_containsAny(texto, _termosSeveridade3)) return 3;
    if (_containsAny(texto, _termosSeveridade2)) return 2;
    return 1;
  }

  int _probabilityFromScenario() {
    final perigosTexto = perigosERiscos.map((e) => e.text).join(' ');
    final perigosNorm = TextNormalizer.normalize(perigosTexto).toLowerCase();
    final consequenciasNorm = _textoConsequenciasNormalizado();
    final salvaguardasCompletas = salvaguardas.every(
      (s) => s.text.trim().isNotEmpty,
    );
    final termosCriticos = <String>[
      'altura',
      'confin',
      'eletric',
      'explos',
      'queda',
      'amput',
    ];

    var p = 1;
    if (passos.length >= 3) p += 1;
    if (_containsAny(perigosNorm, termosCriticos)) p = p < 4 ? 4 : p;
    if (_containsAny(consequenciasNorm, _termosConsequenciaGrave)) {
      p = p < 3 ? 3 : p;
    }
    if (!salvaguardasCompletas) p += 1;
    if (_ferramentasSelecionadas().isEmpty) p += 1;

    if (salvaguardasCompletas && _ferramentasSelecionadas().isNotEmpty) {
      p -= 1;
    }
    if (p < 1) return 1;
    if (p > 5) return 5;
    return p;
  }

  void _recalcularRiscoAutomatico() {
    final novaSeveridade = _severityFromConsequences();
    final novaProbabilidade = _probabilityFromScenario();

    if (novaSeveridade == severidade && novaProbabilidade == probabilidade) {
      return;
    }

    if (!mounted) return;
    setState(() {
      severidade = novaSeveridade;
      probabilidade = novaProbabilidade;
    });
  }

  // Mantido por compatibilidade com chamadas existentes na tela.
  void sugerirSeveridadePorConsequencia() => _recalcularRiscoAutomatico();

  // ======================================================
  // CHECKLIST TECNICO BLOQUEANTE
  // ======================================================
  String? validarChecklistTecnico() {
    if (_isElectricalSelected() &&
        (!bloqueio || !dissipacao || !testeEnergiaZero)) {
      return 'Atividade com energia eletrica exige bloqueio, dissipacao e teste de energia zero.';
    }

    final algumaEnergiaSelecionada =
        semEnergia || dangerousEnergiesChecklist.values.any((value) => value);
    if (!algumaEnergiaSelecionada) {
      return 'Selecione ao menos uma opcao em Energias Perigosas.';
    }

    final textoConsequencias = _textoConsequenciasNormalizado();

    if (_containsAny(textoConsequencias, _termosConsequenciaGrave) &&
        severidade < 4) {
      return 'Consequencia grave com severidade incompativel.';
    }

    if (classificacao == 'CRITICO' &&
        salvaguardas.any((s) => s.text.trim().isEmpty)) {
      return 'Risco critico exige salvaguardas descritas em todos os passos.';
    }

    if (episPorPasso.any((e) => e.text.trim().isEmpty)) {
      return 'Todos os passos devem possuir EPIs definidos.';
    }

    if (_ferramentasSelecionadas().isEmpty) {
      return 'Selecione ao menos uma ferramenta utilizada.';
    }

    if (_episSelecionados().isEmpty) {
      return 'Selecione ao menos um EPI geral (catalogo do backend) ou adicione manualmente.';
    }

    if (evidenciasPorPasso.any((e) => e == null)) {
      return 'Anexe evidencias de imagem para todos os passos antes da aprovacao.';
    }

    return null;
  }

  List<String> _ferramentasSelecionadas() {
    final selecionadas = <String>[
      ...ferramentas.entries.where((e) => e.value).map((e) => e.key),
      ...ferramentasExtras,
    ];
    return selecionadas;
  }

  List<String> _episSelecionados() {
    final selecionados = <String>[
      ...episGerais.entries.where((e) => e.value).map((e) => e.key),
      ...episExtras,
    ];
    return selecionados;
  }

  List<Map<String, dynamic>> _buildMvpHazardsPayload() {
    final hazards = <Map<String, dynamic>>[];
    for (var i = 0; i < perigosERiscos.length; i++) {
      final nome = TextNormalizer.normalize(perigosERiscos[i].text.trim());
      if (nome.isEmpty) continue;
      hazards.add({'name': nome, 'source': 'flutter_matrix', 'step': i + 1});
    }
    return hazards;
  }

  List<Map<String, dynamic>> _buildMvpControlsPayload() {
    final controls = <Map<String, dynamic>>[];
    for (var i = 0; i < salvaguardas.length; i++) {
      final medida = TextNormalizer.normalize(salvaguardas[i].text.trim());
      if (medida.isEmpty) continue;
      controls.add({
        'type': 'procedimento',
        'name': medida,
        'source': 'flutter_matrix',
        'step': i + 1,
      });
    }
    for (final epi in _episSelecionados()) {
      controls.add({'type': 'epi', 'name': epi, 'source': 'flutter_matrix'});
    }
    for (final tool in _ferramentasSelecionadas()) {
      controls.add({
        'type': 'ferramenta',
        'name': tool,
        'source': 'flutter_matrix',
      });
    }
    return controls;
  }

  // ======================================================
  // SALVAR APR (BLOQUEADO)
  // ======================================================
  Future<void> salvarAPR() async {
    if (dataElaboracao == null) {
      _alerta('Informe a data de elaboracao.');
      return;
    }
    if (descricaoAtividadeController.text.isEmpty) {
      _alerta('Descreva a atividade.');
      return;
    }
    if (passos.any((p) => p.text.isEmpty)) {
      _alerta('Todos os passos devem ser preenchidos.');
      return;
    }
    if (perigosERiscos.any((p) => p.text.trim().isEmpty)) {
      _alerta('Todos os passos devem ter pelo menos 1 perigo.');
      return;
    }
    if (salvaguardas.any((s) => s.text.trim().isEmpty)) {
      _alerta('Todos os passos devem ter pelo menos 1 medida.');
      return;
    }

    final erroChecklist = validarChecklistTecnico();
    if (erroChecklist != null) {
      _alerta(erroChecklist);
      return;
    }

    final aprId = await _ensureAprLinked();
    if (aprId == null) {
      return;
    }

    setState(() => _saving = true);
    String? evidenceError;
    try {
      await _api.updateApr(
        aprId: aprId,
        payload: {
          'dangerous_energies_checklist': Map<String, bool>.from(
            dangerousEnergiesChecklist,
          ),
        },
      );
    } catch (e) {
      _alerta('Erro ao salvar checklist de energias: $e');
      setState(() => _saving = false);
      return;
    }

    try {
      for (var i = 0; i < passos.length; i++) {
        final passoResp = await _api.addPasso(
          aprId: aprId,
          descricao: passos[i].text,
          perigos: perigosERiscos[i].text,
          riscos: consequencias[i].text,
          medidasControle: salvaguardas[i].text,
          epis: episPorPasso[i].text,
          normas: '',
        );
        final passoId = passoResp['id'] as int?;
        final evidencia = evidenciasPorPasso[i];
        if (passoId != null && evidencia != null) {
          try {
            await _api.uploadEvidence(
              aprId: aprId,
              passoId: passoId,
              filename: evidencia.name,
              filePath: evidencia.path,
              bytes: evidencia.bytes,
              caption: evidenciasCaption[i].text,
            );
          } catch (e) {
            evidenceError ??= 'Falha ao enviar evidencia do passo ${i + 1}: $e';
          }
        }
      }
    } catch (e) {
      _alerta('Erro ao salvar itens no backend: $e');
      setState(() => _saving = false);
      return;
    }

    try {
      await _api.updateAprMvp(
        aprId: aprId.toString(),
        title: _atividadeAtual.trim().isEmpty ? 'APR' : _atividadeAtual.trim(),
        activity: descricaoAtividadeController.text.trim(),
        hazards: _buildMvpHazardsPayload(),
        controls: _buildMvpControlsPayload(),
      );
    } catch (e) {
      _alerta('Falha ao sincronizar perigos/controles para aprovacao: $e');
      setState(() => _saving = false);
      return;
    }

    try {
      await _api.updateAprStatus(aprId: aprId, status: 'submitted');
    } catch (_) {
      // compat: segue para aprovacao mesmo se status legacy nao atualizar
    }

    setState(() => _saving = false);
    if (!mounted) {
      return;
    }

    if (evidenceError != null) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(evidenceError)));
    }

    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => AprApprovalScreen(
          aprId: aprId,
          atividade: _atividadeAtual.trim().isEmpty
              ? 'APR'
              : _atividadeAtual.trim(),
          probabilidade: probabilidade,
          severidade: severidade,
          classificacao: classificacao,
        ),
      ),
    );
  }

  void _alerta(String msg) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Atencao'),
        content: Text(msg),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('OK'),
          ),
        ],
      ),
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

  // ======================================================
  // UI
  // ======================================================
  @override
  Widget build(BuildContext context) => _buildModernLayout(context);

  Future<void> _openBiblioteca() async {
    await showModalBottomSheet<void>(
      context: context,
      builder: (ctx) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                leading: const Icon(Icons.shield_outlined),
                title: const Text('Biblioteca de EPIs'),
                onTap: () {
                  Navigator.pop(ctx);
                  Navigator.pushNamed(context, '/epis');
                },
              ),
              ListTile(
                leading: const Icon(Icons.report_outlined),
                title: const Text('Biblioteca de Perigos'),
                onTap: () {
                  Navigator.pop(ctx);
                  Navigator.pushNamed(context, '/perigos');
                },
              ),
            ],
          ),
        );
      },
    );
  }

  Future<void> _saveDraftNow() async {
    await _autoSaveDraft();
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text('Rascunho salvo.')));
  }

  int _stepSeverityFromText(String consequencia) {
    final text = TextNormalizer.normalize(consequencia).toLowerCase();
    if (_containsAny(text, _termosSeveridade5)) return 5;
    if (_containsAny(text, _termosSeveridade4)) return 4;
    if (_containsAny(text, _termosSeveridade3)) return 3;
    if (_containsAny(text, _termosSeveridade2)) return 2;
    return 1;
  }

  int _stepProbabilityFromText(String perigo, String salvaguarda, String epi) {
    final hazard = TextNormalizer.normalize(perigo).toLowerCase();
    var p = 1;
    final critical = <String>[
      'altura',
      'confin',
      'eletric',
      'explos',
      'queda',
      'amput',
    ];
    if (_containsAny(hazard, critical)) p = 4;
    if (salvaguarda.trim().isEmpty) p += 1;
    if (epi.trim().isEmpty) p += 1;
    if (salvaguarda.trim().isNotEmpty && epi.trim().isNotEmpty) p -= 1;
    return p.clamp(1, 5);
  }

  int _stepScoreAt(int index) {
    final s = _stepSeverityFromText(consequencias[index].text);
    final p = _stepProbabilityFromText(
      perigosERiscos[index].text,
      salvaguardas[index].text,
      episPorPasso[index].text,
    );
    return p * s;
  }

  Color _stepRiskColor(int index) {
    final score = _stepScoreAt(index);
    if (score <= 5) return const Color(0xFF16A34A);
    if (score <= 12) return const Color(0xFFD97706);
    return const Color(0xFFDC2626);
  }

  String _stepRiskLevel(int index) {
    final score = _stepScoreAt(index);
    if (score <= 5) return 'Baixo';
    if (score <= 12) return 'Medio';
    return 'Alto';
  }

  bool _stepValid(int index) {
    return passos[index].text.trim().isNotEmpty &&
        perigosERiscos[index].text.trim().isNotEmpty &&
        salvaguardas[index].text.trim().isNotEmpty;
  }

  Map<String, int> _riskBuckets() {
    var low = 0;
    var medium = 0;
    var high = 0;
    for (var i = 0; i < passos.length; i++) {
      if (!_stepValid(i)) continue;
      final score = _stepScoreAt(i);
      if (score <= 5) {
        low += 1;
      } else if (score <= 12) {
        medium += 1;
      } else {
        high += 1;
      }
    }
    return {'low': low, 'medium': medium, 'high': high};
  }

  List<String> _blockingIssues() {
    final issues = <String>[];
    if (dataElaboracao == null) issues.add('Selecione a data de elaboracao.');
    if (descricaoAtividadeController.text.trim().isEmpty) {
      issues.add('Preencha a descricao da atividade.');
    }
    if (passos.isEmpty) {
      issues.add('Adicione ao menos 1 passo.');
    }
    for (var i = 0; i < passos.length; i++) {
      if (!_stepValid(i)) {
        issues.add('Passo ${i + 1} incompleto.');
      }
    }
    final checklistError = validarChecklistTecnico();
    if (checklistError != null) issues.add(checklistError);
    return issues.toSet().toList(growable: false);
  }

  Future<void> _openStepEditor({int? index}) async {
    final isEdit = index != null;
    final stepCtrl = TextEditingController(
      text: isEdit ? passos[index].text : '',
    );
    final hazardCtrl = TextEditingController(
      text: isEdit ? perigosERiscos[index].text : '',
    );
    final consequenceCtrl = TextEditingController(
      text: isEdit ? consequencias[index].text : '',
    );
    final safeguardCtrl = TextEditingController(
      text: isEdit ? salvaguardas[index].text : '',
    );
    final epiCtrl = TextEditingController(
      text: isEdit ? episPorPasso[index].text : '',
    );

    final saved = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (sheetContext) {
        return Padding(
          padding: EdgeInsets.fromLTRB(
            16,
            8,
            16,
            16 + MediaQuery.of(sheetContext).viewInsets.bottom,
          ),
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  isEdit
                      ? 'Editar passo ${index + 1}'
                      : 'Adicionar passo manual',
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF0B3C5D),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: stepCtrl,
                  decoration: _fieldDecoration('Descricao do passo'),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: hazardCtrl,
                  decoration: _fieldDecoration('Perigos'),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: consequenceCtrl,
                  decoration: _fieldDecoration('Consequencias'),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: safeguardCtrl,
                  decoration: _fieldDecoration('Salvaguardas'),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: epiCtrl,
                  decoration: _fieldDecoration('EPIs do passo'),
                ),
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    TextButton(
                      onPressed: () => Navigator.pop(sheetContext, false),
                      child: const Text('Cancelar'),
                    ),
                    const SizedBox(width: 8),
                    FilledButton(
                      onPressed: () {
                        if (stepCtrl.text.trim().isEmpty ||
                            hazardCtrl.text.trim().isEmpty ||
                            safeguardCtrl.text.trim().isEmpty) {
                          ScaffoldMessenger.of(sheetContext).showSnackBar(
                            const SnackBar(
                              content: Text(
                                'Descricao, perigo e salvaguardas sao obrigatorios.',
                              ),
                            ),
                          );
                          return;
                        }
                        if (isEdit) {
                          passos[index].text = stepCtrl.text.trim();
                          perigosERiscos[index].text = hazardCtrl.text.trim();
                          consequencias[index].text = consequenceCtrl.text
                              .trim();
                          salvaguardas[index].text = safeguardCtrl.text.trim();
                          episPorPasso[index].text = epiCtrl.text.trim();
                        } else {
                          adicionarPasso();
                          final newIndex = passos.length - 1;
                          passos[newIndex].text = stepCtrl.text.trim();
                          perigosERiscos[newIndex].text = hazardCtrl.text
                              .trim();
                          consequencias[newIndex].text = consequenceCtrl.text
                              .trim();
                          salvaguardas[newIndex].text = safeguardCtrl.text
                              .trim();
                          episPorPasso[newIndex].text = epiCtrl.text.trim();
                        }
                        _scheduleAutosave();
                        Navigator.pop(sheetContext, true);
                      },
                      child: const Text('Salvar passo'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );

    stepCtrl.dispose();
    hazardCtrl.dispose();
    consequenceCtrl.dispose();
    safeguardCtrl.dispose();
    epiCtrl.dispose();

    if (saved == true && mounted) {
      setState(() {});
    }
  }

  List<String> _appliedControls() {
    return {
      ..._ferramentasSelecionadas(),
      ..._episSelecionados(),
      ...salvaguardas
          .map((s) => TextNormalizer.normalize(s.text))
          .where((s) => s.trim().isNotEmpty),
    }.toList(growable: false);
  }

  String _stepNormsAt(int index) {
    final raw = [
      passos[index].text,
      perigosERiscos[index].text,
      consequencias[index].text,
      salvaguardas[index].text,
      episPorPasso[index].text,
    ].join(' ');

    final pattern = RegExp(
      r'\bNR\s*[-]?\s*\d+[A-Za-z]?\b',
      caseSensitive: false,
    );
    final unique = <String>{};

    for (final match in pattern.allMatches(raw)) {
      final token = match.group(0);
      if (token == null) continue;
      final normalized = token.toUpperCase().replaceAll(RegExp(r'\s+'), '');
      if (normalized.isEmpty) continue;
      final pretty = normalized.startsWith('NR-')
          ? normalized
          : normalized.replaceFirst('NR', 'NR-');
      unique.add(pretty);
    }

    if (unique.isEmpty) {
      return '';
    }
    final items = unique.toList()..sort();
    return items.join('; ');
  }

  List<AprMatrixStepViewData> _buildStepViewData() {
    return List.generate(passos.length, (i) {
      final title = passos[i].text.trim();
      return AprMatrixStepViewData(
        keyId: identityHashCode(passos[i]),
        index: i,
        title: title.isEmpty ? 'Passo ${i + 1}' : title,
        hazards: perigosERiscos[i].text.trim(),
        consequences: consequencias[i].text.trim(),
        safeguards: salvaguardas[i].text.trim(),
        epis: episPorPasso[i].text.trim(),
        norms: _stepNormsAt(i),
        evidenceName: evidenciasPorPasso[i]?.name,
        evidencePreviewBytes: evidenciasPorPasso[i]?.bytes,
        hasEvidence: evidenciasPorPasso[i] != null,
        riskScore: _stepScoreAt(i),
        riskLevel: _stepRiskLevel(i),
        riskColor: _stepRiskColor(i),
        generatingEvidence: _generatingEvidenceStepKeys.contains(
          identityHashCode(passos[i]),
        ),
      );
    });
  }

  Widget _buildModernLayout(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    final isDesktop = width >= 1080;
    final aprIdLabel =
        _aprId?.toString() ?? (_linkingApr ? 'vinculando...' : '-');
    final blocking = _blockingIssues();
    final canAdvance = blocking.isEmpty && !_saving;
    final buckets = _riskBuckets();
    final validSteps =
        (buckets['low'] ?? 0) +
        (buckets['medium'] ?? 0) +
        (buckets['high'] ?? 0);
    final stepScores = List<int>.generate(passos.length, _stepScoreAt);
    final stepScoreTotal = stepScores.fold<int>(0, (sum, score) => sum + score);
    final stepScoreMax = stepScores.fold<int>(
      0,
      (maxValue, score) => score > maxValue ? score : maxValue,
    );
    final stepViews = _buildStepViewData();
    final elaborationDateLabel = dataElaboracao == null
        ? 'Nao informada'
        : _dateForUi(dataElaboracao!);

    final fixedSummaryDate = Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFDCE3EE)),
      ),
      child: Row(
        children: [
          const Icon(
            Icons.calendar_month_outlined,
            size: 16,
            color: Color(0xFF475569),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'Data de elaboracao: $elaborationDateLabel',
              style: const TextStyle(
                fontSize: 12.5,
                fontWeight: FontWeight.w700,
                color: Color(0xFF334155),
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );

    final summaryPanel = AprMatrixSummaryPanel(
      elaborationDateLabel: elaborationDateLabel,
      validSteps: validSteps,
      riskValue: risco,
      stepScoreTotal: stepScoreTotal,
      stepScoreMax: stepScoreMax,
      classification: classificacao,
      riskColor: corRisco,
      buckets: buckets,
      appliedControls: _appliedControls(),
      blockingIssues: blocking,
      autosaving: _autosaving,
      saving: _saving,
      canAdvance: canAdvance,
      onSave: _saveDraftNow,
      onAdvance: salvarAPR,
    );

    final editorPanel = AprMatrixEditorPanel(
      descricaoController: descricaoAtividadeController,
      onGenerateIa: gerarComIA,
      generatingIa: _generatingIa,
      onApplyModel: aplicarModelo,
      onSelectEvidence: selecionarImagem,
      selectedEvidenceBytes: imagemBytes,
      onAddStep: () {
        _openStepEditor();
      },
      steps: stepViews,
      onEditStep: (i) {
        _openStepEditor(index: i);
      },
      ferramentas: ferramentas,
      episGerais: episGerais,
      onToggleFerramenta: (tool) => setState(() {
        ferramentas[tool] = !(ferramentas[tool] ?? false);
        _scheduleAutosave();
      }),
      onToggleEpi: (epi) => setState(() {
        episGerais[epi] = !(episGerais[epi] ?? false);
        _scheduleAutosave();
      }),
      onDuplicateStep: (i) => setState(() {
        adicionarPasso();
        final n = passos.length - 1;
        passos[n].text = passos[i].text;
        perigosERiscos[n].text = perigosERiscos[i].text;
        consequencias[n].text = consequencias[i].text;
        salvaguardas[n].text = salvaguardas[i].text;
        episPorPasso[n].text = episPorPasso[i].text;
        evidenciasCaption[n].text = evidenciasCaption[i].text;
        _scheduleAutosave();
      }),
      onRemoveStep: (i) => setState(() => removerPasso(i)),
      onSelectStepEvidence: (i) => selecionarEvidenciaPasso(i),
      onGenerateStepEvidenceIa: gerarImagemIaPasso,
      onReorderSteps: (oldIndex, newIndex) =>
          setState(() => _reorderStep(oldIndex, newIndex)),
      optionalNormFrameworks: _optionalNormFrameworks,
      loadingNormProfile: _loadingNormProfile,
      savingNormProfile: _savingNormProfile,
      riskEngineMode: _normProfileMode,
      resolvedNormScope: _resolvedScopeLabel(_resolvedNormScope),
      onToggleNormFramework: (frameworkId) {
        _toggleNormFramework(frameworkId);
      },
    );

    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        leading: AppBackButton(onFallback: widget.onBack),
        backgroundColor: Colors.white,
        surfaceTintColor: Colors.white,
        elevation: 0,
        titleSpacing: 0,
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'APR - Matriz de Risco',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w800,
                color: Color(0xFF0B3C5D),
              ),
            ),
            SizedBox(height: 2),
            Text(
              'Etapa 2 de 5',
              style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: _openBiblioteca,
            child: const Text('Biblioteca'),
          ),
          TextButton(
            onPressed: () => _alerta(
              'Ajuda rapida: complete passos, perigos, salvaguardas e evidencias antes de avancar.',
            ),
            child: const Text('Ajuda'),
          ),
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: FilledButton(
              onPressed: (_saving || _autosaving) ? null : _saveDraftNow,
              child: Text(_autosaving ? 'Salvando...' : 'Salvar'),
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 10, 16, 16),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1380),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const AprMatrixStepperHeader(activeStep: 1),
                  const SizedBox(height: 10),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF8FAFC),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: const Color(0xFFDCE3EE)),
                    ),
                    child: Wrap(
                      spacing: 12,
                      runSpacing: 8,
                      children: [
                        OutlinedButton.icon(
                          onPressed: _pickDataElaboracao,
                          icon: const Icon(Icons.calendar_month_outlined),
                          label: Text(
                            dataElaboracao == null
                                ? 'Selecionar data'
                                : 'Data: ${_dateForUi(dataElaboracao!)}',
                          ),
                        ),
                        Text(
                          'Empresa: ${widget.apr.empresa}',
                          style: const TextStyle(fontSize: 12.5),
                        ),
                        Text(
                          'Atividade: $_atividadeAtual',
                          style: const TextStyle(fontSize: 12.5),
                        ),
                        Text(
                          'APR ID: $aprIdLabel',
                          style: const TextStyle(fontSize: 12.5),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                  Expanded(
                    child: isDesktop
                        ? Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(
                                flex: 8,
                                child: SingleChildScrollView(
                                  child: editorPanel,
                                ),
                              ),
                              const SizedBox(width: 16),
                              SizedBox(
                                width: 420,
                                child: Column(
                                  crossAxisAlignment:
                                      CrossAxisAlignment.stretch,
                                  children: [
                                    fixedSummaryDate,
                                    const SizedBox(height: 8),
                                    Expanded(
                                      child: SingleChildScrollView(
                                        child: summaryPanel,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          )
                        : SingleChildScrollView(
                            child: Column(
                              children: [
                                editorPanel,
                                const SizedBox(height: 12),
                                Card(
                                  margin: EdgeInsets.zero,
                                  elevation: 0,
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(14),
                                    side: const BorderSide(
                                      color: Color(0xFFDCE5F2),
                                    ),
                                  ),
                                  child: Theme(
                                    data: Theme.of(context).copyWith(
                                      dividerColor: Colors.transparent,
                                    ),
                                    child: ExpansionTile(
                                      initiallyExpanded: _summaryExpandedMobile,
                                      onExpansionChanged: (value) => setState(
                                        () => _summaryExpandedMobile = value,
                                      ),
                                      title: const Text(
                                        'Resumo da etapa',
                                        style: TextStyle(
                                          fontWeight: FontWeight.w700,
                                          color: Color(0xFF0B3C5D),
                                        ),
                                      ),
                                      subtitle: const Text(
                                        'PxS, controles, status e acoes',
                                      ),
                                      childrenPadding:
                                          const EdgeInsets.fromLTRB(
                                            12,
                                            0,
                                            12,
                                            12,
                                          ),
                                      children: [
                                        fixedSummaryDate,
                                        const SizedBox(height: 8),
                                        summaryPanel,
                                      ],
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

import '../config/api_config.dart';
import '../services/api_service.dart';
import '../widgets/app_back_button.dart';

class AprApprovalScreen extends StatefulWidget {
  final int aprId;
  final String atividade;
  final int probabilidade;
  final int severidade;
  final String classificacao;

  const AprApprovalScreen({
    super.key,
    required this.aprId,
    required this.atividade,
    required this.probabilidade,
    required this.severidade,
    required this.classificacao,
  });

  @override
  State<AprApprovalScreen> createState() => _AprApprovalScreenState();
}

class _AprApprovalScreenState extends State<AprApprovalScreen> {
  late final ApiService _api;

  final TextEditingController _reasonCtrl = TextEditingController();
  final TextEditingController _manualApproverCtrl = TextEditingController();

  bool _loading = true;
  bool _decisionBusy = false;
  bool _pdfBusy = false;
  bool _savePlatformBusy = false;

  String? _error;
  String? _shareUrl;
  String? _approvedByName;
  String _status = 'submitted';

  bool _matrixReady = false;
  bool _isApproved = false;
  int _hazardCount = 0;
  int _controlCount = 0;
  int _stepCount = 0;
  int _stepsMissingFields = 0;
  int _stepsMissingEvidence = 0;
  int? _selectedApproverId;
  DateTime? _dueAt;

  List<Map<String, dynamic>> _approvers = <Map<String, dynamic>>[];

  @override
  void initState() {
    super.initState();
    _api = ApiService(baseUrl: resolveBaseUrl());
    _loadData();
  }

  @override
  void dispose() {
    _reasonCtrl.dispose();
    _manualApproverCtrl.dispose();
    super.dispose();
  }

  bool _isApproverRole(String role) {
    final r = role.trim().toLowerCase();
    return r.contains('admin') ||
        r.contains('aprova') ||
        r.contains('gestor') ||
        r.contains('seguranca');
  }

  bool _isApprovedStatus(String status) {
    final s = status.trim().toLowerCase();
    return s == 'approved' ||
        s == 'aprovado' ||
        s == 'final' ||
        s == 'arquivado' ||
        s == 'archived';
  }

  bool _isBlank(dynamic value) {
    if (value == null) return true;
    return value.toString().trim().isEmpty;
  }

  Future<void> _loadData() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final usersFuture = _api.getCompanyUsers();
      final aprFuture = _api.getAprMvpByExternalId(widget.aprId.toString());
      final detailsFuture = _api.getApr(widget.aprId);
      final results = await Future.wait([
        usersFuture,
        aprFuture,
        detailsFuture,
      ]);

      final users = results[0] as List<Map<String, dynamic>>;
      final apr = results[1] as Map<String, dynamic>;
      final details = results[2] as Map<String, dynamic>;

      final hazards = (apr['hazards'] as List<dynamic>? ?? <dynamic>[]);
      final controls = (apr['controls'] as List<dynamic>? ?? <dynamic>[]);
      final steps = (details['passos'] as List<dynamic>? ?? <dynamic>[])
          .whereType<Map<String, dynamic>>()
          .toList();
      final status = apr['status']?.toString() ?? 'submitted';
      var missingFields = 0;
      var missingEvidence = 0;
      for (final step in steps) {
        final requiredOk =
            !_isBlank(step['descricao']) &&
            !_isBlank(step['perigos']) &&
            !_isBlank(step['medidas_controle']) &&
            !_isBlank(step['epis']);
        if (!requiredOk) {
          missingFields += 1;
        }
        final technical = step['technical_evidence'];
        final evidenceUrl = technical is Map<String, dynamic>
            ? technical['url']?.toString()
            : null;
        if (_isBlank(evidenceUrl)) {
          missingEvidence += 1;
        }
      }

      if (!mounted) return;
      setState(() {
        _approvers = users
            .where((u) => _isApproverRole(u['role']?.toString() ?? ''))
            .toList();
        _hazardCount = hazards.length;
        _controlCount = controls.length;
        _stepCount = steps.length;
        _stepsMissingFields = missingFields;
        _stepsMissingEvidence = missingEvidence;
        _matrixReady =
            _hazardCount > 0 &&
            _controlCount > 0 &&
            _stepCount > 0 &&
            _stepsMissingFields == 0 &&
            _stepsMissingEvidence == 0;
        _status = status;
        _isApproved = _isApprovedStatus(status);
        _approvedByName = apr['approved_by_name']?.toString();
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = 'Falha ao carregar aprovacao: $e');
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _pickDueDate() async {
    final picked = await showDatePicker(
      context: context,
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(const Duration(days: 365)),
      initialDate: DateTime.now().add(const Duration(days: 2)),
    );
    if (picked == null || !mounted) return;
    setState(() => _dueAt = picked);
  }

  Future<void> _sendDecision(String decision) async {
    final reason = _reasonCtrl.text.trim();
    if (!_matrixReady && decision == 'approve') {
      _showSnack(
        'Matriz incompleta. Preencha perigos, controles, passos e evidencias antes da aprovacao.',
      );
      return;
    }
    if ((decision == 'reject' || decision == 'request_evidence') &&
        reason.isEmpty) {
      _showSnack('Motivo obrigatorio para reprovar/solicitar evidencia.');
      return;
    }
    if (decision == 'approve' &&
        _selectedApproverId == null &&
        _manualApproverCtrl.text.trim().isEmpty) {
      _showSnack('Selecione ou informe quem aprovou a APR.');
      return;
    }

    setState(() => _decisionBusy = true);
    try {
      final response = await _api.decideAprApproval(
        aprId: widget.aprId,
        decision: decision,
        reason: reason.isEmpty ? null : reason,
        approvedByUserId: _selectedApproverId,
        approvedByName: _manualApproverCtrl.text.trim().isEmpty
            ? null
            : _manualApproverCtrl.text.trim(),
        dueAt: _dueAt,
      );

      if (!mounted) return;
      final status = response['status']?.toString() ?? _status;
      setState(() {
        _status = status;
        _isApproved = _isApprovedStatus(status);
        _approvedByName =
            response['approved_by_name']?.toString() ?? _approvedByName;
      });

      if (decision == 'approve') {
        _showSnack(
          'APR aprovada. PDF liberado para gerar e salvar na plataforma.',
        );
      } else if (decision == 'request_evidence') {
        _showSnack('Solicitacao de evidencia registrada com sucesso.');
      } else {
        _showSnack('APR reprovada com motivo registrado.');
      }
    } catch (e) {
      _showSnack('Falha ao registrar decisao: $e');
    } finally {
      if (mounted) {
        setState(() => _decisionBusy = false);
      }
    }
  }

  Future<void> _generateAndOpenPdf() async {
    if (!_isApproved) {
      _showSnack('PDF so pode ser gerado apos aprovacao.');
      return;
    }

    setState(() => _pdfBusy = true);
    try {
      final bytes = await _api.generateFinalPdfV1(aprId: widget.aprId);
      final path = await _savePdfLocally(bytes);
      await OpenFilex.open(path);
      _showSnack('PDF gerado e salvo localmente com sucesso.');
    } catch (e) {
      _showSnack('Falha ao gerar PDF: $e');
    } finally {
      if (mounted) {
        setState(() => _pdfBusy = false);
      }
    }
  }

  Future<void> _savePdfOnPlatform() async {
    if (!_isApproved) {
      _showSnack('Salvamento em plataforma disponivel apenas apos aprovacao.');
      return;
    }

    setState(() => _savePlatformBusy = true);
    try {
      final response = await _api.createAprShare(aprId: widget.aprId);
      if (!mounted) return;
      setState(() => _shareUrl = response['share_url']?.toString());
      _showSnack('PDF salvo na plataforma e link gerado.');
    } catch (e) {
      _showSnack('Falha ao salvar PDF na plataforma: $e');
    } finally {
      if (mounted) {
        setState(() => _savePlatformBusy = false);
      }
    }
  }

  Future<String> _savePdfLocally(Uint8List bytes) async {
    final directory = await getApplicationDocumentsDirectory();
    final filename =
        'APR_${widget.aprId}_${DateTime.now().toIso8601String().split('T').first}.pdf';
    final filePath = '${directory.path}/$filename';
    final file = File(filePath);
    await file.writeAsBytes(bytes);
    return filePath;
  }

  void _showSnack(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    final isWide = width >= 940;

    return Scaffold(
      appBar: AppBar(
        leading: const AppBackButton(),
        title: const Text('Etapa 4 - Aprovacao'),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadData,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(16),
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 1180),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _stageHeader(),
                        const SizedBox(height: 14),
                        _heroSummary(),
                        const SizedBox(height: 14),
                        if (_error != null)
                          _warningCard(
                            _error!,
                            color: Colors.red.shade100,
                            borderColor: Colors.red.shade300,
                          ),
                        if (!_matrixReady)
                          _warningCard(
                            'Todas as secoes sao obrigatorias. Volte na matriz, complete perigos/controles/evidencias e salve novamente.',
                            color: Colors.amber.shade100,
                            borderColor: Colors.amber.shade300,
                          ),
                        const SizedBox(height: 8),
                        isWide
                            ? Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Expanded(flex: 7, child: _approvalFormCard()),
                                  const SizedBox(width: 12),
                                  Expanded(flex: 5, child: _pdfCard()),
                                ],
                              )
                            : Column(
                                children: [
                                  _approvalFormCard(),
                                  const SizedBox(height: 12),
                                  _pdfCard(),
                                ],
                              ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
    );
  }

  Widget _stageHeader() {
    final stages = <String>[
      'Criar',
      'Perigos',
      'Controles',
      'Aprovacao',
      'Execucao',
      'Relatorio',
    ];
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'FLUXO APR',
              style: TextStyle(
                fontWeight: FontWeight.w600,
                letterSpacing: 1.2,
                color: Color(0xFF0B3C5D),
              ),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (var i = 0; i < stages.length; i++)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 10,
                    ),
                    decoration: BoxDecoration(
                      color: i < 3
                          ? const Color(0xFFE9F7F2)
                          : (i == 3
                                ? const Color(0xFFDBEAFE)
                                : const Color(0xFFF3F4F6)),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: i == 3
                            ? const Color(0xFF0B3C5D)
                            : const Color(0xFFD1D5DB),
                      ),
                    ),
                    child: Text(
                      'Etapa ${i + 1} - ${stages[i]}',
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _heroSummary() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        gradient: const LinearGradient(
          colors: [Color(0xFF0B3C5D), Color(0xFF153A59)],
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'ASSINATURA DE APROVACAO',
            style: TextStyle(
              color: Colors.white70,
              letterSpacing: 2,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            widget.atividade,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 26,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Status: ${_status.toUpperCase()}  •  Matriz: ${_matrixReady ? "COMPLETA" : "INCOMPLETA"}  •  Aprovada por: ${_approvedByName ?? "aguardando"}',
            style: const TextStyle(color: Colors.white, fontSize: 13),
          ),
          const SizedBox(height: 6),
          Text(
            'Risco: ${widget.classificacao} (P=${widget.probabilidade} x S=${widget.severidade})',
            style: const TextStyle(color: Colors.white70),
          ),
        ],
      ),
    );
  }

  Widget _approvalFormCard() {
    final selectedApproverExists = _approvers.any(
      (item) => item['id'] == _selectedApproverId,
    );
    if (!selectedApproverExists) {
      _selectedApproverId = null;
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Decisao de aprovacao',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 10),
            Text('Perigos mapeados: $_hazardCount'),
            Text('Controles aplicados: $_controlCount'),
            Text('Passos preenchidos: $_stepCount'),
            Text(
              'Passos com campos pendentes: $_stepsMissingFields',
              style: TextStyle(
                color: _stepsMissingFields > 0 ? Colors.red.shade700 : null,
              ),
            ),
            Text(
              'Passos sem evidencia: $_stepsMissingEvidence',
              style: TextStyle(
                color: _stepsMissingEvidence > 0 ? Colors.red.shade700 : null,
              ),
            ),
            const SizedBox(height: 10),
            if (_approvers.isNotEmpty)
              DropdownButtonFormField<int>(
                initialValue: _selectedApproverId,
                decoration: const InputDecoration(
                  labelText: 'Aprovador',
                  border: OutlineInputBorder(),
                ),
                items: _approvers
                    .map(
                      (u) => DropdownMenuItem<int>(
                        value: u['id'] as int,
                        child: Text(
                          '${u['name'] ?? u['email']} - ${u['role'] ?? ''}',
                        ),
                      ),
                    )
                    .toList(),
                onChanged: _decisionBusy
                    ? null
                    : (value) => setState(() => _selectedApproverId = value),
              )
            else
              TextField(
                controller: _manualApproverCtrl,
                enabled: !_decisionBusy,
                decoration: const InputDecoration(
                  labelText: 'Aprovador (manual)',
                  border: OutlineInputBorder(),
                ),
              ),
            const SizedBox(height: 10),
            TextField(
              controller: _reasonCtrl,
              enabled: !_decisionBusy,
              minLines: 3,
              maxLines: 5,
              decoration: const InputDecoration(
                labelText:
                    'Motivo (obrigatorio para reprovar/solicitar evidencia)',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                OutlinedButton.icon(
                  onPressed: _decisionBusy ? null : _pickDueDate,
                  icon: const Icon(Icons.schedule),
                  label: Text(
                    _dueAt == null
                        ? 'Prazo da pendencia'
                        : 'Prazo: ${_dueAt!.day.toString().padLeft(2, '0')}/${_dueAt!.month.toString().padLeft(2, '0')}/${_dueAt!.year}',
                  ),
                ),
                ElevatedButton(
                  onPressed: _decisionBusy
                      ? null
                      : () => _sendDecision('request_evidence'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.amber.shade700,
                  ),
                  child: const Text('Solicitar evidencia'),
                ),
                ElevatedButton(
                  onPressed: _decisionBusy
                      ? null
                      : () => _sendDecision('reject'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.red.shade700,
                  ),
                  child: const Text('Reprovar'),
                ),
                ElevatedButton(
                  onPressed: _decisionBusy
                      ? null
                      : () => _sendDecision('approve'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF0B3C5D),
                  ),
                  child: _decisionBusy
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Text('Aprovar e liberar PDF'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _pdfCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'PDF e Biblioteca',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 10),
            Text(
              _isApproved
                  ? 'Aprovada. PDF liberado para gerar e salvar.'
                  : 'Aguardando aprovacao formal para liberar PDF.',
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: (_pdfBusy || !_isApproved)
                    ? null
                    : _generateAndOpenPdf,
                icon: const Icon(Icons.picture_as_pdf),
                label: _pdfBusy
                    ? const Text('Gerando PDF...')
                    : const Text('Gerar e abrir PDF'),
              ),
            ),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: (_savePlatformBusy || !_isApproved)
                    ? null
                    : _savePdfOnPlatform,
                icon: const Icon(Icons.cloud_upload_outlined),
                label: _savePlatformBusy
                    ? const Text('Salvando...')
                    : const Text('Salvar PDF na plataforma'),
              ),
            ),
            if (_shareUrl != null) ...[
              const SizedBox(height: 10),
              SelectableText('Link salvo: $_shareUrl'),
            ],
          ],
        ),
      ),
    );
  }

  Widget _warningCard(
    String message, {
    required Color color,
    required Color borderColor,
  }) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: borderColor),
      ),
      child: Text(message),
    );
  }
}

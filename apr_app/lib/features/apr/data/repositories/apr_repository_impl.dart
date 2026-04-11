import 'dart:typed_data';

import 'package:intl/intl.dart';

import '../../../../core/network/api_client.dart';
import '../../../../core/utils/apr_form_codec.dart';
import '../../domain/entities/apr_models.dart';
import '../../domain/repositories/apr_repository.dart';
import '../dtos/apr_dtos.dart';
import '../local/workflow_mock_store.dart';
import '../mappers/apr_mapper.dart';

class AprRepositoryImpl implements AprRepository {
  AprRepositoryImpl(this._apiClient, this._mockStore);

  final ApiClient _apiClient;
  final WorkflowMockStore _mockStore;

  @override
  Future<List<AprSummary>> listAprs() async {
    final mvpJson = await _apiClient.getList('/aprs');
    final mvpItems = mvpJson
        .map(
          (item) => AprMvpDto.fromJson(
            (item as Map?)?.cast<String, dynamic>() ?? const {},
          ),
        )
        .toList();
    final legacyItems = await _bestEffortLegacyList();

    return mvpItems.map((mvp) {
      final legacy = _matchLegacy(mvp, legacyItems);
      return AprMapper.toSummary(mvp, legacy: legacy);
    }).toList();
  }

  @override
  Future<AprDetail> loadAprDetail(
    String aprId, {
    bool ensureLegacy = false,
  }) async {
    final mvp = AprMvpDto.fromJson(await _apiClient.get('/aprs/$aprId'));
    var legacyId = await _resolveLegacyId(aprId, mvp);
    if (ensureLegacy && legacyId == null) {
      legacyId = await _createLegacyMirror(mvp);
    }
    LegacyAprDto? legacy;
    if (legacyId != null) {
      legacy = LegacyAprDto.fromJson(
        await _apiClient.get('/v1/aprs/$legacyId'),
      );
    }
    final approval = await _mockStore.readApproval(aprId);
    final execution = await _mockStore.readExecution(aprId);
    return AprMapper.toDetail(
      mvp,
      legacy: legacy,
      approval: approval,
      execution: execution,
    );
  }

  @override
  Future<AprSummary> createApr(AprFormDraft draft) async {
    final response = await _apiClient.post(
      '/aprs',
      body: <String, dynamic>{
        'title': draft.title.trim(),
        'location': AprFormCodec.buildLocation(
          site: draft.site,
          area: draft.area,
        ),
        'activity': AprFormCodec.buildActivity(
          characteristic: draft.characteristic,
          description: draft.description,
          contractUnit: draft.contractUnit,
          shift: draft.shift,
          evaluator: draft.evaluator,
        ),
        'hazards': const <dynamic>[],
        'controls': const <dynamic>[],
      },
    );
    return AprMapper.toSummary(AprMvpDto.fromJson(response));
  }

  @override
  Future<AprDetail> saveAprBase(String aprId, AprFormDraft draft) async {
    final detail = await loadAprDetail(aprId);
    await _apiClient.put(
      '/aprs/$aprId',
      body: <String, dynamic>{
        'title': draft.title.trim(),
        'location': AprFormCodec.buildLocation(
          site: draft.site,
          area: draft.area,
        ),
        'activity': AprFormCodec.buildActivity(
          characteristic: draft.characteristic,
          description: draft.description,
          contractUnit: draft.contractUnit,
          shift: draft.shift,
          evaluator: draft.evaluator,
        ),
        'hazards': detail.summary.hazards,
        'controls': detail.summary.controls,
      },
    );

    final legacyId = await _resolveLegacyId(aprId, null);
    if (legacyId != null) {
      await _apiClient.patch(
        '/v1/aprs/$legacyId',
        body: <String, dynamic>{
          'worksite': draft.site,
          'sector': draft.area,
          'responsible': draft.evaluator,
          'date': draft.date == null
              ? null
              : DateFormat('yyyy-MM-dd').format(draft.date!),
          'titulo': draft.title,
          'activity_name': draft.characteristic,
          'descricao': draft.description,
        },
      );
    }

    return loadAprDetail(aprId);
  }

  @override
  Future<AprDetail> saveControls(String aprId, ControlsDraft draft) async {
    final detail = await loadAprDetail(aprId, ensureLegacy: true);
    final legacyId = detail.summary.legacyId;
    if (legacyId == null) {
      return detail;
    }

    final mvpControls = <Map<String, dynamic>>[
      ...draft.technicalParameters.entries
          .where((entry) => entry.value)
          .map(
            (entry) => <String, dynamic>{
              'type': 'technical_parameter',
              'label': entry.key,
            },
          ),
      ...draft.steps.map(
        (step) => <String, dynamic>{
          'type': 'step',
          'order': step.order,
          'description': step.description,
          'hazards': step.hazards,
          'measures': step.measures,
        },
      ),
    ];

    await _apiClient.put(
      '/aprs/$aprId',
      body: <String, dynamic>{
        'title': detail.summary.title,
        'location': detail.summary.location,
        'activity': detail.summary.activity,
        'hazards': detail.summary.hazards,
        'controls': mvpControls,
      },
    );

    await _apiClient.patch(
      '/v1/aprs/$legacyId',
      body: <String, dynamic>{
        'descricao': draft.description,
        'dangerous_energies_checklist': <String, dynamic>{
          'hydraulic': draft.technicalParameters['Hidraulica'] ?? false,
          'residual': draft.technicalParameters['Residual'] ?? false,
          'kinetic': draft.technicalParameters['Cinetica'] ?? false,
          'mechanical': draft.technicalParameters['Mecanica'] ?? false,
          'electrical': draft.technicalParameters['Eletrica'] ?? false,
          'gravitational_potential':
              draft.technicalParameters['Gravitacional'] ?? false,
          'thermal': draft.technicalParameters['Termica'] ?? false,
          'pneumatic': draft.technicalParameters['Pneumatica'] ?? false,
        },
      },
    );

    await _apiClient.post(
      '/v1/aprs/$legacyId/steps/bulk',
      body: <String, dynamic>{
        'replace': true,
        'items': draft.steps
            .map(
              (step) => <String, dynamic>{
                'step_order': step.order,
                'description': step.description,
                'hazards': step.hazards,
                'risks': step.risks,
                'measures': step.measures,
                'epis': step.epis,
                'regulations': step.regulations,
              },
            )
            .toList(),
      },
    );

    return loadAprDetail(aprId, ensureLegacy: true);
  }

  @override
  Future<AprDetail> submitForApproval(String aprId) async {
    try {
      await _apiClient.post('/aprs/$aprId/submit');
    } catch (_) {}

    final detail = await loadAprDetail(aprId, ensureLegacy: true);
    final legacyId = detail.summary.legacyId;
    if (legacyId != null) {
      try {
        await _apiClient.patch(
          '/v1/aprs/$legacyId/status',
          body: <String, dynamic>{'status': 'submitted'},
        );
      } catch (_) {}
    }
    return loadAprDetail(aprId, ensureLegacy: true);
  }

  @override
  Future<AprDetail> approve(
    String aprId, {
    required String approver,
    String? note,
  }) async {
    final detail = await loadAprDetail(aprId, ensureLegacy: true);
    final legacyId = detail.summary.legacyId;
    if (legacyId != null) {
      await _apiClient.patch(
        '/v1/aprs/$legacyId/status',
        body: <String, dynamic>{'status': 'approved'},
      );
    }
    await _mockStore.writeApproval(
      aprId,
      ApprovalMeta(
        approvedBy: approver.trim(),
        approvedAt: DateTime.now(),
        lastComment: note,
      ),
    );
    return loadAprDetail(aprId, ensureLegacy: true);
  }

  @override
  Future<AprDetail> updateExecution(
    String aprId, {
    DateTime? startedAt,
    DateTime? pausedAt,
    DateTime? finishedAt,
    String? notes,
    List<bool>? checklist,
  }) async {
    final current = await _mockStore.readExecution(aprId);
    final next = ExecutionMeta(
      startedAt: startedAt ?? current.startedAt,
      pausedAt: pausedAt ?? current.pausedAt,
      finishedAt: finishedAt ?? current.finishedAt,
      notes: notes ?? current.notes,
      checklist: checklist ?? current.checklist,
    );
    await _mockStore.writeExecution(aprId, next);
    final detail = await loadAprDetail(aprId, ensureLegacy: true);
    if (finishedAt != null && detail.summary.legacyId != null) {
      try {
        final responsible = detail.formFields.evaluator.trim().isEmpty
            ? 'Equipe HCS'
            : detail.formFields.evaluator.trim();
        await _apiClient.post(
          '/v1/aprs/${detail.summary.legacyId}/finalize',
          body: <String, dynamic>{'responsible_confirm': responsible},
        );
      } catch (_) {}
    }
    return loadAprDetail(aprId, ensureLegacy: true);
  }

  @override
  Future<List<int>> exportPdf(String aprId) async {
    final detail = await loadAprDetail(aprId, ensureLegacy: true);
    final legacyId = detail.summary.legacyId;
    if (legacyId == null) {
      return Uint8List(0);
    }
    final bytes = await _apiClient.getBytes('/v1/aprs/$legacyId/pdf');
    return bytes;
  }

  @override
  Future<String> sharePdf(String aprId) async {
    final detail = await loadAprDetail(aprId, ensureLegacy: true);
    final legacyId = detail.summary.legacyId;
    if (legacyId == null) {
      return '';
    }
    final response = await _apiClient.post('/v1/aprs/$legacyId/share');
    return response['share_url']?.toString() ?? '';
  }

  @override
  Future<AprAnalytics> loadAnalytics() async {
    final items = await listAprs();
    final allScores = items
        .map((item) => item.riskScore)
        .where((score) => score > 0)
        .toList();
    final inExecution = items
        .where(
          (item) =>
              item.status == AprStatus.inProgress ||
              item.status == AprStatus.paused,
        )
        .length;
    return AprAnalytics(
      total: items.length,
      draft: items.where((item) => item.status == AprStatus.draft).length,
      inApproval: items
          .where(
            (item) =>
                item.status == AprStatus.submitted ||
                item.status == AprStatus.approved,
          )
          .length,
      inExecution: inExecution,
      finished: items
          .where(
            (item) =>
                item.status == AprStatus.finished ||
                item.status == AprStatus.archived,
          )
          .length,
      highRisk: items.where((item) => item.riskScore >= 15).length,
      avgScore: allScores.isEmpty
          ? 0
          : allScores.reduce((a, b) => a + b) / allScores.length,
    );
  }

  LegacyAprDto? _matchLegacy(AprMvpDto mvp, List<LegacyAprDto> candidates) {
    for (final item in candidates) {
      if (item.title.trim().toLowerCase() == mvp.title.trim().toLowerCase()) {
        return item;
      }
      if (mvp.location != null &&
          item.worksite.trim().toLowerCase() ==
              mvp.location!.trim().toLowerCase()) {
        return item;
      }
    }
    return null;
  }

  Future<int?> _resolveLegacyId(String aprId, AprMvpDto? mvp) async {
    final legacyItems = await _bestEffortLegacyList();
    final target =
        mvp ?? AprMvpDto.fromJson(await _apiClient.get('/aprs/$aprId'));
    return _matchLegacy(target, legacyItems)?.id;
  }

  Future<int> _createLegacyMirror(AprMvpDto mvp) async {
    final fields = AprFormCodec.decode(
      location: mvp.location,
      activity: mvp.activity,
    );
    final response = await _apiClient.post(
      '/v1/aprs',
      body: <String, dynamic>{
        'worksite': fields.site.isEmpty
            ? (mvp.location ?? 'Nao informado')
            : fields.site,
        'sector': fields.area.isEmpty ? 'Nao informado' : fields.area,
        'responsible': fields.evaluator.isEmpty
            ? 'Equipe HCS'
            : fields.evaluator,
        'date': DateFormat('yyyy-MM-dd').format(DateTime.now()),
        'activity_id': 'mvp-${mvp.id}',
        'activity_name': fields.characteristic.isEmpty
            ? mvp.title
            : fields.characteristic,
        'titulo': mvp.title,
        'risco': 'mvp',
        'descricao': fields.description.isEmpty
            ? (mvp.activity ?? mvp.title)
            : fields.description,
      },
    );
    return (response['id'] as num?)?.toInt() ?? 0;
  }

  Future<List<LegacyAprDto>> _bestEffortLegacyList() async {
    try {
      final legacyJson = await _apiClient.get('/v1/aprs?skip=0&limit=250');
      return (((legacyJson['items'] as List?) ?? const <dynamic>[]))
          .map(
            (item) => LegacyAprDto.fromJson(
              (item as Map?)?.cast<String, dynamic>() ?? const {},
            ),
          )
          .toList();
    } catch (_) {
      return const <LegacyAprDto>[];
    }
  }
}

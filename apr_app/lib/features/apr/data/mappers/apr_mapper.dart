import '../../../../core/utils/apr_form_codec.dart';
import '../../domain/entities/apr_models.dart';
import '../dtos/apr_dtos.dart';

class AprMapper {
  const AprMapper._();

  static AprStatus statusFromMvp(String raw) {
    switch (raw) {
      case 'submitted':
        return AprStatus.submitted;
      case 'approved':
        return AprStatus.approved;
      case 'rejected':
        return AprStatus.rejected;
      case 'archived':
        return AprStatus.archived;
      default:
        return AprStatus.draft;
    }
  }

  static AprStatus statusFromLegacy(String raw) {
    switch (raw) {
      case 'aprovado':
      case 'approved':
        return AprStatus.approved;
      case 'reprovado':
      case 'rejected':
        return AprStatus.rejected;
      case 'arquivado':
      case 'archived':
        return AprStatus.archived;
      case 'em_execucao':
        return AprStatus.inProgress;
      case 'pausado':
        return AprStatus.paused;
      case 'finalizado':
        return AprStatus.finished;
      case 'enviado':
      case 'submitted':
        return AprStatus.submitted;
      default:
        return AprStatus.draft;
    }
  }

  static AprSummary toSummary(AprMvpDto dto, {LegacyAprDto? legacy}) {
    final riskItems = legacy?.riskItems ?? const <LegacyRiskItemDto>[];
    final topScore = riskItems.isEmpty
        ? 0
        : riskItems
              .map((item) => item.probability * item.severity)
              .reduce((a, b) => a > b ? a : b);
    return AprSummary(
      id: dto.id,
      legacyId: legacy?.id,
      title: dto.title,
      location: dto.location ?? legacy?.worksite,
      activity: dto.activity ?? legacy?.description,
      status: legacy != null
          ? statusFromLegacy(legacy.status)
          : statusFromMvp(dto.status),
      createdAt: dto.createdAt,
      updatedAt: legacy?.updatedAt ?? dto.updatedAt,
      riskScore: topScore,
      progress: _progressFromStatus(
        legacy != null
            ? statusFromLegacy(legacy.status)
            : statusFromMvp(dto.status),
      ),
      hazards: dto.hazards,
      controls: dto.controls,
    );
  }

  static AprDetail toDetail(
    AprMvpDto dto, {
    LegacyAprDto? legacy,
    required ApprovalMeta approval,
    required ExecutionMeta execution,
  }) {
    final fields = AprFormCodec.decode(
      location: dto.location ?? legacy?.worksite,
      activity: dto.activity ?? legacy?.description,
    );
    final formDraft = AprFormDraft(
      title: dto.title,
      site: fields.site,
      area: fields.area,
      contractUnit: fields.contractUnit,
      shift: fields.shift,
      evaluator: fields.evaluator.isNotEmpty
          ? fields.evaluator
          : (legacy?.responsible ?? ''),
      characteristic: fields.characteristic,
      description: fields.description,
      date: legacy?.date,
    );

    return AprDetail(
      summary: toSummary(dto, legacy: legacy),
      formFields: formDraft,
      description: legacy?.description ?? dto.activity ?? '',
      stepDrafts: (legacy?.steps ?? const <LegacyStepDto>[])
          .map(
            (step) => AprStep(
              id: step.id,
              order: step.order,
              description: step.description,
              hazards: AprFormCodec.splitLines(step.hazards),
              risks: AprFormCodec.splitLines(step.risks),
              measures: AprFormCodec.splitLines(step.measures),
              epis: AprFormCodec.splitLines(step.epis),
              regulations: AprFormCodec.splitLines(step.regulations),
            ),
          )
          .toList(),
      riskItems: (legacy?.riskItems ?? const <LegacyRiskItemDto>[])
          .map(
            (item) => RiskItem(
              id: item.id,
              stepId: item.stepId,
              description: item.description,
              probability: item.probability,
              severity: item.severity,
              level: item.level,
            ),
          )
          .toList(),
      energyChecklist: {
        'Hidraulica': legacy?.dangerousEnergiesChecklist['hydraulic'] == true,
        'Residual': legacy?.dangerousEnergiesChecklist['residual'] == true,
        'Cinetica': legacy?.dangerousEnergiesChecklist['kinetic'] == true,
        'Mecanica': legacy?.dangerousEnergiesChecklist['mechanical'] == true,
        'Eletrica': legacy?.dangerousEnergiesChecklist['electrical'] == true,
        'Gravitacional':
            legacy?.dangerousEnergiesChecklist['gravitational_potential'] ==
            true,
        'Termica': legacy?.dangerousEnergiesChecklist['thermal'] == true,
        'Pneumatica': legacy?.dangerousEnergiesChecklist['pneumatic'] == true,
      },
      approval: approval,
      execution: execution,
    );
  }

  static double _progressFromStatus(AprStatus status) {
    switch (status) {
      case AprStatus.draft:
        return 0.2;
      case AprStatus.submitted:
        return 0.55;
      case AprStatus.approved:
        return 0.78;
      case AprStatus.inProgress:
      case AprStatus.paused:
        return 0.88;
      case AprStatus.finished:
      case AprStatus.archived:
        return 1;
      case AprStatus.rejected:
        return 0.42;
    }
  }
}

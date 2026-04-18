class AprMvpDto {
  const AprMvpDto({
    required this.id,
    required this.title,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    required this.hazards,
    required this.controls,
    this.location,
    this.activity,
  });

  factory AprMvpDto.fromJson(Map<String, dynamic> json) {
    return AprMvpDto(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? 'APR',
      status: json['status']?.toString() ?? 'draft',
      createdAt:
          DateTime.tryParse(json['created_at']?.toString() ?? '') ??
          DateTime.now(),
      updatedAt:
          DateTime.tryParse(json['updated_at']?.toString() ?? '') ??
          DateTime.now(),
      location: json['location']?.toString(),
      activity: json['activity']?.toString(),
      hazards: ((json['hazards'] as List?) ?? const <dynamic>[])
          .map(
            (item) =>
                (item as Map?)?.cast<String, dynamic>() ??
                const <String, dynamic>{},
          )
          .toList(),
      controls: ((json['controls'] as List?) ?? const <dynamic>[])
          .map(
            (item) =>
                (item as Map?)?.cast<String, dynamic>() ??
                const <String, dynamic>{},
          )
          .toList(),
    );
  }

  final String id;
  final String title;
  final String status;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String? location;
  final String? activity;
  final List<Map<String, dynamic>> hazards;
  final List<Map<String, dynamic>> controls;
}

class LegacyAprDto {
  const LegacyAprDto({
    required this.id,
    required this.title,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    required this.description,
    required this.worksite,
    required this.sector,
    required this.responsible,
    required this.activityId,
    required this.risk,
    required this.dangerousEnergiesChecklist,
    this.date,
    this.steps = const <LegacyStepDto>[],
    this.riskItems = const <LegacyRiskItemDto>[],
  });

  factory LegacyAprDto.fromJson(Map<String, dynamic> json) {
    return LegacyAprDto(
      id: (json['id'] as num?)?.toInt() ?? 0,
      title: json['titulo']?.toString() ?? 'APR',
      status: json['status']?.toString() ?? 'rascunho',
      createdAt:
          DateTime.tryParse(json['criado_em']?.toString() ?? '') ??
          DateTime.now(),
      updatedAt:
          DateTime.tryParse(json['atualizado_em']?.toString() ?? '') ??
          DateTime.now(),
      description: json['descricao']?.toString() ?? '',
      worksite: json['worksite']?.toString() ?? '',
      sector: json['sector']?.toString() ?? '',
      responsible: json['responsible']?.toString() ?? '',
      activityId: _readString(json, 'activity_id', fallbackKey: 'atividade_id'),
      risk: json['risco']?.toString() ?? '',
      date: json['date'] == null
          ? null
          : DateTime.tryParse(json['date'].toString()),
      dangerousEnergiesChecklist:
          (json['dangerous_energies_checklist'] as Map?)
              ?.cast<String, dynamic>() ??
          const {},
      steps: ((json['passos'] as List?) ?? const <dynamic>[])
          .map(
            (item) => LegacyStepDto.fromJson(
              (item as Map?)?.cast<String, dynamic>() ?? const {},
            ),
          )
          .toList(),
      riskItems: ((json['risk_items'] as List?) ?? const <dynamic>[])
          .map(
            (item) => LegacyRiskItemDto.fromJson(
              (item as Map?)?.cast<String, dynamic>() ?? const {},
            ),
          )
          .toList(),
    );
  }

  final int id;
  final String title;
  final String status;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String description;
  final String worksite;
  final String sector;
  final String responsible;
  final String? activityId;
  final String risk;
  final DateTime? date;
  final Map<String, dynamic> dangerousEnergiesChecklist;
  final List<LegacyStepDto> steps;
  final List<LegacyRiskItemDto> riskItems;
}

String? _readString(
  Map<String, dynamic> json,
  String key, {
  String? fallbackKey,
}) {
  final primary = json[key]?.toString().trim();
  if (primary != null && primary.isNotEmpty) {
    return primary;
  }
  if (fallbackKey == null) {
    return null;
  }
  final fallback = json[fallbackKey]?.toString().trim();
  if (fallback != null && fallback.isNotEmpty) {
    return fallback;
  }
  return null;
}

class LegacyStepDto {
  const LegacyStepDto({
    required this.id,
    required this.order,
    required this.description,
    required this.hazards,
    required this.risks,
    required this.measures,
    required this.epis,
    required this.regulations,
  });

  factory LegacyStepDto.fromJson(Map<String, dynamic> json) {
    return LegacyStepDto(
      id: (json['id'] as num?)?.toInt(),
      order: (json['ordem'] as num?)?.toInt() ?? 1,
      description: json['descricao']?.toString() ?? '',
      hazards: json['perigos']?.toString() ?? '',
      risks: json['riscos']?.toString() ?? '',
      measures: json['medidas_controle']?.toString() ?? '',
      epis: json['epis']?.toString() ?? '',
      regulations: json['normas']?.toString() ?? '',
    );
  }

  final int? id;
  final int order;
  final String description;
  final String hazards;
  final String risks;
  final String measures;
  final String epis;
  final String regulations;
}

class LegacyRiskItemDto {
  const LegacyRiskItemDto({
    required this.id,
    required this.stepId,
    required this.description,
    required this.probability,
    required this.severity,
    required this.level,
  });

  factory LegacyRiskItemDto.fromJson(Map<String, dynamic> json) {
    return LegacyRiskItemDto(
      id: (json['id'] as num?)?.toInt() ?? 0,
      stepId: (json['step_id'] as num?)?.toInt() ?? 0,
      description: json['risk_description']?.toString() ?? '',
      probability: (json['probability'] as num?)?.toInt() ?? 1,
      severity: (json['severity'] as num?)?.toInt() ?? 1,
      level: json['risk_level']?.toString() ?? 'Baixo',
    );
  }

  final int id;
  final int stepId;
  final String description;
  final int probability;
  final int severity;
  final String level;
}

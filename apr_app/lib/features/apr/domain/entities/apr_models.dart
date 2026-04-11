enum AprStatus {
  draft,
  submitted,
  approved,
  rejected,
  archived,
  inProgress,
  paused,
  finished,
}

enum WorkflowStage {
  create,
  controls,
  approval,
  execution,
  report;

  String get path => switch (this) {
    WorkflowStage.create => 'criar',
    WorkflowStage.controls => 'controles',
    WorkflowStage.approval => 'aprovacao',
    WorkflowStage.execution => 'execucao',
    WorkflowStage.report => 'relatorio',
  };

  String get label => switch (this) {
    WorkflowStage.create => 'Criar',
    WorkflowStage.controls => 'Matriz de risco',
    WorkflowStage.approval => 'Aprovacao',
    WorkflowStage.execution => 'Execucao',
    WorkflowStage.report => 'Relatorio',
  };

  String get title => switch (this) {
    WorkflowStage.create => 'Etapa 1 · Criar APR',
    WorkflowStage.controls => 'Etapa 2 · Matriz de risco',
    WorkflowStage.approval => 'Etapa 4 · Aprovacao',
    WorkflowStage.execution => 'Etapa 5 · Execucao',
    WorkflowStage.report => 'Etapa 6 · Relatorio',
  };

  static WorkflowStage? tryFromPath(String raw) {
    for (final stage in WorkflowStage.values) {
      if (stage.path == raw) {
        return stage;
      }
    }
    return null;
  }
}

class AprSummary {
  const AprSummary({
    required this.id,
    required this.title,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    this.legacyId,
    this.location,
    this.activity,
    this.riskScore = 0,
    this.progress = 0,
    this.hazards = const <Map<String, dynamic>>[],
    this.controls = const <Map<String, dynamic>>[],
  });

  final String id;
  final int? legacyId;
  final String title;
  final String? location;
  final String? activity;
  final AprStatus status;
  final DateTime createdAt;
  final DateTime updatedAt;
  final int riskScore;
  final double progress;
  final List<Map<String, dynamic>> hazards;
  final List<Map<String, dynamic>> controls;

  bool get isComplete =>
      status == AprStatus.finished || status == AprStatus.archived;
}

class AprStep {
  const AprStep({
    this.id,
    required this.order,
    required this.description,
    this.hazards = const <String>[],
    this.risks = const <String>[],
    this.measures = const <String>[],
    this.epis = const <String>[],
    this.regulations = const <String>[],
  });

  final int? id;
  final int order;
  final String description;
  final List<String> hazards;
  final List<String> risks;
  final List<String> measures;
  final List<String> epis;
  final List<String> regulations;
}

class RiskItem {
  const RiskItem({
    required this.id,
    required this.stepId,
    required this.description,
    required this.probability,
    required this.severity,
    required this.level,
  });

  final int id;
  final int stepId;
  final String description;
  final int probability;
  final int severity;
  final String level;

  int get score => probability * severity;
}

class ApprovalMeta {
  const ApprovalMeta({this.approvedBy, this.approvedAt, this.lastComment});

  final String? approvedBy;
  final DateTime? approvedAt;
  final String? lastComment;
}

class ExecutionMeta {
  const ExecutionMeta({
    this.startedAt,
    this.pausedAt,
    this.finishedAt,
    this.notes = '',
    this.checklist = const <bool>[],
  });

  final DateTime? startedAt;
  final DateTime? pausedAt;
  final DateTime? finishedAt;
  final String notes;
  final List<bool> checklist;
}

class AprDetail {
  const AprDetail({
    required this.summary,
    required this.formFields,
    required this.description,
    required this.stepDrafts,
    required this.riskItems,
    required this.energyChecklist,
    this.approval = const ApprovalMeta(),
    this.execution = const ExecutionMeta(),
  });

  final AprSummary summary;
  final AprFormDraft formFields;
  final String description;
  final List<AprStep> stepDrafts;
  final List<RiskItem> riskItems;
  final Map<String, bool> energyChecklist;
  final ApprovalMeta approval;
  final ExecutionMeta execution;

  AprDetail copyWith({
    AprSummary? summary,
    AprFormDraft? formFields,
    String? description,
    List<AprStep>? stepDrafts,
    List<RiskItem>? riskItems,
    Map<String, bool>? energyChecklist,
    ApprovalMeta? approval,
    ExecutionMeta? execution,
  }) {
    return AprDetail(
      summary: summary ?? this.summary,
      formFields: formFields ?? this.formFields,
      description: description ?? this.description,
      stepDrafts: stepDrafts ?? this.stepDrafts,
      riskItems: riskItems ?? this.riskItems,
      energyChecklist: energyChecklist ?? this.energyChecklist,
      approval: approval ?? this.approval,
      execution: execution ?? this.execution,
    );
  }
}

class AprFormDraft {
  const AprFormDraft({
    this.title = '',
    this.site = '',
    this.area = '',
    this.contractUnit = '',
    this.shift = '',
    this.evaluator = '',
    this.characteristic = '',
    this.description = '',
    this.date,
  });

  final String title;
  final String site;
  final String area;
  final String contractUnit;
  final String shift;
  final String evaluator;
  final String characteristic;
  final String description;
  final DateTime? date;

  AprFormDraft copyWith({
    String? title,
    String? site,
    String? area,
    String? contractUnit,
    String? shift,
    String? evaluator,
    String? characteristic,
    String? description,
    DateTime? date,
    bool clearDate = false,
  }) {
    return AprFormDraft(
      title: title ?? this.title,
      site: site ?? this.site,
      area: area ?? this.area,
      contractUnit: contractUnit ?? this.contractUnit,
      shift: shift ?? this.shift,
      evaluator: evaluator ?? this.evaluator,
      characteristic: characteristic ?? this.characteristic,
      description: description ?? this.description,
      date: clearDate ? null : (date ?? this.date),
    );
  }
}

class ControlsDraft {
  const ControlsDraft({
    required this.description,
    required this.technicalParameters,
    required this.steps,
  });

  final String description;
  final Map<String, bool> technicalParameters;
  final List<AprStep> steps;
}

class AprAnalytics {
  const AprAnalytics({
    required this.total,
    required this.draft,
    required this.inApproval,
    required this.inExecution,
    required this.finished,
    required this.highRisk,
    required this.avgScore,
  });

  final int total;
  final int draft;
  final int inApproval;
  final int inExecution;
  final int finished;
  final int highRisk;
  final double avgScore;
}

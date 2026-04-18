import 'dart:io';

import 'package:flutter/material.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_spacing.dart';
import '../../../../core/utils/app_formatters.dart';
import '../../../../shared/widgets/app_badge.dart';
import '../../../../shared/widgets/app_button.dart';
import '../../../../shared/widgets/app_feedback_state.dart';
import '../../../../shared/widgets/app_input.dart';
import '../../../../shared/widgets/app_panel.dart';
import '../../../../shared/widgets/section_header.dart';
import '../../../auth/domain/entities/app_user.dart';
import '../../../auth/presentation/controllers/session_controller.dart';
import '../../domain/entities/apr_models.dart';
import '../controllers/workflow_controller.dart';
import '../widgets/workflow_chrome.dart';
import '../widgets/workspace_scaffold.dart';

class WorkflowScreen extends StatefulWidget {
  const WorkflowScreen({
    super.key,
    required this.controller,
    required this.sessionController,
    required this.stage,
    required this.onDestinationSelected,
    required this.onStageChanged,
    required this.onLogout,
  });

  final WorkflowController controller;
  final SessionController sessionController;
  final WorkflowStage stage;
  final ValueChanged<ShellDestination> onDestinationSelected;
  final ValueChanged<WorkflowStage> onStageChanged;
  final Future<void> Function() onLogout;

  @override
  State<WorkflowScreen> createState() => _WorkflowScreenState();
}

class _WorkflowScreenState extends State<WorkflowScreen> {
  final _titleController = TextEditingController();
  final _siteController = TextEditingController();
  final _areaController = TextEditingController();
  final _contractController = TextEditingController();
  final _shiftController = TextEditingController();
  final _evaluatorController = TextEditingController();
  final _characteristicController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _approverController = TextEditingController();
  final _approvalNoteController = TextEditingController();
  final _executionNotesController = TextEditingController();

  List<AprStep> _steps = <AprStep>[];
  Map<String, bool> _energyChecklist = <String, bool>{};
  List<bool> _executionChecklist = <bool>[false, false, false, false];

  @override
  void initState() {
    super.initState();
    widget.controller.load(ensureLegacy: widget.stage != WorkflowStage.create);
  }

  @override
  void dispose() {
    _titleController.dispose();
    _siteController.dispose();
    _areaController.dispose();
    _contractController.dispose();
    _shiftController.dispose();
    _evaluatorController.dispose();
    _characteristicController.dispose();
    _descriptionController.dispose();
    _approverController.dispose();
    _approvalNoteController.dispose();
    _executionNotesController.dispose();
    super.dispose();
  }

  void _bind(AprDetail detail) {
    _titleController.text = detail.formFields.title;
    _siteController.text = detail.formFields.site;
    _areaController.text = detail.formFields.area;
    _contractController.text = detail.formFields.contractUnit;
    _shiftController.text = detail.formFields.shift;
    _evaluatorController.text = detail.formFields.evaluator;
    _characteristicController.text = detail.formFields.characteristic;
    _descriptionController.text = detail.formFields.description;
    _approverController.text = detail.approval.approvedBy ?? '';
    _approvalNoteController.text = detail.approval.lastComment ?? '';
    _executionNotesController.text = detail.execution.notes;
    _steps = detail.stepDrafts.isEmpty ? _defaultSteps() : detail.stepDrafts;
    _energyChecklist = detail.energyChecklist.isEmpty
        ? <String, bool>{
            'Hidraulica': false,
            'Residual': false,
            'Cinetica': false,
            'Mecanica': false,
            'Eletrica': true,
            'Gravitacional': false,
            'Termica': false,
            'Pneumatica': false,
          }
        : Map<String, bool>.from(detail.energyChecklist);
    _executionChecklist = detail.execution.checklist.isEmpty
        ? <bool>[false, false, false, false]
        : List<bool>.from(detail.execution.checklist);
  }

  Future<void> _saveBase() async {
    await widget.controller.saveBase(
      AprFormDraft(
        title: _titleController.text,
        site: _siteController.text,
        area: _areaController.text,
        contractUnit: _contractController.text,
        shift: _shiftController.text,
        evaluator: _evaluatorController.text,
        characteristic: _characteristicController.text,
        description: _descriptionController.text,
      ),
    );
  }

  Future<void> _saveControls() async {
    await widget.controller.saveControls(
      ControlsDraft(
        description: _descriptionController.text,
        technicalParameters: _energyChecklist,
        steps: _steps,
      ),
    );
  }

  Future<void> _exportPdf() async {
    final bytes = await widget.controller.exportPdf();
    if (!mounted || bytes.isEmpty) {
      return;
    }
    final directory = await getTemporaryDirectory();
    final file = File('${directory.path}\\apr-${widget.controller.aprId}.pdf');
    await file.writeAsBytes(bytes, flush: true);
    await OpenFilex.open(file.path);
  }

  @override
  Widget build(BuildContext context) {
    final user = widget.sessionController.currentUser!;
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (context, _) {
        final detail = widget.controller.state.data;
        if (detail != null) {
          _bind(detail);
        }
        return WorkspaceScaffold(
          active: ShellDestination.workflow,
          currentUser: user,
          heroEyebrow: detail?.summary.title ?? 'Workflow APR',
          heroTitle: widget.stage.title,
          heroDescription:
              'As etapas carregam dados reais, preservam o ritmo visual do Stitch e mantem retorno funcional para a proxima decisao.',
          heroActions: _heroActions(user),
          heroAside: detail == null ? null : _HeroAside(detail: detail),
          onDestinationSelected: widget.onDestinationSelected,
          onLogout: () => widget.onLogout(),
          body: widget.controller.state.loading
              ? const AppFeedbackState.inlineLoading(
                  title: 'Carregando workflow',
                  message: 'Sincronizando MVP, legado e trilha operacional.',
                )
              : widget.controller.state.error != null
              ? AppFeedbackState.inlineError(
                  title: 'Falha ao abrir a etapa',
                  message: widget.controller.state.error!,
                  actionLabel: 'Recarregar',
                  onAction: () => widget.controller.load(
                    ensureLegacy: widget.stage != WorkflowStage.create,
                  ),
                )
              : detail == null
              ? const AppFeedbackState.inlineEmpty(
                  title: 'APR indisponivel',
                  message: 'Nao foi possivel recuperar os dados da rota atual.',
                )
              : Column(
                  children: <Widget>[
                    WorkflowChrome(
                      activeStage: widget.stage,
                      status: detail.summary.status,
                      onStageTap: widget.onStageChanged,
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    _StageScaffold(
                      stage: widget.stage,
                      detail: detail,
                      titleController: _titleController,
                      siteController: _siteController,
                      areaController: _areaController,
                      contractController: _contractController,
                      shiftController: _shiftController,
                      evaluatorController: _evaluatorController,
                      characteristicController: _characteristicController,
                      descriptionController: _descriptionController,
                      approverController: _approverController,
                      approvalNoteController: _approvalNoteController,
                      executionNotesController: _executionNotesController,
                      steps: _steps,
                      energyChecklist: _energyChecklist,
                      executionChecklist: _executionChecklist,
                      onStepChanged: (index, step) =>
                          setState(() => _steps[index] = step),
                      onEnergyChanged: (key, value) =>
                          setState(() => _energyChecklist[key] = value),
                      onExecutionChanged: (index, value) =>
                          setState(() => _executionChecklist[index] = value),
                      onSaveControls: _saveControls,
                      onSubmitForApproval: () async {
                        await _saveControls();
                        await widget.controller.submitForApproval();
                        if (mounted) {
                          widget.onStageChanged(WorkflowStage.approval);
                        }
                      },
                      onApprove: () async {
                        await widget.controller.approve(
                          approver: _approverController.text.isEmpty
                              ? user.firstName
                              : _approverController.text,
                          note: _approvalNoteController.text,
                        );
                        if (mounted) {
                          widget.onStageChanged(WorkflowStage.execution);
                        }
                      },
                      onStartExecution: () => widget.controller.updateExecution(
                        startedAt: DateTime.now(),
                        checklist: _executionChecklist,
                        notes: _executionNotesController.text,
                      ),
                      onPauseExecution: () => widget.controller.updateExecution(
                        pausedAt: DateTime.now(),
                        checklist: _executionChecklist,
                        notes: _executionNotesController.text,
                      ),
                      onFinishExecution: () async {
                        await widget.controller.updateExecution(
                          finishedAt: DateTime.now(),
                          checklist: _executionChecklist,
                          notes: _executionNotesController.text,
                        );
                        if (mounted) {
                          widget.onStageChanged(WorkflowStage.report);
                        }
                      },
                      onExportPdf: _exportPdf,
                      onSharePdf: () => widget.controller.sharePdf(),
                    ),
                  ],
                ),
        );
      },
    );
  }

  List<Widget> _heroActions(AppUser user) {
    switch (widget.stage) {
      case WorkflowStage.create:
        return <Widget>[
          AppButton(
            label: 'Salvar rascunho',
            expanded: false,
            tone: AppButtonTone.secondary,
            onPressed: widget.controller.actionBusy ? null : _saveBase,
          ),
          AppButton(
            label: 'Avancar para matriz',
            expanded: false,
            onPressed: widget.controller.actionBusy
                ? null
                : () async {
                    await _saveBase();
                    if (mounted) widget.onStageChanged(WorkflowStage.controls);
                  },
          ),
        ];
      case WorkflowStage.controls:
        return <Widget>[
          AppButton(
            label: 'Salvar controles',
            expanded: false,
            onPressed: widget.controller.actionBusy ? null : _saveControls,
          ),
        ];
      case WorkflowStage.approval:
        return <Widget>[
          AppButton(
            label: 'Aprovar APR',
            expanded: false,
            tone: AppButtonTone.success,
            onPressed: widget.controller.actionBusy
                ? null
                : () async {
                    await widget.controller.approve(
                      approver: _approverController.text.isEmpty
                          ? user.firstName
                          : _approverController.text,
                      note: _approvalNoteController.text,
                    );
                    if (mounted) widget.onStageChanged(WorkflowStage.execution);
                  },
          ),
        ];
      case WorkflowStage.execution:
      case WorkflowStage.report:
        return const <Widget>[];
    }
  }

  List<AprStep> _defaultSteps() {
    return const <AprStep>[
      AprStep(
        order: 1,
        description: 'Isolamento e liberacao da frente',
        hazards: <String>['Energia residual'],
        risks: <String>['Acionamento inesperado'],
        measures: <String>['Bloqueio e etiquetagem'],
        epis: <String>['Capacete', 'Luva'],
        regulations: <String>['NR-10'],
      ),
      AprStep(
        order: 2,
        description: 'Execucao da manutencao planejada',
        hazards: <String>['Superficie quente'],
        risks: <String>['Queimadura'],
        measures: <String>['Espera de resfriamento'],
        epis: <String>['Luva termica'],
        regulations: <String>['NR-12'],
      ),
      AprStep(
        order: 3,
        description: 'Teste assistido e retomada operacional',
        hazards: <String>['Partes moveis'],
        risks: <String>['Prensagem'],
        measures: <String>['Zona isolada e checklist final'],
        epis: <String>['Oculos'],
        regulations: <String>['NR-12'],
      ),
    ];
  }
}

class _HeroAside extends StatelessWidget {
  const _HeroAside({required this.detail});

  final AprDetail detail;

  @override
  Widget build(BuildContext context) {
    return AppPanel(
      radius: 28,
      backgroundColor: AppColors.surfaceElevated,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          AppBadge(
            label: _statusLabel(detail.summary.status),
            tone: _statusTone(detail.summary.status),
          ),
          const SizedBox(height: AppSpacing.lg),
          _MetaRow(
            label: 'Atualizacao',
            value: AppFormatters.dateTime(detail.summary.updatedAt),
          ),
          _MetaRow(
            label: 'Site',
            value: detail.formFields.site.isEmpty
                ? 'Sem site'
                : detail.formFields.site,
          ),
          _MetaRow(
            label: 'Area',
            value: detail.formFields.area.isEmpty
                ? 'Sem area'
                : detail.formFields.area,
          ),
          _MetaRow(
            label: 'Risco',
            value: detail.summary.riskScore == 0
                ? 'Sem score'
                : '${detail.summary.riskScore}',
          ),
        ],
      ),
    );
  }
}

class _StageScaffold extends StatelessWidget {
  const _StageScaffold({
    required this.stage,
    required this.detail,
    required this.titleController,
    required this.siteController,
    required this.areaController,
    required this.contractController,
    required this.shiftController,
    required this.evaluatorController,
    required this.characteristicController,
    required this.descriptionController,
    required this.approverController,
    required this.approvalNoteController,
    required this.executionNotesController,
    required this.steps,
    required this.energyChecklist,
    required this.executionChecklist,
    required this.onStepChanged,
    required this.onEnergyChanged,
    required this.onExecutionChanged,
    required this.onSaveControls,
    required this.onSubmitForApproval,
    required this.onApprove,
    required this.onStartExecution,
    required this.onPauseExecution,
    required this.onFinishExecution,
    required this.onExportPdf,
    required this.onSharePdf,
  });

  final WorkflowStage stage;
  final AprDetail detail;
  final TextEditingController titleController;
  final TextEditingController siteController;
  final TextEditingController areaController;
  final TextEditingController contractController;
  final TextEditingController shiftController;
  final TextEditingController evaluatorController;
  final TextEditingController characteristicController;
  final TextEditingController descriptionController;
  final TextEditingController approverController;
  final TextEditingController approvalNoteController;
  final TextEditingController executionNotesController;
  final List<AprStep> steps;
  final Map<String, bool> energyChecklist;
  final List<bool> executionChecklist;
  final void Function(int, AprStep) onStepChanged;
  final void Function(String, bool) onEnergyChanged;
  final void Function(int, bool) onExecutionChanged;
  final Future<void> Function() onSaveControls;
  final Future<void> Function() onSubmitForApproval;
  final Future<void> Function() onApprove;
  final Future<void> Function() onStartExecution;
  final Future<void> Function() onPauseExecution;
  final Future<void> Function() onFinishExecution;
  final Future<void> Function() onExportPdf;
  final Future<void> Function() onSharePdf;

  @override
  Widget build(BuildContext context) {
    switch (stage) {
      case WorkflowStage.create:
        return _CreateStage(
          titleController: titleController,
          siteController: siteController,
          areaController: areaController,
          contractController: contractController,
          shiftController: shiftController,
          evaluatorController: evaluatorController,
          characteristicController: characteristicController,
          descriptionController: descriptionController,
        );
      case WorkflowStage.controls:
        return _ControlsStage(
          detail: detail,
          descriptionController: descriptionController,
          steps: steps,
          energyChecklist: energyChecklist,
          onStepChanged: onStepChanged,
          onEnergyChanged: onEnergyChanged,
          onSubmitForApproval: onSubmitForApproval,
        );
      case WorkflowStage.approval:
        return _ApprovalStage(
          detail: detail,
          approverController: approverController,
          approvalNoteController: approvalNoteController,
          onApprove: onApprove,
        );
      case WorkflowStage.execution:
        return _ExecutionStage(
          detail: detail,
          executionNotesController: executionNotesController,
          executionChecklist: executionChecklist,
          onExecutionChanged: onExecutionChanged,
          onStartExecution: onStartExecution,
          onPauseExecution: onPauseExecution,
          onFinishExecution: onFinishExecution,
        );
      case WorkflowStage.report:
        return _ReportStage(
          detail: detail,
          onExportPdf: onExportPdf,
          onSharePdf: onSharePdf,
        );
    }
  }
}

class _CreateStage extends StatelessWidget {
  const _CreateStage({
    required this.titleController,
    required this.siteController,
    required this.areaController,
    required this.contractController,
    required this.shiftController,
    required this.evaluatorController,
    required this.characteristicController,
    required this.descriptionController,
  });

  final TextEditingController titleController;
  final TextEditingController siteController;
  final TextEditingController areaController;
  final TextEditingController contractController;
  final TextEditingController shiftController;
  final TextEditingController evaluatorController;
  final TextEditingController characteristicController;
  final TextEditingController descriptionController;

  @override
  Widget build(BuildContext context) {
    return AppPanel(
      radius: 30,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const SectionHeader(
            eyebrow: 'Etapa 1',
            title: 'Cadastro principal da APR',
            subtitle:
                'Os blocos seguem o ritmo do Stitch para manter proporcao e leitura operacional.',
          ),
          const SizedBox(height: AppSpacing.xl),
          Row(
            children: <Widget>[
              Expanded(
                child: AppInput(
                  label: 'Titulo da APR',
                  controller: titleController,
                ),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: AppInput(label: 'Site', controller: siteController),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Row(
            children: <Widget>[
              Expanded(
                child: AppInput(
                  label: 'Area / setor',
                  controller: areaController,
                ),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: AppInput(
                  label: 'Caracteristica',
                  controller: characteristicController,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Row(
            children: <Widget>[
              Expanded(
                child: AppInput(
                  label: 'Contrato / unidade',
                  controller: contractController,
                ),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: AppInput(label: 'Turno', controller: shiftController),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          AppInput(
            label: 'Elaboradores / avaliadores',
            controller: evaluatorController,
          ),
          const SizedBox(height: AppSpacing.md),
          AppInput(
            label: 'Descricao do projeto / atividade',
            controller: descriptionController,
            minLines: 5,
            maxLines: 7,
          ),
        ],
      ),
    );
  }
}

class _ControlsStage extends StatelessWidget {
  const _ControlsStage({
    required this.detail,
    required this.descriptionController,
    required this.steps,
    required this.energyChecklist,
    required this.onStepChanged,
    required this.onEnergyChanged,
    required this.onSubmitForApproval,
  });

  final AprDetail detail;
  final TextEditingController descriptionController;
  final List<AprStep> steps;
  final Map<String, bool> energyChecklist;
  final void Function(int, AprStep) onStepChanged;
  final void Function(String, bool) onEnergyChanged;
  final Future<void> Function() onSubmitForApproval;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Expanded(
              child: AppPanel(
                radius: 30,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    const SectionHeader(
                      eyebrow: 'Descricao da atividade',
                      title: 'Contexto tecnico consolidado',
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    AppInput(
                      label: 'Resumo tecnico',
                      controller: descriptionController,
                      minLines: 5,
                      maxLines: 7,
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(width: AppSpacing.lg),
            Expanded(
              child: AppPanel(
                radius: 30,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    const SectionHeader(
                      eyebrow: 'Parametros tecnicos',
                      title: 'Energias perigosas',
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    Wrap(
                      spacing: AppSpacing.sm,
                      runSpacing: AppSpacing.sm,
                      children: energyChecklist.entries
                          .map(
                            (entry) => _ToggleChip(
                              label: entry.key,
                              selected: entry.value,
                              onTap: () =>
                                  onEnergyChanged(entry.key, !entry.value),
                            ),
                          )
                          .toList(),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.lg),
        AppPanel(
          radius: 30,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              SectionHeader(
                eyebrow: 'Passos e salvaguardas',
                title: 'Matriz operacional do trabalho',
                action: AppButton(
                  label: 'Enviar para aprovacao',
                  expanded: false,
                  onPressed: onSubmitForApproval,
                ),
              ),
              const SizedBox(height: AppSpacing.lg),
              ...List.generate(
                steps.length,
                (index) => _StepCard(
                  step: steps[index],
                  onChanged: (step) => onStepChanged(index, step),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _StepCard extends StatelessWidget {
  const _StepCard({required this.step, required this.onChanged});

  final AprStep step;
  final ValueChanged<AprStep> onChanged;

  @override
  Widget build(BuildContext context) {
    final controller = TextEditingController(text: step.description);
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.md),
      child: AppPanel(
        backgroundColor: AppColors.surfaceElevated,
        radius: 24,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Passo ${step.order.toString().padLeft(2, '0')}',
              style: Theme.of(
                context,
              ).textTheme.labelLarge?.copyWith(color: AppColors.textSoft),
            ),
            const SizedBox(height: AppSpacing.sm),
            AppInput(
              label: 'Descricao',
              controller: controller,
              minLines: 2,
              maxLines: 3,
              onSubmitted: (_) => onChanged(
                AprStep(
                  id: step.id,
                  order: step.order,
                  description: controller.text,
                  hazards: step.hazards,
                  risks: step.risks,
                  measures: step.measures,
                  epis: step.epis,
                  regulations: step.regulations,
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.md),
            Wrap(
              spacing: AppSpacing.sm,
              runSpacing: AppSpacing.sm,
              children: <Widget>[
                ...step.hazards.map(
                  (item) => AppBadge(label: item, tone: AppBadgeTone.warning),
                ),
                ...step.measures.map(
                  (item) => AppBadge(label: item, tone: AppBadgeTone.success),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _ToggleChip extends StatelessWidget {
  const _ToggleChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: selected ? AppColors.primarySoft : AppColors.surfaceElevated,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
            color: selected
                ? AppColors.primary.withValues(alpha: 0.3)
                : AppColors.border,
          ),
        ),
        child: Text(
          label,
          style: Theme.of(context).textTheme.labelMedium?.copyWith(
            color: selected ? AppColors.primaryDeep : AppColors.textSoft,
          ),
        ),
      ),
    );
  }
}

class _ApprovalStage extends StatelessWidget {
  const _ApprovalStage({
    required this.detail,
    required this.approverController,
    required this.approvalNoteController,
    required this.onApprove,
  });

  final AprDetail detail;
  final TextEditingController approverController;
  final TextEditingController approvalNoteController;
  final Future<void> Function() onApprove;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        AppPanel(
          radius: 30,
          backgroundColor: AppColors.primarySoft,
          borderColor: Colors.transparent,
          child: Row(
            children: <Widget>[
              const Icon(
                Icons.verified_user_rounded,
                color: AppColors.primaryDeep,
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Text(
                  'Parecer pronto para aprovacao formal com base tecnica, matriz e trilha do responsavel.',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: AppColors.primaryDeep,
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Expanded(
              child: AppPanel(
                radius: 30,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    const SectionHeader(
                      eyebrow: 'Resumo tecnico',
                      title: 'Pontos-chave para decisao',
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    _MetaRow(label: 'Titulo', value: detail.summary.title),
                    _MetaRow(
                      label: 'Responsavel',
                      value: detail.formFields.evaluator.isEmpty
                          ? 'Sem responsavel'
                          : detail.formFields.evaluator,
                    ),
                    _MetaRow(
                      label: 'Etapas',
                      value: '${detail.stepDrafts.length} passos estruturados',
                    ),
                    _MetaRow(
                      label: 'Risco maximo',
                      value: detail.summary.riskScore == 0
                          ? 'Nao calculado'
                          : '${detail.summary.riskScore}',
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(width: AppSpacing.lg),
            Expanded(
              child: AppPanel(
                radius: 30,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    const SectionHeader(
                      eyebrow: 'Aprovador',
                      title: 'Decisao e comentario',
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    AppInput(
                      label: 'Nome do aprovador',
                      controller: approverController,
                      hint: 'Coordenacao tecnica',
                    ),
                    const SizedBox(height: AppSpacing.md),
                    AppInput(
                      label: 'Comentario',
                      controller: approvalNoteController,
                      minLines: 4,
                      maxLines: 5,
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    AppButton(label: 'Aprovar APR', onPressed: onApprove),
                  ],
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _ExecutionStage extends StatelessWidget {
  const _ExecutionStage({
    required this.detail,
    required this.executionNotesController,
    required this.executionChecklist,
    required this.onExecutionChanged,
    required this.onStartExecution,
    required this.onPauseExecution,
    required this.onFinishExecution,
  });

  final AprDetail detail;
  final TextEditingController executionNotesController;
  final List<bool> executionChecklist;
  final void Function(int, bool) onExecutionChanged;
  final Future<void> Function() onStartExecution;
  final Future<void> Function() onPauseExecution;
  final Future<void> Function() onFinishExecution;

  @override
  Widget build(BuildContext context) {
    const labels = <String>[
      'Equipe alinhada e liberada',
      'Bloqueios verificados antes da intervencao',
      'EPI e permissao validados',
      'Retomada segura confirmada',
    ];
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Expanded(
          flex: 7,
          child: AppPanel(
            radius: 30,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                const SectionHeader(
                  eyebrow: 'Checklist operacional',
                  title: 'Execucao assistida',
                ),
                const SizedBox(height: AppSpacing.lg),
                ...List.generate(
                  labels.length,
                  (index) => Padding(
                    padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                    child: _ExecutionItem(
                      label: labels[index],
                      selected: executionChecklist[index],
                      onTap: () =>
                          onExecutionChanged(index, !executionChecklist[index]),
                    ),
                  ),
                ),
                const SizedBox(height: AppSpacing.md),
                AppInput(
                  label: 'Notas de execucao',
                  controller: executionNotesController,
                  minLines: 5,
                  maxLines: 6,
                ),
                const SizedBox(height: AppSpacing.lg),
                Wrap(
                  spacing: AppSpacing.md,
                  runSpacing: AppSpacing.md,
                  children: <Widget>[
                    AppButton(
                      label: 'Iniciar execucao',
                      expanded: false,
                      onPressed: onStartExecution,
                    ),
                    AppButton(
                      label: 'Pausar',
                      expanded: false,
                      tone: AppButtonTone.secondary,
                      onPressed: onPauseExecution,
                    ),
                    AppButton(
                      label: 'Finalizar execucao',
                      expanded: false,
                      tone: AppButtonTone.success,
                      onPressed: onFinishExecution,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
        const SizedBox(width: AppSpacing.lg),
        Expanded(
          flex: 4,
          child: AppPanel(
            radius: 30,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                const SectionHeader(
                  eyebrow: 'Estado atual',
                  title: 'Resumo da frente',
                ),
                const SizedBox(height: AppSpacing.lg),
                _MetaRow(
                  label: 'Inicio',
                  value: AppFormatters.dateTime(detail.execution.startedAt),
                ),
                _MetaRow(
                  label: 'Pausa',
                  value: AppFormatters.dateTime(detail.execution.pausedAt),
                ),
                _MetaRow(
                  label: 'Finalizacao',
                  value: AppFormatters.dateTime(detail.execution.finishedAt),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _ExecutionItem extends StatelessWidget {
  const _ExecutionItem({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          color: selected ? AppColors.primarySoft : AppColors.surfaceElevated,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: selected
                ? AppColors.primary.withValues(alpha: 0.28)
                : AppColors.border,
          ),
        ),
        child: Row(
          children: <Widget>[
            AnimatedContainer(
              duration: const Duration(milliseconds: 160),
              width: 22,
              height: 22,
              decoration: BoxDecoration(
                color: selected ? AppColors.primary : Colors.white,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: selected ? AppColors.primary : AppColors.borderStrong,
                ),
              ),
              child: selected
                  ? const Icon(
                      Icons.check_rounded,
                      size: 16,
                      color: Colors.white,
                    )
                  : null,
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Text(label, style: Theme.of(context).textTheme.titleSmall),
            ),
          ],
        ),
      ),
    );
  }
}

class _ReportStage extends StatelessWidget {
  const _ReportStage({
    required this.detail,
    required this.onExportPdf,
    required this.onSharePdf,
  });

  final AprDetail detail;
  final Future<void> Function() onExportPdf;
  final Future<void> Function() onSharePdf;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Expanded(
          flex: 7,
          child: AppPanel(
            radius: 30,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                const SectionHeader(
                  eyebrow: 'Resumo consolidado',
                  title: 'Base final da APR',
                ),
                const SizedBox(height: AppSpacing.lg),
                Text(
                  detail.summary.title,
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: AppSpacing.sm),
                Text(
                  detail.description.isEmpty
                      ? 'Sem descricao consolidada.'
                      : detail.description,
                  style: Theme.of(
                    context,
                  ).textTheme.bodyMedium?.copyWith(color: AppColors.textSoft),
                ),
                const SizedBox(height: AppSpacing.xl),
                Wrap(
                  spacing: AppSpacing.sm,
                  runSpacing: AppSpacing.sm,
                  children: detail.stepDrafts
                      .expand((step) => step.measures)
                      .take(6)
                      .map(
                        (item) =>
                            AppBadge(label: item, tone: AppBadgeTone.success),
                      )
                      .toList(),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(width: AppSpacing.lg),
        Expanded(
          flex: 4,
          child: AppPanel(
            radius: 30,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                const SectionHeader(
                  eyebrow: 'Distribuicao',
                  title: 'Saidas de fechamento',
                ),
                const SizedBox(height: AppSpacing.lg),
                AppButton(label: 'Exportar PDF', onPressed: onExportPdf),
                const SizedBox(height: AppSpacing.sm),
                AppButton(
                  label: 'Compartilhar',
                  tone: AppButtonTone.secondary,
                  onPressed: onSharePdf,
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _MetaRow extends StatelessWidget {
  const _MetaRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          SizedBox(
            width: 110,
            child: Text(
              label,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: AppColors.textMuted),
            ),
          ),
          Expanded(
            child: Text(value, style: Theme.of(context).textTheme.titleSmall),
          ),
        ],
      ),
    );
  }
}

String _statusLabel(AprStatus status) {
  switch (status) {
    case AprStatus.submitted:
      return 'Em aprovacao';
    case AprStatus.approved:
      return 'Aprovada';
    case AprStatus.inProgress:
      return 'Em execucao';
    case AprStatus.paused:
      return 'Pausada';
    case AprStatus.finished:
      return 'Finalizada';
    case AprStatus.archived:
      return 'Arquivada';
    case AprStatus.rejected:
      return 'Reprovada';
    default:
      return 'Rascunho';
  }
}

AppBadgeTone _statusTone(AprStatus status) {
  switch (status) {
    case AprStatus.submitted:
      return AppBadgeTone.warning;
    case AprStatus.approved:
    case AprStatus.finished:
      return AppBadgeTone.success;
    case AprStatus.rejected:
      return AppBadgeTone.danger;
    default:
      return AppBadgeTone.info;
  }
}

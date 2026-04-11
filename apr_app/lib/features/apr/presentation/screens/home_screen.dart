import 'package:flutter/material.dart';

import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_spacing.dart';
import '../../../../core/utils/app_formatters.dart';
import '../../../../shared/widgets/app_badge.dart';
import '../../../../shared/widgets/app_button.dart';
import '../../../../shared/widgets/app_feedback_state.dart';
import '../../../../shared/widgets/app_panel.dart';
import '../../../../shared/widgets/section_header.dart';
import '../../../auth/presentation/controllers/session_controller.dart';
import '../../domain/entities/apr_models.dart';
import '../controllers/home_controller.dart';
import '../widgets/metric_card.dart';
import '../widgets/workspace_scaffold.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({
    super.key,
    required this.controller,
    required this.sessionController,
    required this.onDestinationSelected,
    required this.onOpenApr,
    required this.onLogout,
  });

  final HomeController controller;
  final SessionController sessionController;
  final ValueChanged<ShellDestination> onDestinationSelected;
  final ValueChanged<AprSummary> onOpenApr;
  final Future<void> Function() onLogout;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    widget.controller.load();
  }

  @override
  Widget build(BuildContext context) {
    final user = widget.sessionController.currentUser!;
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (context, _) {
        final payload = widget.controller.state.data;
        final items = payload?.items ?? const <AprSummary>[];
        final analytics = payload?.analytics;
        return WorkspaceScaffold(
          active: ShellDestination.home,
          currentUser: user,
          heroEyebrow: 'Painel APR Corporativo',
          heroTitle: 'Operacao enxuta, rastreavel e pronta para decisao.',
          heroDescription:
              'A fila operacional, a biblioteca de APRs e o workflow tecnico ficam no mesmo pulso. O frontend reflete o Stitch com fluxo real entre cadastro, matriz, aprovacao, execucao e relatorio.',
          heroActions: <Widget>[
            AppButton(
              label: 'Criar nova APR',
              icon: Icons.add_rounded,
              expanded: false,
              onPressed: () =>
                  widget.onDestinationSelected(ShellDestination.newApr),
            ),
            AppButton(
              label: 'Abrir biblioteca',
              tone: AppButtonTone.secondary,
              expanded: false,
              onPressed: () =>
                  widget.onDestinationSelected(ShellDestination.library),
            ),
          ],
          heroAside: AppPanel(
            radius: 28,
            backgroundColor: AppColors.surfaceElevated,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                const AppBadge(
                  label: 'Resumo operacional',
                  tone: AppBadgeTone.success,
                ),
                const SizedBox(height: AppSpacing.lg),
                Text(
                  'Leitura rapida',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: AppSpacing.sm),
                Text(
                  analytics == null
                      ? 'Sem consolidado no momento.'
                      : '${analytics.inApproval} APRs em decisao, ${analytics.inExecution} em campo e ${analytics.highRisk} com criticidade alta.',
                  style: Theme.of(
                    context,
                  ).textTheme.bodyMedium?.copyWith(color: AppColors.textSoft),
                ),
                const SizedBox(height: AppSpacing.xl),
                _SummaryLine(
                  label: 'Empresa',
                  value: user.companyName ?? 'Sem empresa',
                ),
                _SummaryLine(label: 'Perfil', value: user.role),
                _SummaryLine(
                  label: 'Atualizacao',
                  value: AppFormatters.dateTime(
                    items.isEmpty ? null : items.first.updatedAt,
                  ),
                ),
              ],
            ),
          ),
          metrics: analytics == null
              ? const <Widget>[]
              : <Widget>[
                  SizedBox(
                    width: 240,
                    child: MetricCard(
                      label: 'APRs ativas',
                      value: analytics.total.toString(),
                      detail: '${analytics.draft} em rascunho',
                    ),
                  ),
                  SizedBox(
                    width: 240,
                    child: MetricCard(
                      label: 'Em aprovacao',
                      value: analytics.inApproval.toString(),
                      detail: 'Fluxo pronto para decisao',
                      tone: AppBadgeTone.warning,
                    ),
                  ),
                  SizedBox(
                    width: 240,
                    child: MetricCard(
                      label: 'Em execucao',
                      value: analytics.inExecution.toString(),
                      detail: 'Operacoes monitoradas',
                      tone: AppBadgeTone.success,
                    ),
                  ),
                  SizedBox(
                    width: 240,
                    child: MetricCard(
                      label: 'Risco medio',
                      value: analytics.avgScore.toStringAsFixed(1),
                      detail: '${analytics.highRisk} acima do limite',
                      tone: AppBadgeTone.danger,
                    ),
                  ),
                ],
          onDestinationSelected: widget.onDestinationSelected,
          onLogout: () => widget.onLogout(),
          body: widget.controller.state.loading
              ? const AppFeedbackState.inlineLoading(
                  title: 'Carregando visao operacional',
                  message: 'Sincronizando APRs, status e sinais do backend.',
                )
              : widget.controller.state.error != null
              ? AppFeedbackState.inlineError(
                  title: 'Falha ao montar o painel',
                  message: widget.controller.state.error!,
                  actionLabel: 'Tentar de novo',
                  onAction: widget.controller.load,
                )
              : items.isEmpty
              ? AppFeedbackState.inlineEmpty(
                  title: 'Nenhuma APR criada ainda',
                  message:
                      'Abra o cadastro guiado e comece um fluxo completo de APR.',
                  actionLabel: 'Criar agora',
                  onAction: () =>
                      widget.onDestinationSelected(ShellDestination.newApr),
                )
              : _HomeBody(items: items, onOpenApr: widget.onOpenApr),
        );
      },
    );
  }
}

class _HomeBody extends StatelessWidget {
  const _HomeBody({required this.items, required this.onOpenApr});

  final List<AprSummary> items;
  final ValueChanged<AprSummary> onOpenApr;

  @override
  Widget build(BuildContext context) {
    final focus = items.take(3).toList();
    final queue = items.skip(3).take(4).toList();
    return Column(
      children: <Widget>[
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Expanded(
              flex: 8,
              child: AppPanel(
                radius: 30,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    const SectionHeader(
                      eyebrow: 'Central de execucao da APR',
                      title: 'Acompanhamento vivo das frentes prioritarias',
                      subtitle:
                          'Os cards assumem densidade maior para refletir criticidade, etapa e ultima movimentacao.',
                    ),
                    const SizedBox(height: AppSpacing.xl),
                    Wrap(
                      spacing: AppSpacing.lg,
                      runSpacing: AppSpacing.lg,
                      children: focus
                          .map(
                            (apr) => SizedBox(
                              width: 320,
                              child: _AprFocusCard(
                                apr: apr,
                                onTap: () => onOpenApr(apr),
                              ),
                            ),
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
                      eyebrow: 'Fila tecnica',
                      title: 'Sequencia de decisao',
                      subtitle:
                          'Ordem sugerida pela criticidade e pelo estado atual.',
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    ...queue.map(
                      (item) =>
                          _QueueRow(apr: item, onTap: () => onOpenApr(item)),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.lg),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Expanded(
              child: AppPanel(
                radius: 28,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    const SectionHeader(
                      eyebrow: 'Roteiro do fluxo',
                      title: 'De cadastro a relatorio',
                      subtitle:
                          'Cada etapa vira rota real e retorna ao contexto anterior sem telas soltas.',
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    Wrap(
                      spacing: AppSpacing.md,
                      runSpacing: AppSpacing.md,
                      children: WorkflowStage.values
                          .map(
                            (stage) => Container(
                              width: 190,
                              padding: const EdgeInsets.all(AppSpacing.md),
                              decoration: BoxDecoration(
                                color: AppColors.surfaceElevated,
                                borderRadius: BorderRadius.circular(20),
                                border: Border.all(color: AppColors.border),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: <Widget>[
                                  Text(
                                    '${stage.index + 1}'.padLeft(2, '0'),
                                    style: Theme.of(context)
                                        .textTheme
                                        .labelMedium
                                        ?.copyWith(color: AppColors.textMuted),
                                  ),
                                  const SizedBox(height: AppSpacing.xs),
                                  Text(
                                    stage.label,
                                    style: Theme.of(
                                      context,
                                    ).textTheme.titleSmall,
                                  ),
                                ],
                              ),
                            ),
                          )
                          .toList(),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(width: AppSpacing.lg),
            Expanded(
              child: AppPanel(
                radius: 28,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    const SectionHeader(
                      eyebrow: 'Radar de evidencia',
                      title: 'Sinais para decisao rapida',
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    ...items
                        .take(4)
                        .map(
                          (item) => Padding(
                            padding: const EdgeInsets.only(
                              bottom: AppSpacing.md,
                            ),
                            child: Row(
                              children: <Widget>[
                                Expanded(
                                  child: Text(
                                    item.title,
                                    style: Theme.of(
                                      context,
                                    ).textTheme.titleSmall,
                                  ),
                                ),
                                const SizedBox(width: AppSpacing.md),
                                AppBadge(
                                  label: item.riskScore == 0
                                      ? 'Sem matriz'
                                      : 'Score ${item.riskScore}',
                                  tone: item.riskScore >= 15
                                      ? AppBadgeTone.danger
                                      : AppBadgeTone.info,
                                ),
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
      ],
    );
  }
}

class _AprFocusCard extends StatelessWidget {
  const _AprFocusCard({required this.apr, required this.onTap});

  final AprSummary apr;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AppPanel(
        radius: 26,
        backgroundColor: apr.riskScore >= 15
            ? const Color(0xFFFFF2F4)
            : AppColors.surfaceElevated,
        borderColor: apr.riskScore >= 15
            ? AppColors.danger.withValues(alpha: 0.26)
            : AppColors.border,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              children: <Widget>[
                AppBadge(
                  label: _statusLabel(apr.status),
                  tone: _statusTone(apr.status),
                ),
                const Spacer(),
                Text(
                  AppFormatters.date(apr.updatedAt),
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: AppColors.textMuted),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.lg),
            Text(apr.title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: AppSpacing.sm),
            Text(
              apr.activity ?? apr.location ?? 'Sem resumo operacional',
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: AppColors.textSoft),
            ),
            const SizedBox(height: AppSpacing.lg),
            Row(
              children: <Widget>[
                Expanded(
                  child: _MiniStat(
                    label: 'Risco',
                    value: apr.riskScore == 0 ? '—' : '${apr.riskScore}',
                  ),
                ),
                Expanded(
                  child: _MiniStat(
                    label: 'Progresso',
                    value: AppFormatters.percent(apr.progress * 100),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _QueueRow extends StatelessWidget {
  const _QueueRow({required this.apr, required this.onTap});

  final AprSummary apr;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: AppSpacing.sm),
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          color: AppColors.surfaceElevated,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: AppColors.border),
        ),
        child: Row(
          children: <Widget>[
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    apr.title,
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                  const SizedBox(height: AppSpacing.xxs),
                  Text(
                    apr.location ?? 'Sem local definido',
                    style: Theme.of(
                      context,
                    ).textTheme.bodySmall?.copyWith(color: AppColors.textMuted),
                  ),
                ],
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            AppBadge(
              label: _statusLabel(apr.status),
              tone: _statusTone(apr.status),
            ),
          ],
        ),
      ),
    );
  }
}

class _MiniStat extends StatelessWidget {
  const _MiniStat({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          label,
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: AppColors.textMuted),
        ),
        const SizedBox(height: AppSpacing.xxs),
        Text(value, style: Theme.of(context).textTheme.titleSmall),
      ],
    );
  }
}

class _SummaryLine extends StatelessWidget {
  const _SummaryLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Text(
              label,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: AppColors.textMuted),
            ),
          ),
          Text(value, style: Theme.of(context).textTheme.titleSmall),
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

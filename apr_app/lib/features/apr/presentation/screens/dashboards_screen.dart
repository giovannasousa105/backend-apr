import 'package:flutter/material.dart';

import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_spacing.dart';
import '../../../../core/utils/app_formatters.dart';
import '../../../../shared/widgets/app_badge.dart';
import '../../../../shared/widgets/app_feedback_state.dart';
import '../../../../shared/widgets/app_panel.dart';
import '../../../../shared/widgets/section_header.dart';
import '../../../auth/presentation/controllers/session_controller.dart';
import '../../domain/entities/apr_models.dart';
import '../controllers/dashboard_controller.dart';
import '../widgets/metric_card.dart';
import '../widgets/workspace_scaffold.dart';

class RiskDashboardScreen extends StatefulWidget {
  const RiskDashboardScreen({
    super.key,
    required this.controller,
    required this.sessionController,
    required this.onDestinationSelected,
    required this.onLogout,
  });

  final DashboardController controller;
  final SessionController sessionController;
  final ValueChanged<ShellDestination> onDestinationSelected;
  final Future<void> Function() onLogout;

  @override
  State<RiskDashboardScreen> createState() => _RiskDashboardScreenState();
}

class _RiskDashboardScreenState extends State<RiskDashboardScreen> {
  @override
  void initState() {
    super.initState();
    widget.controller.load();
  }

  @override
  Widget build(BuildContext context) {
    return _DashboardShell(
      title: 'Dashboard de risco com leitura priorizada e sinais operacionais.',
      eyebrow: 'Risk Dashboard',
      description:
          'A camada visual deixa de ser placeholder e vira mapa acionavel com distribuicao de criticidade e APRs mais expostas.',
      active: ShellDestination.risk,
      controller: widget.controller,
      sessionController: widget.sessionController,
      onDestinationSelected: widget.onDestinationSelected,
      onLogout: widget.onLogout,
      builder: (payload) => _RiskBody(payload: payload),
    );
  }
}

class ExecutiveDashboardScreen extends StatefulWidget {
  const ExecutiveDashboardScreen({
    super.key,
    required this.controller,
    required this.sessionController,
    required this.onDestinationSelected,
    required this.onLogout,
  });

  final DashboardController controller;
  final SessionController sessionController;
  final ValueChanged<ShellDestination> onDestinationSelected;
  final Future<void> Function() onLogout;

  @override
  State<ExecutiveDashboardScreen> createState() =>
      _ExecutiveDashboardScreenState();
}

class _ExecutiveDashboardScreenState extends State<ExecutiveDashboardScreen> {
  @override
  void initState() {
    super.initState();
    widget.controller.load();
  }

  @override
  Widget build(BuildContext context) {
    return _DashboardShell(
      title: 'Leitura executiva consolidada, direta e pronta para priorizacao.',
      eyebrow: 'Executive Dashboard',
      description:
          'KPIs, carteira ativa e criticidade agregada em composicao premium, sem blocos pesados e sem cara de admin template.',
      active: ShellDestination.executive,
      controller: widget.controller,
      sessionController: widget.sessionController,
      onDestinationSelected: widget.onDestinationSelected,
      onLogout: widget.onLogout,
      builder: (payload) => _ExecutiveBody(payload: payload),
    );
  }
}

class _DashboardShell extends StatelessWidget {
  const _DashboardShell({
    required this.title,
    required this.eyebrow,
    required this.description,
    required this.active,
    required this.controller,
    required this.sessionController,
    required this.onDestinationSelected,
    required this.onLogout,
    required this.builder,
  });

  final String title;
  final String eyebrow;
  final String description;
  final ShellDestination active;
  final DashboardController controller;
  final SessionController sessionController;
  final ValueChanged<ShellDestination> onDestinationSelected;
  final Future<void> Function() onLogout;
  final Widget Function(DashboardPayload payload) builder;

  @override
  Widget build(BuildContext context) {
    final user = sessionController.currentUser!;
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        final payload = controller.state.data;
        return WorkspaceScaffold(
          active: active,
          currentUser: user,
          heroEyebrow: eyebrow,
          heroTitle: title,
          heroDescription: description,
          metrics: payload == null
              ? const <Widget>[]
              : <Widget>[
                  SizedBox(
                    width: 230,
                    child: MetricCard(
                      label: 'Total APRs',
                      value: payload.analytics.total.toString(),
                      detail: 'Base corporativa',
                    ),
                  ),
                  SizedBox(
                    width: 230,
                    child: MetricCard(
                      label: 'Risco alto',
                      value: payload.analytics.highRisk.toString(),
                      detail: 'Acima do limiar',
                      tone: AppBadgeTone.danger,
                    ),
                  ),
                  SizedBox(
                    width: 230,
                    child: MetricCard(
                      label: 'Em execucao',
                      value: payload.analytics.inExecution.toString(),
                      detail: 'Monitoramento ativo',
                      tone: AppBadgeTone.success,
                    ),
                  ),
                ],
          onDestinationSelected: onDestinationSelected,
          onLogout: () => onLogout(),
          body: controller.state.loading
              ? const AppFeedbackState.inlineLoading(
                  title: 'Carregando indicadores',
                  message: 'Consolidando carteira e criticidade.',
                )
              : controller.state.error != null
              ? AppFeedbackState.inlineError(
                  title: 'Falha ao consolidar dashboard',
                  message: controller.state.error!,
                  actionLabel: 'Recarregar',
                  onAction: controller.load,
                )
              : payload == null
              ? const AppFeedbackState.inlineEmpty(
                  title: 'Sem dados para exibir',
                  message: 'A carteira ainda nao tem APRs suficientes.',
                )
              : builder(payload),
        );
      },
    );
  }
}

class _RiskBody extends StatelessWidget {
  const _RiskBody({required this.payload});

  final DashboardPayload payload;

  @override
  Widget build(BuildContext context) {
    final buckets = <String, int>{
      'Baixo': 0,
      'Moderado': 0,
      'Alto': 0,
      'Critico': 0,
    };
    for (final item in payload.items) {
      if (item.riskScore >= 20) {
        buckets['Critico'] = buckets['Critico']! + 1;
      } else if (item.riskScore >= 15) {
        buckets['Alto'] = buckets['Alto']! + 1;
      } else if (item.riskScore >= 8) {
        buckets['Moderado'] = buckets['Moderado']! + 1;
      } else {
        buckets['Baixo'] = buckets['Baixo']! + 1;
      }
    }
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
                  eyebrow: 'Mapa de criticidade',
                  title: 'Distribuicao por faixa de risco',
                ),
                const SizedBox(height: AppSpacing.lg),
                Row(
                  children: buckets.entries
                      .map(
                        (entry) => Expanded(
                          child: _RiskBucket(
                            label: entry.key,
                            count: entry.value,
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
          flex: 5,
          child: AppPanel(
            radius: 30,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                const SectionHeader(
                  eyebrow: 'Fila exposta',
                  title: 'APRs com maior score',
                ),
                const SizedBox(height: AppSpacing.lg),
                ...payload.items
                    .where((item) => item.riskScore > 0)
                    .take(5)
                    .map((item) => _ExposureRow(item: item)),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _ExecutiveBody extends StatelessWidget {
  const _ExecutiveBody({required this.payload});

  final DashboardPayload payload;

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
                  eyebrow: 'Carteira ativa',
                  title: 'Visao executiva das APRs',
                ),
                const SizedBox(height: AppSpacing.lg),
                ...payload.items
                    .take(6)
                    .map(
                      (item) => Padding(
                        padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                        child: Row(
                          children: <Widget>[
                            Expanded(
                              child: Text(
                                item.title,
                                style: Theme.of(context).textTheme.titleSmall,
                              ),
                            ),
                            Text(
                              AppFormatters.date(item.updatedAt),
                              style: Theme.of(context).textTheme.bodySmall
                                  ?.copyWith(color: AppColors.textMuted),
                            ),
                          ],
                        ),
                      ),
                    ),
              ],
            ),
          ),
        ),
        const SizedBox(width: AppSpacing.lg),
        Expanded(
          flex: 5,
          child: AppPanel(
            radius: 30,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                const SectionHeader(
                  eyebrow: 'Sinais chave',
                  title: 'Leitura direta para gestao',
                ),
                const SizedBox(height: AppSpacing.lg),
                _SignalRow(
                  label: 'Finalizadas',
                  value: payload.analytics.finished.toString(),
                ),
                _SignalRow(
                  label: 'Em aprovacao',
                  value: payload.analytics.inApproval.toString(),
                ),
                _SignalRow(
                  label: 'Risco medio',
                  value: payload.analytics.avgScore.toStringAsFixed(1),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _RiskBucket extends StatelessWidget {
  const _RiskBucket({required this.label, required this.count});

  final String label;
  final int count;

  @override
  Widget build(BuildContext context) {
    final color = switch (label) {
      'Critico' => AppColors.danger,
      'Alto' => AppColors.warning,
      'Moderado' => AppColors.info,
      _ => AppColors.success,
    };
    return Container(
      margin: const EdgeInsets.only(right: AppSpacing.sm),
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            label,
            style: Theme.of(
              context,
            ).textTheme.labelLarge?.copyWith(color: color),
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(
            count.toString(),
            style: Theme.of(context).textTheme.headlineMedium,
          ),
        ],
      ),
    );
  }
}

class _ExposureRow extends StatelessWidget {
  const _ExposureRow({required this.item});

  final AprSummary item;

  @override
  Widget build(BuildContext context) {
    return Container(
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
            child: Text(
              item.title,
              style: Theme.of(context).textTheme.titleSmall,
            ),
          ),
          AppBadge(
            label: 'Score ${item.riskScore}',
            tone: item.riskScore >= 15
                ? AppBadgeTone.danger
                : AppBadgeTone.warning,
          ),
        ],
      ),
    );
  }
}

class _SignalRow extends StatelessWidget {
  const _SignalRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.md),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Text(
              label,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: AppColors.textSoft),
            ),
          ),
          Text(value, style: Theme.of(context).textTheme.titleLarge),
        ],
      ),
    );
  }
}

import 'package:flutter/material.dart';

import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_spacing.dart';
import '../../../../core/utils/app_formatters.dart';
import '../../../../shared/widgets/app_badge.dart';
import '../../../../shared/widgets/app_feedback_state.dart';
import '../../../../shared/widgets/app_input.dart';
import '../../../../shared/widgets/app_panel.dart';
import '../../../../shared/widgets/section_header.dart';
import '../../../auth/presentation/controllers/session_controller.dart';
import '../../domain/entities/apr_models.dart';
import '../controllers/library_controller.dart';
import '../widgets/workspace_scaffold.dart';

class LibraryScreen extends StatefulWidget {
  const LibraryScreen({
    super.key,
    required this.controller,
    required this.sessionController,
    required this.onDestinationSelected,
    required this.onOpenApr,
    required this.onLogout,
  });

  final LibraryController controller;
  final SessionController sessionController;
  final ValueChanged<ShellDestination> onDestinationSelected;
  final ValueChanged<AprSummary> onOpenApr;
  final Future<void> Function() onLogout;

  @override
  State<LibraryScreen> createState() => _LibraryScreenState();
}

class _LibraryScreenState extends State<LibraryScreen> {
  final _queryController = TextEditingController();

  @override
  void initState() {
    super.initState();
    widget.controller.load();
  }

  @override
  void dispose() {
    _queryController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final user = widget.sessionController.currentUser!;
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (context, _) {
        final items = widget.controller.filteredItems;
        return WorkspaceScaffold(
          active: ShellDestination.library,
          currentUser: user,
          heroEyebrow: 'Biblioteca APR',
          heroTitle: 'Gestao refinada de APRs, atalhos e trilhas documentais.',
          heroDescription:
              'A biblioteca organiza filtros, historico e acesso direto ao fluxo. Nada de tabela genérica solta: o grid respeita o ritmo visual do Stitch.',
          heroAside: AppPanel(
            radius: 28,
            backgroundColor: AppColors.surfaceElevated,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                const AppBadge(
                  label: 'Pesquisa operacional',
                  tone: AppBadgeTone.info,
                ),
                const SizedBox(height: AppSpacing.lg),
                Text(
                  'Recortes rapidos',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: AppSpacing.sm),
                Text(
                  'Filtre por termo, estado e abra a APR direto no passo certo.',
                  style: Theme.of(
                    context,
                  ).textTheme.bodyMedium?.copyWith(color: AppColors.textSoft),
                ),
              ],
            ),
          ),
          onDestinationSelected: widget.onDestinationSelected,
          onLogout: () => widget.onLogout(),
          body: widget.controller.state.loading
              ? const AppFeedbackState.inlineLoading(
                  title: 'Carregando biblioteca',
                  message: 'Buscando APRs e consolidando o indice operacional.',
                )
              : widget.controller.state.error != null
              ? AppFeedbackState.inlineError(
                  title: 'Falha ao carregar a biblioteca',
                  message: widget.controller.state.error!,
                  actionLabel: 'Tentar novamente',
                  onAction: widget.controller.load,
                )
              : Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    SizedBox(
                      width: 320,
                      child: AppPanel(
                        radius: 30,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            const SectionHeader(
                              eyebrow: 'Filtros',
                              title: 'Curadoria de busca',
                            ),
                            const SizedBox(height: AppSpacing.lg),
                            AppInput(
                              label: 'Buscar APR',
                              controller: _queryController,
                              hint: 'Titulo, local ou resumo',
                              onSubmitted: widget.controller.setQuery,
                              onChanged: widget.controller.setQuery,
                            ),
                            const SizedBox(height: AppSpacing.lg),
                            Wrap(
                              spacing: AppSpacing.sm,
                              runSpacing: AppSpacing.sm,
                              children: <Widget>[
                                _FilterChip(
                                  label: 'Todas',
                                  selected: widget.controller.filter == null,
                                  onTap: () =>
                                      widget.controller.setFilter(null),
                                ),
                                _FilterChip(
                                  label: 'Rascunho',
                                  selected:
                                      widget.controller.filter ==
                                      AprStatus.draft,
                                  onTap: () => widget.controller.setFilter(
                                    AprStatus.draft,
                                  ),
                                ),
                                _FilterChip(
                                  label: 'Aprovacao',
                                  selected:
                                      widget.controller.filter ==
                                      AprStatus.submitted,
                                  onTap: () => widget.controller.setFilter(
                                    AprStatus.submitted,
                                  ),
                                ),
                                _FilterChip(
                                  label: 'Execucao',
                                  selected:
                                      widget.controller.filter ==
                                      AprStatus.inProgress,
                                  onTap: () => widget.controller.setFilter(
                                    AprStatus.inProgress,
                                  ),
                                ),
                              ],
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
                              eyebrow: 'Indice operacional',
                              title: 'APRs recentes e trilha documental',
                            ),
                            const SizedBox(height: AppSpacing.lg),
                            if (items.isEmpty)
                              AppFeedbackState.inlineEmpty(
                                title: 'Nenhum resultado para o filtro atual',
                                message:
                                    'Ajuste os recortes ou crie uma nova APR.',
                                actionLabel: 'Nova APR',
                                onAction: () => widget.onDestinationSelected(
                                  ShellDestination.newApr,
                                ),
                              )
                            else
                              ...items.map(
                                (item) => _LibraryRow(
                                  apr: item,
                                  onTap: () => widget.onOpenApr(item),
                                ),
                              ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
        );
      },
    );
  }
}

class _LibraryRow extends StatelessWidget {
  const _LibraryRow({required this.apr, required this.onTap});

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
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: AppColors.border),
        ),
        child: Row(
          children: <Widget>[
            Expanded(
              flex: 4,
              child: Text(
                apr.title,
                style: Theme.of(context).textTheme.titleSmall,
              ),
            ),
            Expanded(
              flex: 2,
              child: Text(
                apr.location ?? 'Sem local',
                style: Theme.of(
                  context,
                ).textTheme.bodyMedium?.copyWith(color: AppColors.textSoft),
              ),
            ),
            Expanded(
              flex: 2,
              child: Text(
                AppFormatters.date(apr.updatedAt),
                style: Theme.of(
                  context,
                ).textTheme.bodyMedium?.copyWith(color: AppColors.textSoft),
              ),
            ),
            Expanded(
              flex: 2,
              child: Align(
                alignment: Alignment.centerLeft,
                child: AppBadge(
                  label: apr.riskScore == 0
                      ? 'Sem score'
                      : 'Score ${apr.riskScore}',
                  tone: apr.riskScore >= 15
                      ? AppBadgeTone.danger
                      : AppBadgeTone.info,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _FilterChip extends StatelessWidget {
  const _FilterChip({
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
                ? AppColors.primary.withValues(alpha: 0.26)
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

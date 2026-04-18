import 'package:flutter/material.dart';

import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_radius.dart';
import '../../../../app/theme/app_spacing.dart';
import '../../../../features/auth/domain/entities/app_user.dart';
import '../../../../shared/widgets/app_badge.dart';
import '../../../../shared/widgets/app_button.dart';
import '../../../../shared/widgets/app_panel.dart';

enum ShellDestination { home, library, newApr, workflow, risk, executive }

class WorkspaceScaffold extends StatelessWidget {
  const WorkspaceScaffold({
    super.key,
    required this.active,
    required this.currentUser,
    required this.heroEyebrow,
    required this.heroTitle,
    required this.heroDescription,
    required this.body,
    required this.onDestinationSelected,
    required this.onLogout,
    this.heroActions = const <Widget>[],
    this.heroAside,
    this.metrics = const <Widget>[],
  });

  final ShellDestination active;
  final AppUser currentUser;
  final String heroEyebrow;
  final String heroTitle;
  final String heroDescription;
  final List<Widget> heroActions;
  final Widget? heroAside;
  final List<Widget> metrics;
  final Widget body;
  final ValueChanged<ShellDestination> onDestinationSelected;
  final VoidCallback onLogout;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: <Color>[Color(0xFFF4F7FC), Color(0xFFEEF3F8)],
          ),
        ),
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final wide = constraints.maxWidth >= 1180;
              return Align(
                alignment: Alignment.topCenter,
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 1720),
                  child: Padding(
                    padding: const EdgeInsets.all(AppSpacing.shell),
                    child: wide
                        ? Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              SizedBox(
                                width: 298,
                                child: _Sidebar(
                                  active: active,
                                  currentUser: currentUser,
                                  onDestinationSelected: onDestinationSelected,
                                  onLogout: onLogout,
                                ),
                              ),
                              const SizedBox(width: AppSpacing.xl),
                              Expanded(
                                child: _Content(
                                  heroEyebrow: heroEyebrow,
                                  heroTitle: heroTitle,
                                  heroDescription: heroDescription,
                                  heroActions: heroActions,
                                  heroAside: heroAside,
                                  metrics: metrics,
                                  body: body,
                                ),
                              ),
                            ],
                          )
                        : _MobileContent(
                            active: active,
                            currentUser: currentUser,
                            onDestinationSelected: onDestinationSelected,
                            onLogout: onLogout,
                            heroEyebrow: heroEyebrow,
                            heroTitle: heroTitle,
                            heroDescription: heroDescription,
                            heroActions: heroActions,
                            heroAside: heroAside,
                            metrics: metrics,
                            body: body,
                          ),
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}

class _Content extends StatelessWidget {
  const _Content({
    required this.heroEyebrow,
    required this.heroTitle,
    required this.heroDescription,
    required this.heroActions,
    required this.heroAside,
    required this.metrics,
    required this.body,
  });

  final String heroEyebrow;
  final String heroTitle;
  final String heroDescription;
  final List<Widget> heroActions;
  final Widget? heroAside;
  final List<Widget> metrics;
  final Widget body;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(
        parent: AlwaysScrollableScrollPhysics(),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          AppPanel(
            radius: AppRadius.xxl,
            padding: const EdgeInsets.all(AppSpacing.xxxl),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Expanded(
                      flex: 7,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          AppBadge(label: heroEyebrow, tone: AppBadgeTone.info),
                          const SizedBox(height: AppSpacing.lg),
                          Text(
                            heroTitle,
                            style: Theme.of(context).textTheme.displayMedium,
                          ),
                          const SizedBox(height: AppSpacing.md),
                          Text(
                            heroDescription,
                            style: Theme.of(context).textTheme.bodyLarge
                                ?.copyWith(color: AppColors.textSoft),
                          ),
                          if (heroActions.isNotEmpty) ...<Widget>[
                            const SizedBox(height: AppSpacing.xl),
                            Wrap(
                              spacing: AppSpacing.md,
                              runSpacing: AppSpacing.md,
                              children: heroActions,
                            ),
                          ],
                        ],
                      ),
                    ),
                    if (heroAside != null) ...<Widget>[
                      const SizedBox(width: AppSpacing.xl),
                      Expanded(flex: 4, child: heroAside!),
                    ],
                  ],
                ),
                if (metrics.isNotEmpty) ...<Widget>[
                  const SizedBox(height: AppSpacing.xxl),
                  Wrap(
                    spacing: AppSpacing.lg,
                    runSpacing: AppSpacing.lg,
                    children: metrics,
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.xl),
          body,
          const SizedBox(height: AppSpacing.section),
        ],
      ),
    );
  }
}

class _Sidebar extends StatelessWidget {
  const _Sidebar({
    required this.active,
    required this.currentUser,
    required this.onDestinationSelected,
    required this.onLogout,
  });

  final ShellDestination active;
  final AppUser currentUser;
  final ValueChanged<ShellDestination> onDestinationSelected;
  final VoidCallback onLogout;

  @override
  Widget build(BuildContext context) {
    return AppPanel(
      radius: 30,
      padding: const EdgeInsets.all(AppSpacing.xl),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const AppBadge(label: 'HCS', tone: AppBadgeTone.info),
          const SizedBox(height: AppSpacing.md),
          Text(
            'APR Intelligence',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(
            'Motor central para criacao, controle e evidencia operacional.',
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: AppColors.textSoft),
          ),
          const SizedBox(height: AppSpacing.xl),
          AppPanel(
            backgroundColor: AppColors.primarySoft,
            borderColor: Colors.transparent,
            radius: 22,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Motor central',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: AppColors.primaryDeep,
                  ),
                ),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  'Fluxo corporativo conectado com base MVP + legado para PDF e rastreabilidade.',
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: AppColors.primaryDeep),
                ),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.xl),
          ..._navItems(context),
          const SizedBox(height: AppSpacing.xl),
          AppButton(
            label: 'Criar nova APR',
            icon: Icons.add_rounded,
            onPressed: () => onDestinationSelected(ShellDestination.newApr),
          ),
          const SizedBox(height: AppSpacing.md),
          AppButton(
            label: 'Sair',
            tone: AppButtonTone.secondary,
            icon: Icons.logout_rounded,
            onPressed: onLogout,
          ),
          const SizedBox(height: AppSpacing.xl),
          Container(
            padding: const EdgeInsets.all(AppSpacing.md),
            decoration: BoxDecoration(
              color: AppColors.surfaceElevated,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: AppColors.border),
            ),
            child: Row(
              children: <Widget>[
                Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: AppColors.primarySoft,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  alignment: Alignment.center,
                  child: Text(
                    currentUser.firstName.substring(0, 1).toUpperCase(),
                  ),
                ),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        currentUser.name ?? currentUser.email,
                        style: Theme.of(context).textTheme.titleSmall,
                      ),
                      Text(
                        currentUser.companyName ?? 'Sem empresa',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: AppColors.textMuted,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  List<Widget> _navItems(BuildContext context) {
    final items = <(ShellDestination, IconData, String, String)>[
      (
        ShellDestination.home,
        Icons.home_rounded,
        'Visao geral',
        'Painel central',
      ),
      (
        ShellDestination.library,
        Icons.grid_view_rounded,
        'Biblioteca',
        'Atalhos e historico',
      ),
      (
        ShellDestination.newApr,
        Icons.edit_note_rounded,
        'Nova APR',
        'Cadastro guiado',
      ),
      (
        ShellDestination.workflow,
        Icons.alt_route_rounded,
        'Fluxo APR',
        'Etapas conectadas',
      ),
      (
        ShellDestination.risk,
        Icons.warning_amber_rounded,
        'Dash de riscos',
        'Mapa operacional',
      ),
      (
        ShellDestination.executive,
        Icons.analytics_rounded,
        'Dash executivo',
        'Leitura consolidada',
      ),
    ];
    return items
        .map(
          (item) => Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.sm),
            child: _NavPill(
              selected: active == item.$1,
              icon: item.$2,
              title: item.$3,
              subtitle: item.$4,
              onTap: () => onDestinationSelected(item.$1),
            ),
          ),
        )
        .toList();
  }
}

class _MobileContent extends StatelessWidget {
  const _MobileContent({
    required this.active,
    required this.currentUser,
    required this.onDestinationSelected,
    required this.onLogout,
    required this.heroEyebrow,
    required this.heroTitle,
    required this.heroDescription,
    required this.heroActions,
    required this.heroAside,
    required this.metrics,
    required this.body,
  });

  final ShellDestination active;
  final AppUser currentUser;
  final ValueChanged<ShellDestination> onDestinationSelected;
  final VoidCallback onLogout;
  final String heroEyebrow;
  final String heroTitle;
  final String heroDescription;
  final List<Widget> heroActions;
  final Widget? heroAside;
  final List<Widget> metrics;
  final Widget body;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        SizedBox(
          height: 58,
          child: ListView(
            scrollDirection: Axis.horizontal,
            physics: const BouncingScrollPhysics(),
            children: <Widget>[
              for (final item in ShellDestination.values)
                Padding(
                  padding: const EdgeInsets.only(right: AppSpacing.sm),
                  child: AppChip(
                    label: switch (item) {
                      ShellDestination.home => 'Visao geral',
                      ShellDestination.library => 'Biblioteca',
                      ShellDestination.newApr => 'Nova APR',
                      ShellDestination.workflow => 'Fluxo',
                      ShellDestination.risk => 'Riscos',
                      ShellDestination.executive => 'Executivo',
                    },
                    selected: item == active,
                    onTap: () => onDestinationSelected(item),
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
        Expanded(
          child: _Content(
            heroEyebrow: heroEyebrow,
            heroTitle: heroTitle,
            heroDescription: heroDescription,
            heroActions: <Widget>[
              ...heroActions,
              AppButton(
                label: 'Sair',
                expanded: false,
                tone: AppButtonTone.secondary,
                onPressed: onLogout,
              ),
            ],
            heroAside: heroAside,
            metrics: metrics,
            body: body,
          ),
        ),
      ],
    );
  }
}

class _NavPill extends StatelessWidget {
  const _NavPill({
    required this.selected,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final bool selected;
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        decoration: BoxDecoration(
          color: selected ? AppColors.primarySoft : AppColors.surface,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
            color: selected
                ? AppColors.primary.withValues(alpha: 0.25)
                : Colors.transparent,
          ),
        ),
        child: Row(
          children: <Widget>[
            Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                color: selected ? Colors.white : AppColors.surfaceElevated,
                borderRadius: BorderRadius.circular(14),
              ),
              alignment: Alignment.center,
              child: Icon(
                icon,
                size: 20,
                color: selected ? AppColors.primaryDeep : AppColors.sidebarIcon,
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(title, style: Theme.of(context).textTheme.titleSmall),
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: Theme.of(
                      context,
                    ).textTheme.bodySmall?.copyWith(color: AppColors.textMuted),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

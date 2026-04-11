import 'package:flutter/material.dart';
import 'widgets/sidebar.dart';
import 'widgets/topbar.dart';
import 'pages/portal_home.dart';
import 'pages/parameters/users_page.dart';
import 'pages/parameters/sites_page.dart';
import 'pages/parameters/activity_characteristics_page.dart';

enum AppRoute { portal, users, sites, activityChars }

class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  AppRoute _route = AppRoute.portal;

  Widget _pageFor(AppRoute r) {
    switch (r) {
      case AppRoute.portal:
        return const PortalHome();
      case AppRoute.users:
        return const UsersPage();
      case AppRoute.sites:
        return const SitesPage();
      case AppRoute.activityChars:
        return const ActivityCharacteristicsPage();
    }
  }

  String _titleFor(AppRoute r) {
    switch (r) {
      case AppRoute.portal:
        return 'HCS Construction Safety Portal';
      case AppRoute.users:
        return 'Parâmetros • Usuários';
      case AppRoute.sites:
        return 'Parâmetros • Sites';
      case AppRoute.activityChars:
        return 'Parâmetros • Características da Atividade';
    }
  }

  @override
  Widget build(BuildContext context) {
    final isWide = MediaQuery.of(context).size.width >= 1100;

    return Scaffold(
      body: Row(
        children: [
          if (isWide)
            Sidebar(
              selected: _route,
              onSelect: (r) => setState(() => _route = r),
            ),
          Expanded(
            child: Column(
              children: [
                TopBar(
                  title: _titleFor(_route),
                  onMenuTap: isWide
                      ? null
                      : () => showModalBottomSheet(
                          context: context,
                          backgroundColor: Colors.transparent,
                          builder: (_) => SafeArea(
                            child: Padding(
                              padding: const EdgeInsets.all(12),
                              child: Sidebar(
                                selected: _route,
                                onSelect: (r) {
                                  Navigator.pop(context);
                                  setState(() => _route = r);
                                },
                              ),
                            ),
                          ),
                        ),
                ),
                Expanded(
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 220),
                    child: _pageFor(_route),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

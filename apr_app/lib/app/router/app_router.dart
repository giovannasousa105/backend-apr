import 'package:flutter/material.dart';

import '../../features/apr/domain/entities/apr_models.dart';
import '../../features/apr/domain/repositories/apr_repository.dart';
import '../../features/apr/presentation/controllers/dashboard_controller.dart';
import '../../features/apr/presentation/controllers/home_controller.dart';
import '../../features/apr/presentation/controllers/library_controller.dart';
import '../../features/apr/presentation/controllers/workflow_controller.dart';
import '../../features/apr/presentation/screens/dashboards_screen.dart';
import '../../features/apr/presentation/screens/home_screen.dart';
import '../../features/apr/presentation/screens/library_screen.dart';
import '../../features/apr/presentation/screens/new_apr_screen.dart';
import '../../features/apr/presentation/screens/workflow_screen.dart';
import '../../features/apr/presentation/widgets/workspace_scaffold.dart';
import '../../features/auth/presentation/controllers/session_controller.dart';
import '../../features/auth/presentation/screens/login_screen.dart';
import '../../shared/widgets/app_feedback_state.dart';

class AppRouter {
  AppRouter({
    required SessionController sessionController,
    required AprRepository aprRepository,
  }) : _sessionController = sessionController,
       _aprRepository = aprRepository;

  final SessionController _sessionController;
  final AprRepository _aprRepository;

  Route<dynamic> onGenerateRoute(RouteSettings settings) {
    final uri = Uri.parse(settings.name ?? '/');
    if (uri.path == '/login') {
      return _page(LoginScreen(controller: _sessionController));
    }
    if (uri.path == '/' || uri.path == '/aprs') {
      return _page(
        _SessionAware(
          controller: _sessionController,
          child: HomeScreen(
            controller: HomeController(_aprRepository, _sessionController),
            sessionController: _sessionController,
            onDestinationSelected: _handleShellDestination,
            onOpenApr: _openWorkflowSummary,
            onLogout: _logout,
          ),
        ),
      );
    }
    if (uri.path == '/aprs/library') {
      return _page(
        _SessionAware(
          controller: _sessionController,
          child: LibraryScreen(
            controller: LibraryController(_aprRepository),
            sessionController: _sessionController,
            onDestinationSelected: _handleShellDestination,
            onOpenApr: _openWorkflowSummary,
            onLogout: _logout,
          ),
        ),
      );
    }
    if (uri.path == '/aprs/new') {
      return _page(
        _SessionAware(
          controller: _sessionController,
          child: NewAprScreen(
            repository: _aprRepository,
            sessionController: _sessionController,
            onDestinationSelected: _handleShellDestination,
            onCreated: (id) => _navKey.currentState?.pushReplacementNamed(
              '/aprs/$id/${WorkflowStage.create.path}',
            ),
            onLogout: _logout,
          ),
        ),
      );
    }
    if (uri.path == '/dashboards/risk') {
      return _page(
        _SessionAware(
          controller: _sessionController,
          child: RiskDashboardScreen(
            controller: DashboardController(_aprRepository),
            sessionController: _sessionController,
            onDestinationSelected: _handleShellDestination,
            onLogout: _logout,
          ),
        ),
      );
    }
    if (uri.path == '/dashboards/executive') {
      return _page(
        _SessionAware(
          controller: _sessionController,
          child: ExecutiveDashboardScreen(
            controller: DashboardController(_aprRepository),
            sessionController: _sessionController,
            onDestinationSelected: _handleShellDestination,
            onLogout: _logout,
          ),
        ),
      );
    }
    if (uri.pathSegments.length == 3 && uri.pathSegments.first == 'aprs') {
      final aprId = uri.pathSegments[1];
      final stage = WorkflowStage.tryFromPath(uri.pathSegments[2]);
      if (stage != null) {
        return _page(
          _SessionAware(
            controller: _sessionController,
            child: WorkflowScreen(
              controller: WorkflowController(_aprRepository, aprId),
              sessionController: _sessionController,
              stage: stage,
              onDestinationSelected: _handleShellDestination,
              onStageChanged: (nextStage) => _navKey.currentState
                  ?.pushReplacementNamed('/aprs/$aprId/${nextStage.path}'),
              onLogout: _logout,
            ),
          ),
        );
      }
    }
    return _page(
      const Scaffold(
        body: Center(
          child: AppFeedbackState.inlineEmpty(
            title: 'Rota nao encontrada',
            message:
                'A navegacao solicitada nao existe nesta versao do frontend.',
          ),
        ),
      ),
    );
  }

  final GlobalKey<NavigatorState> _navKey = GlobalKey<NavigatorState>();

  GlobalKey<NavigatorState> get navigatorKey => _navKey;

  void _handleShellDestination(ShellDestination destination) {
    final path = switch (destination) {
      ShellDestination.home => '/',
      ShellDestination.library => '/aprs/library',
      ShellDestination.newApr => '/aprs/new',
      ShellDestination.workflow => '/',
      ShellDestination.risk => '/dashboards/risk',
      ShellDestination.executive => '/dashboards/executive',
    };
    _navKey.currentState?.pushReplacementNamed(path);
  }

  void _openWorkflowSummary(AprSummary apr) {
    final stage = switch (apr.status) {
      AprStatus.submitted => WorkflowStage.approval,
      AprStatus.approved => WorkflowStage.execution,
      AprStatus.inProgress ||
      AprStatus.paused ||
      AprStatus.finished => WorkflowStage.execution,
      AprStatus.archived => WorkflowStage.report,
      _ => WorkflowStage.create,
    };
    _navKey.currentState?.pushNamed('/aprs/${apr.id}/${stage.path}');
  }

  Future<void> _logout() async {
    await _sessionController.logout();
    _navKey.currentState?.pushNamedAndRemoveUntil('/login', (route) => false);
  }

  MaterialPageRoute<void> _page(Widget child) {
    return MaterialPageRoute<void>(builder: (_) => child);
  }
}

class _BootstrappingScreen extends StatelessWidget {
  const _BootstrappingScreen();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: SizedBox(
          width: 420,
          child: AppFeedbackState.inlineLoading(
            title: 'Preparando sessao',
            message:
                'Validando token, perfil e empresa antes de abrir o workspace.',
          ),
        ),
      ),
    );
  }
}

class _SessionAware extends StatelessWidget {
  const _SessionAware({required this.controller, required this.child});

  final SessionController controller;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        if (controller.isBootstrapping) {
          return const _BootstrappingScreen();
        }
        if (!controller.isAuthenticated) {
          return LoginScreen(controller: controller);
        }
        return child;
      },
    );
  }
}

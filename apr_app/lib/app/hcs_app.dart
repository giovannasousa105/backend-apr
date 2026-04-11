import 'package:flutter/material.dart';

import '../core/network/api_client.dart';
import '../features/apr/data/local/workflow_mock_store.dart';
import '../features/apr/data/repositories/apr_repository_impl.dart';
import '../features/auth/data/local/session_token_store.dart';
import '../features/auth/data/repositories/auth_repository_impl.dart';
import '../features/auth/presentation/controllers/session_controller.dart';
import 'router/app_router.dart';
import 'theme/app_theme.dart';

class HcsApp extends StatefulWidget {
  const HcsApp({super.key});

  @override
  State<HcsApp> createState() => _HcsAppState();
}

class _HcsAppState extends State<HcsApp> {
  late final SessionTokenStore _tokenStore;
  late final ApiClient _apiClient;
  late final SessionController _sessionController;
  late final AppRouter _router;

  @override
  void initState() {
    super.initState();
    _tokenStore = SessionTokenStore();
    _apiClient = ApiClient(_tokenStore);
    _sessionController = SessionController(
      AuthRepositoryImpl(_apiClient, _tokenStore),
    );
    _router = AppRouter(
      sessionController: _sessionController,
      aprRepository: AprRepositoryImpl(_apiClient, WorkflowMockStore()),
    );
    _sessionController.bootstrap();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _sessionController,
      builder: (context, _) => MaterialApp(
        key: ValueKey<String>(
          '${_sessionController.isBootstrapping}-${_sessionController.isAuthenticated}',
        ),
        debugShowCheckedModeBanner: false,
        title: 'HCS APR',
        theme: AppTheme.light(),
        navigatorKey: _router.navigatorKey,
        onGenerateRoute: _router.onGenerateRoute,
        initialRoute: '/',
      ),
    );
  }
}

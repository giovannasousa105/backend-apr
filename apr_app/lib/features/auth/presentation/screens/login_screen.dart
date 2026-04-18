import 'package:flutter/material.dart';

import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_spacing.dart';
import '../../../../shared/widgets/app_button.dart';
import '../../../../shared/widgets/app_feedback_state.dart';
import '../../../../shared/widgets/app_input.dart';
import '../../../../shared/widgets/app_panel.dart';
import '../../../../shared/widgets/app_badge.dart';
import '../controllers/session_controller.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.controller});

  final SessionController controller;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final ok = await widget.controller.login(
      email: _emailController.text,
      password: _passwordController.text,
    );
    if (!mounted || !ok) {
      return;
    }
    Navigator.of(context).pushReplacementNamed('/');
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: <Color>[
              Color(0xFFF5F9FF),
              Color(0xFFE9F0F7),
              Color(0xFFF8FBFF),
            ],
          ),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(AppSpacing.section),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1120),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.only(
                          right: AppSpacing.section,
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            const AppBadge(
                              label: 'HCS • Operacao APR',
                              tone: AppBadgeTone.info,
                            ),
                            const SizedBox(height: AppSpacing.xl),
                            Text(
                              'APR pronta para operacao, aprovacao e rastreabilidade real.',
                              style: theme.textTheme.displayMedium,
                            ),
                            const SizedBox(height: AppSpacing.lg),
                            Text(
                              'Acesso direto ao fluxo corporativo com biblioteca, matriz, aprovacao, execucao e relatorio consolidado.',
                              style: theme.textTheme.bodyLarge?.copyWith(
                                color: AppColors.textSoft,
                              ),
                            ),
                            const SizedBox(height: AppSpacing.section),
                            Wrap(
                              spacing: AppSpacing.md,
                              runSpacing: AppSpacing.md,
                              children: const <Widget>[
                                _LoginFeature(
                                  title: 'Fila viva',
                                  subtitle:
                                      'status, SLA e prioridade no mesmo painel',
                                ),
                                _LoginFeature(
                                  title: 'Fluxo conectado',
                                  subtitle:
                                      'criar, controlar, aprovar, executar e fechar',
                                ),
                                _LoginFeature(
                                  title: 'Base preparada',
                                  subtitle:
                                      'integra MVP + legado /v1 sem mock colado na UI',
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ),
                    SizedBox(
                      width: 420,
                      child: AnimatedBuilder(
                        animation: widget.controller,
                        builder: (context, _) {
                          return AppPanel(
                            padding: const EdgeInsets.all(AppSpacing.xxl),
                            radius: 30,
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                Text(
                                  'Entrar no workspace',
                                  style: theme.textTheme.headlineMedium,
                                ),
                                const SizedBox(height: AppSpacing.sm),
                                Text(
                                  'Use as credenciais do backend `backend-apr`.',
                                  style: theme.textTheme.bodyMedium?.copyWith(
                                    color: AppColors.textSoft,
                                  ),
                                ),
                                const SizedBox(height: AppSpacing.xl),
                                AppInput(
                                  label: 'E-mail',
                                  hint: 'voce@empresa.com',
                                  controller: _emailController,
                                  keyboardType: TextInputType.emailAddress,
                                ),
                                const SizedBox(height: AppSpacing.md),
                                AppInput(
                                  label: 'Senha',
                                  hint: '••••••••',
                                  controller: _passwordController,
                                  obscureText: true,
                                  onSubmitted: (_) => _submit(),
                                ),
                                const SizedBox(height: AppSpacing.lg),
                                if (widget.controller.errorMessage !=
                                    null) ...<Widget>[
                                  AppFeedbackState.inlineError(
                                    title: 'Falha no acesso',
                                    message: widget.controller.errorMessage!,
                                  ),
                                  const SizedBox(height: AppSpacing.lg),
                                ],
                                AppButton(
                                  label: widget.controller.isBusy
                                      ? 'Entrando...'
                                      : 'Acessar plataforma',
                                  onPressed: widget.controller.isBusy
                                      ? null
                                      : _submit,
                                ),
                                const SizedBox(height: AppSpacing.md),
                                Text(
                                  'Sem empresa vinculada no backend, o login nao conclui a sessao.',
                                  style: theme.textTheme.bodySmall?.copyWith(
                                    color: AppColors.textMuted,
                                  ),
                                ),
                              ],
                            ),
                          );
                        },
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _LoginFeature extends StatelessWidget {
  const _LoginFeature({required this.title, required this.subtitle});

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 220,
      child: AppPanel(
        backgroundColor: AppColors.surface.withValues(alpha: 0.74),
        radius: 24,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: AppSpacing.xs),
            Text(
              subtitle,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: AppColors.textSoft),
            ),
          ],
        ),
      ),
    );
  }
}

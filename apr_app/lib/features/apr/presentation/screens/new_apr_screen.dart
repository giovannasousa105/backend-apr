import 'package:flutter/material.dart';

import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_spacing.dart';
import '../../../../shared/widgets/app_badge.dart';
import '../../../../shared/widgets/app_button.dart';
import '../../../../shared/widgets/app_feedback_state.dart';
import '../../../../shared/widgets/app_input.dart';
import '../../../../shared/widgets/app_panel.dart';
import '../../../../shared/widgets/section_header.dart';
import '../../../auth/presentation/controllers/session_controller.dart';
import '../../domain/entities/apr_models.dart';
import '../../domain/repositories/apr_repository.dart';
import '../widgets/workspace_scaffold.dart';

class NewAprScreen extends StatefulWidget {
  const NewAprScreen({
    super.key,
    required this.repository,
    required this.sessionController,
    required this.onDestinationSelected,
    required this.onCreated,
    required this.onLogout,
  });

  final AprRepository repository;
  final SessionController sessionController;
  final ValueChanged<ShellDestination> onDestinationSelected;
  final ValueChanged<String> onCreated;
  final Future<void> Function() onLogout;

  @override
  State<NewAprScreen> createState() => _NewAprScreenState();
}

class _NewAprScreenState extends State<NewAprScreen> {
  final _titleController = TextEditingController();
  final _siteController = TextEditingController();
  final _areaController = TextEditingController();
  final _characteristicController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _contractController = TextEditingController();
  final _shiftController = TextEditingController();
  final _evaluatorController = TextEditingController();

  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _titleController.dispose();
    _siteController.dispose();
    _areaController.dispose();
    _characteristicController.dispose();
    _descriptionController.dispose();
    _contractController.dispose();
    _shiftController.dispose();
    _evaluatorController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final apr = await widget.repository.createApr(
        AprFormDraft(
          title: _titleController.text,
          site: _siteController.text,
          area: _areaController.text,
          characteristic: _characteristicController.text,
          description: _descriptionController.text,
          contractUnit: _contractController.text,
          shift: _shiftController.text,
          evaluator: _evaluatorController.text,
        ),
      );
      if (!mounted) {
        return;
      }
      widget.onCreated(apr.id);
    } catch (error) {
      setState(() => _error = error.toString());
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = widget.sessionController.currentUser!;
    return WorkspaceScaffold(
      active: ShellDestination.newApr,
      currentUser: user,
      heroEyebrow: 'Nova APR',
      heroTitle: 'Criar nova APR com base limpa e pronta para IA.',
      heroDescription:
          'A etapa inicial concentra briefing, contexto operacional e metadados com proporcao ajustada. O resultado segue direto para a matriz, sem telas isoladas.',
      heroActions: <Widget>[
        AppButton(
          label: _busy ? 'Salvando...' : 'Criar e abrir fluxo',
          expanded: false,
          icon: Icons.arrow_forward_rounded,
          onPressed: _busy ? null : _submit,
        ),
      ],
      heroAside: AppPanel(
        radius: 28,
        backgroundColor: AppColors.surfaceElevated,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const AppBadge(label: 'Briefing tecnico', tone: AppBadgeTone.info),
            const SizedBox(height: AppSpacing.lg),
            Text(
              'O que esta sendo criado',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              'A APR nasce no MVP, e o espelhamento legado entra quando a matriz, aprovacao ou PDF exigirem.',
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: AppColors.textSoft),
            ),
          ],
        ),
      ),
      onDestinationSelected: widget.onDestinationSelected,
      onLogout: () => widget.onLogout(),
      body: Row(
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
                    eyebrow: 'Cadastro principal da atividade',
                    title: 'Base inicial da APR',
                    subtitle:
                        'Composicao manual dos blocos para manter a hierarquia do Stitch.',
                  ),
                  const SizedBox(height: AppSpacing.xl),
                  Row(
                    children: <Widget>[
                      Expanded(
                        child: AppInput(
                          label: 'Titulo da APR',
                          controller: _titleController,
                          hint: 'Parada geral da linha de envase',
                        ),
                      ),
                      const SizedBox(width: AppSpacing.md),
                      Expanded(
                        child: AppInput(
                          label: 'Site',
                          controller: _siteController,
                          hint: 'Unidade Jundiai',
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.md),
                  Row(
                    children: <Widget>[
                      Expanded(
                        child: AppInput(
                          label: 'Area / setor',
                          controller: _areaController,
                          hint: 'Sala de utilidades',
                        ),
                      ),
                      const SizedBox(width: AppSpacing.md),
                      Expanded(
                        child: AppInput(
                          label: 'Caracteristica da atividade',
                          controller: _characteristicController,
                          hint: 'Manutencao programada',
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
                          controller: _contractController,
                          hint: 'Contrato 04 / HCS',
                        ),
                      ),
                      const SizedBox(width: AppSpacing.md),
                      Expanded(
                        child: AppInput(
                          label: 'Turno',
                          controller: _shiftController,
                          hint: 'Diurno',
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.md),
                  AppInput(
                    label: 'Elaboradores / avaliadores',
                    controller: _evaluatorController,
                    hint: 'Giovanna Sousa, Engenharia HCS',
                  ),
                  const SizedBox(height: AppSpacing.md),
                  AppInput(
                    label: 'Descricao do projeto / atividade',
                    controller: _descriptionController,
                    hint: 'Descreva o escopo tecnico e o contexto operacional.',
                    minLines: 5,
                    maxLines: 7,
                  ),
                  if (_error != null) ...<Widget>[
                    const SizedBox(height: AppSpacing.lg),
                    AppFeedbackState.inlineError(
                      title: 'Falha ao criar APR',
                      message: _error!,
                    ),
                  ],
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
                    eyebrow: 'Orientacao',
                    title: 'Pontos para uma abertura forte',
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  const _HintTile(
                    title: 'Titulo claro',
                    subtitle:
                        'Defina o recorte operacional com verbo, local e frente tecnica.',
                  ),
                  const _HintTile(
                    title: 'Contexto fiel',
                    subtitle:
                        'Site, area e turno estruturam matriz, aprovacao e PDF.',
                  ),
                  const _HintTile(
                    title: 'Resumo vivo',
                    subtitle:
                        'A descricao alimenta o passo de controles e ajuda no espelhamento legado.',
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  AppButton(
                    label: _busy
                        ? 'Salvando...'
                        : 'Criar e avancar para matriz',
                    onPressed: _busy ? null : _submit,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _HintTile extends StatelessWidget {
  const _HintTile({required this.title, required this.subtitle});

  final String title;
  final String subtitle;

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
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: AppSpacing.xs),
          Text(
            subtitle,
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: AppColors.textSoft),
          ),
        ],
      ),
    );
  }
}

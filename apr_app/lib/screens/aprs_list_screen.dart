import 'package:flutter/material.dart';

import '../config/api_config.dart';
import '../models/api_models.dart';
import '../services/api_service.dart';
import '../widgets/app_back_button.dart';

enum _AprAction { submit, edit, remove }

class AprsListScreen extends StatefulWidget {
  final VoidCallback? onBack;
  final VoidCallback? onOpenMatriz;
  final void Function(ApiApr apr)? onOpenMatrizWithApr;
  final VoidCallback? onOpenCatalogos;
  final VoidCallback? onOpenAprForm;
  final void Function(ApiApr apr)? onEditApr;

  const AprsListScreen({
    super.key,
    this.onBack,
    this.onOpenMatriz,
    this.onOpenMatrizWithApr,
    this.onOpenCatalogos,
    this.onOpenAprForm,
    this.onEditApr,
  });

  @override
  State<AprsListScreen> createState() => _AprsListScreenState();
}

class _AprsListScreenState extends State<AprsListScreen> {
  late final ApiService _api;
  bool _loading = true;
  String? _error;
  List<ApiApr> _items = [];
  final Set<String> _busyIds = <String>{};

  @override
  void initState() {
    super.initState();
    _api = ApiService(baseUrl: resolveBaseUrl());
    _reload();
  }

  String _statusLabel(String raw) {
    final key = raw.trim().toLowerCase();
    switch (key) {
      case 'rascunho':
      case 'draft':
        return 'Rascunho';
      case 'enviado':
      case 'submitted':
        return 'Enviado';
      case 'aprovado':
      case 'approved':
      case 'final':
        return 'Aprovado';
      case 'reprovado':
      case 'rejected':
        return 'Reprovado';
      case 'arquivado':
      case 'archived':
        return 'Arquivado';
      default:
        return raw;
    }
  }

  bool _canSubmit(String raw) {
    final key = raw.trim().toLowerCase();
    return key == 'rascunho' ||
        key == 'draft' ||
        key == 'reprovado' ||
        key == 'rejected';
  }

  bool _isArchived(String raw) {
    final key = raw.trim().toLowerCase();
    return key == 'arquivado' || key == 'archived';
  }

  Future<int?> _resolveLegacyId(ApiApr apr) async {
    final direct = int.tryParse(apr.id);
    if (direct != null) return direct;
    return _api.resolveLegacyAprIdFromMvpId(apr.id);
  }

  Future<void> _reload() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await _api.getAprs(skip: 0, limit: 200);
      final rawItems = (data['items'] as List<dynamic>? ?? [])
          .whereType<Map<String, dynamic>>();
      final items = rawItems
          .map((e) => ApiApr.fromJson(e))
          .where((item) => !_isArchived(item.status))
          .toList();
      if (!mounted) return;
      setState(() {
        _items = items;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
      });
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  Future<void> _submitApr(ApiApr apr) async {
    if (!_canSubmit(apr.status)) return;
    final legacyAprId = await _resolveLegacyId(apr);
    if (!mounted) return;
    if (legacyAprId == null) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('APR invalida para envio')));
      return;
    }
    setState(() => _busyIds.add(apr.id));
    try {
      await _api.updateAprStatus(aprId: legacyAprId, status: 'submitted');
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('APR enviada com sucesso')));
      await _reload();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Falha ao enviar APR: $e')));
    } finally {
      if (mounted) {
        setState(() => _busyIds.remove(apr.id));
      }
    }
  }

  Future<void> _removeApr(ApiApr apr) async {
    final legacyAprId = await _resolveLegacyId(apr);
    if (!mounted) return;
    if (legacyAprId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('APR invalida para remocao')),
      );
      return;
    }

    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Remover APR'),
        content: const Text(
          'Deseja remover esta APR? Ela sera arquivada e saira da lista.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Remover'),
          ),
        ],
      ),
    );
    if (ok != true) return;

    setState(() => _busyIds.add(apr.id));
    try {
      await _api.deleteApr(legacyAprId);
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('APR removida com sucesso')));
      await _reload();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Falha ao remover APR: $e')));
    } finally {
      if (mounted) {
        setState(() => _busyIds.remove(apr.id));
      }
    }
  }

  PreferredSizeWidget _buildAppBar() {
    return AppBar(
      leading: AppBackButton(onFallback: widget.onBack),
      title: const Text('APRs'),
      actions: [
        if (widget.onOpenAprForm != null)
          IconButton(
            tooltip: 'Nova APR',
            onPressed: widget.onOpenAprForm,
            icon: const Icon(Icons.add),
          ),
        if (widget.onOpenMatriz != null)
          IconButton(
            tooltip: 'Matriz de risco',
            onPressed: widget.onOpenMatriz,
            icon: const Icon(Icons.grid_view),
          ),
        if (widget.onOpenCatalogos != null)
          IconButton(
            tooltip: 'Catalogos',
            onPressed: widget.onOpenCatalogos,
            icon: const Icon(Icons.menu_book_outlined),
          ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return Scaffold(
        appBar: _buildAppBar(),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (_error != null) {
      return Scaffold(
        appBar: _buildAppBar(),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Erro ao carregar APRs: $_error',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 12),
                FilledButton(
                  onPressed: _reload,
                  child: const Text('Tentar novamente'),
                ),
              ],
            ),
          ),
        ),
      );
    }

    if (_items.isEmpty) {
      return Scaffold(
        appBar: _buildAppBar(),
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('Nenhuma APR cadastrada'),
              const SizedBox(height: 12),
              if (widget.onOpenAprForm != null)
                FilledButton(
                  onPressed: widget.onOpenAprForm,
                  child: const Text('Nova APR'),
                ),
              if (widget.onOpenMatriz != null) ...[
                const SizedBox(height: 8),
                TextButton(
                  onPressed: widget.onOpenMatriz,
                  child: const Text('Ir para Matriz'),
                ),
              ],
              if (widget.onOpenCatalogos != null) ...[
                const SizedBox(height: 8),
                TextButton(
                  onPressed: widget.onOpenCatalogos,
                  child: const Text('Ir para Catalogos'),
                ),
              ],
            ],
          ),
        ),
      );
    }

    return Scaffold(
      appBar: _buildAppBar(),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: ListView.separated(
          itemCount: _items.length,
          separatorBuilder: (_, index) => const Divider(height: 1),
          itemBuilder: (context, index) {
            final item = _items[index];
            final busy = _busyIds.contains(item.id);
            final statusLabel = _statusLabel(item.status);

            return ListTile(
              onTap: widget.onOpenMatrizWithApr == null
                  ? widget.onOpenAprForm
                  : () => widget.onOpenMatrizWithApr!(item),
              title: Text(item.titulo.isEmpty ? 'APR sem titulo' : item.titulo),
              subtitle: Text(
                '${item.local?.isNotEmpty == true ? item.local : '-'} • $statusLabel',
              ),
              trailing: busy
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : PopupMenuButton<_AprAction>(
                      tooltip: 'Acoes da APR',
                      onSelected: (action) {
                        switch (action) {
                          case _AprAction.submit:
                            _submitApr(item);
                            break;
                          case _AprAction.edit:
                            widget.onEditApr?.call(item);
                            break;
                          case _AprAction.remove:
                            _removeApr(item);
                            break;
                        }
                      },
                      itemBuilder: (_) => <PopupMenuEntry<_AprAction>>[
                        if (_canSubmit(item.status))
                          const PopupMenuItem<_AprAction>(
                            value: _AprAction.submit,
                            child: Text('Enviar'),
                          ),
                        if (widget.onEditApr != null)
                          const PopupMenuItem<_AprAction>(
                            value: _AprAction.edit,
                            child: Text('Editar'),
                          ),
                        const PopupMenuItem<_AprAction>(
                          value: _AprAction.remove,
                          child: Text('Remover'),
                        ),
                      ],
                      child: Chip(label: Text(statusLabel)),
                    ),
            );
          },
        ),
      ),
    );
  }
}

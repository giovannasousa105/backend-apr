import 'package:flutter/material.dart';

import '../config/api_config.dart';
import '../models/api_models.dart';
import '../services/api_service.dart';
import '../widgets/app_back_button.dart';

class PerigosListScreen extends StatefulWidget {
  const PerigosListScreen({super.key});

  @override
  State<PerigosListScreen> createState() => _PerigosListScreenState();
}

class _PerigosListScreenState extends State<PerigosListScreen> {
  late final ApiService _api;
  late Future<Paginated<ApiPerigo>> _future;

  @override
  void initState() {
    super.initState();
    _api = ApiService(baseUrl: resolveBaseUrl());
    _future = _load();
  }

  Future<Paginated<ApiPerigo>> _load() async {
    final data = await _api.getPerigosAdmin(limit: 100);
    final items = (data['items'] as List<dynamic>)
        .map((e) => ApiPerigo.fromJson(e as Map<String, dynamic>))
        .toList();
    return Paginated<ApiPerigo>(
      items: items,
      total: data['total'] as int,
      skip: data['skip'] as int,
      limit: data['limit'] as int,
    );
  }

  void _showError(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _editPerigo(ApiPerigo item) async {
    final probController = TextEditingController(
      text: item.defaultProbability.toString(),
    );
    final sevController = TextEditingController(
      text: item.defaultSeverity.toString(),
    );

    final result = await showDialog<Map<String, int>>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Editar risco padrao'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                item.perigo,
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: probController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Probabilidade (1-5)',
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: sevController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Severidade (1-5)',
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancelar'),
            ),
            ElevatedButton(
              onPressed: () {
                final prob = int.tryParse(probController.text.trim());
                final sev = int.tryParse(sevController.text.trim());
                if (prob == null || prob < 1 || prob > 5) {
                  _showError('Probabilidade deve ser entre 1 e 5');
                  return;
                }
                if (sev == null || sev < 1 || sev > 5) {
                  _showError('Severidade deve ser entre 1 e 5');
                  return;
                }
                Navigator.pop(context, {'prob': prob, 'sev': sev});
              },
              child: const Text('Salvar'),
            ),
          ],
        );
      },
    );

    if (result == null) return;

    try {
      await _api.updatePerigoDefaults(
        perigoId: item.id,
        defaultProbability: result['prob'],
        defaultSeverity: result['sev'],
      );
      if (mounted) {
        setState(() => _future = _load());
      }
    } catch (e) {
      _showError('Falha ao salvar: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: const AppBackButton(),
        title: const Text('Perigos'),
      ),
      body: FutureBuilder<Paginated<ApiPerigo>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text('Erro: ${snapshot.error}'));
          }
          final data = snapshot.data;
          final items = data?.items ?? [];
          if (items.isEmpty) {
            return const Center(child: Text('Sem perigos'));
          }
          return ListView.separated(
            itemCount: items.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final item = items[index];
              final subtitle = [
                if ((item.consequencias ?? '').isNotEmpty) item.consequencias!,
                'Padrao: P${item.defaultProbability} | S${item.defaultSeverity}',
              ].join('\n');
              return ListTile(
                title: Text(item.perigo),
                subtitle: Text(subtitle),
                isThreeLine: true,
                trailing: IconButton(
                  icon: const Icon(Icons.edit),
                  onPressed: () => _editPerigo(item),
                ),
              );
            },
          );
        },
      ),
    );
  }
}

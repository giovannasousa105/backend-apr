import 'package:flutter/material.dart';

import '../config/api_config.dart';
import '../models/api_models.dart';
import '../services/api_service.dart';
import '../widgets/app_back_button.dart';

class EpisListScreen extends StatefulWidget {
  const EpisListScreen({super.key});

  @override
  State<EpisListScreen> createState() => _EpisListScreenState();
}

class _EpisListScreenState extends State<EpisListScreen> {
  late final ApiService _api;
  late Future<Paginated<ApiEpi>> _future;

  @override
  void initState() {
    super.initState();
    _api = ApiService(baseUrl: resolveBaseUrl());
    _future = _load();
  }

  Future<Paginated<ApiEpi>> _load() async {
    final data = await _api.getEpis(limit: 50);
    final items = (data['items'] as List<dynamic>)
        .map((e) => ApiEpi.fromJson(e as Map<String, dynamic>))
        .toList();
    return Paginated<ApiEpi>(
      items: items,
      total: data['total'] as int,
      skip: data['skip'] as int,
      limit: data['limit'] as int,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(leading: const AppBackButton(), title: const Text('EPIs')),
      body: FutureBuilder<Paginated<ApiEpi>>(
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
            return const Center(child: Text('Sem EPIs'));
          }
          return ListView.separated(
            itemCount: items.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final item = items[index];
              final epi = item.epi;
              final desc = item.descricao ?? '';
              return ListTile(title: Text(epi), subtitle: Text(desc));
            },
          );
        },
      ),
    );
  }
}

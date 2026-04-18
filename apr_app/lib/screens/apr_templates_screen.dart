import 'package:flutter/material.dart';
import '../config/api_config.dart';
import '../services/api_service.dart';
import '../widgets/app_back_button.dart';

class AprTemplatesScreen extends StatefulWidget {
  const AprTemplatesScreen({super.key});

  @override
  State<AprTemplatesScreen> createState() => _AprTemplatesScreenState();
}

class _AprTemplatesScreenState extends State<AprTemplatesScreen> {
  late final ApiService _api;
  bool _loading = true;
  String? _error;
  String _query = '';
  List<Map<String, dynamic>> _items = [];
  List<Map<String, dynamic>> _filtered = [];

  @override
  void initState() {
    super.initState();
    _api = ApiService(baseUrl: resolveBaseUrl());
    _load();
  }

  Future<void> _load() async {
    try {
      final items = await _api.getActivities();
      if (!mounted) return;
      setState(() {
        _items = items;
        _filtered = _applyFilter(items, _query);
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'Falha ao carregar modelos: $e';
        _loading = false;
      });
    }
  }

  List<Map<String, dynamic>> _applyFilter(
    List<Map<String, dynamic>> base,
    String query,
  ) {
    if (query.trim().isEmpty) return base;
    final q = query.toLowerCase();
    return base.where((item) {
      final id = (item['id'] ?? '').toString().toLowerCase();
      final name = (item['name'] ?? '').toString().toLowerCase();
      return id.contains(q) || name.contains(q);
    }).toList();
  }

  void _onSearch(String value) {
    setState(() {
      _query = value;
      _filtered = _applyFilter(_items, _query);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: const AppBackButton(),
        title: const Text('Biblioteca de modelos'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            TextField(
              decoration: const InputDecoration(
                labelText: 'Buscar por atividade',
                prefixIcon: Icon(Icons.search),
                border: OutlineInputBorder(),
              ),
              onChanged: _onSearch,
            ),
            const SizedBox(height: 12),
            if (_loading)
              const Expanded(child: Center(child: CircularProgressIndicator()))
            else if (_error != null)
              Expanded(
                child: Center(
                  child: Text(
                    _error!,
                    style: const TextStyle(color: Colors.red),
                    textAlign: TextAlign.center,
                  ),
                ),
              )
            else
              Expanded(
                child: ListView.separated(
                  itemCount: _filtered.length,
                  separatorBuilder: (_, __) => const Divider(height: 1),
                  itemBuilder: (ctx, index) {
                    final item = _filtered[index];
                    final id = item['id']?.toString() ?? '';
                    final name = item['name']?.toString() ?? '';
                    return ListTile(
                      title: Text(name.isEmpty ? 'Atividade $id' : name),
                      subtitle: Text('ID: $id'),
                      trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                      onTap: () {
                        Navigator.pop(ctx, {'id': id, 'name': name});
                      },
                    );
                  },
                ),
              ),
          ],
        ),
      ),
    );
  }
}

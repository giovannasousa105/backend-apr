import 'package:flutter/material.dart';

import '../models/supabase_cart.dart';
import '../services/supabase_service.dart';

class FloatingCartChat extends StatefulWidget {
  const FloatingCartChat({super.key});

  @override
  State<FloatingCartChat> createState() => _FloatingCartChatState();
}

class _FloatingCartChatState extends State<FloatingCartChat> {
  bool _open = false;
  late Future<List<SupabaseCart>> _future;

  @override
  void initState() {
    super.initState();
    _future = SupabaseService.fetchCarts(limit: 5);
  }

  void _toggle() {
    setState(() {
      _open = !_open;
      if (_open) {
        _future = SupabaseService.fetchCarts(limit: 5);
      }
    });
  }

  Future<void> _refresh() async {
    setState(() {
      _future = SupabaseService.fetchCarts(limit: 5);
    });
    await _future;
  }

  Widget _buildPanel() {
    return Material(
      elevation: 8,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        width: 320,
        constraints: const BoxConstraints(maxHeight: 300),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          color: Theme.of(context).cardColor,
        ),
        child: FutureBuilder<List<SupabaseCart>>(
          future: _future,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const Padding(
                padding: EdgeInsets.all(24),
                child: Center(child: CircularProgressIndicator()),
              );
            }
            if (snapshot.hasError) {
              return Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text(
                      'Não foi possível carregar os carrinhos.',
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 12),
                    Text(snapshot.error.toString()),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: _refresh,
                      child: const Text('Atualizar'),
                    ),
                  ],
                ),
              );
            }

            final carts = snapshot.data ?? [];
            if (carts.isEmpty) {
              return Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    const Text('Sem carrinhos ativos no momento.'),
                    const SizedBox(height: 12),
                    IconButton(
                      onPressed: _refresh,
                      icon: const Icon(Icons.refresh),
                      tooltip: 'Recarregar',
                    ),
                  ],
                ),
              );
            }

            return Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 12,
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Carrinhos no Supabase',
                        style: TextStyle(fontWeight: FontWeight.w600),
                      ),
                      IconButton(
                        onPressed: _refresh,
                        icon: const Icon(Icons.refresh_outlined),
                        tooltip: 'Recarregar',
                      ),
                    ],
                  ),
                ),
                const Divider(height: 1),
                Expanded(
                  child: ListView.separated(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    itemCount: carts.length,
                    separatorBuilder: (_, __) => const Divider(height: 1),
                    itemBuilder: (context, index) {
                      final cart = carts[index];
                      return ListTile(
                        dense: true,
                        title: Text(cart.label),
                        subtitle: Text(
                          '${cart.status} · ${cart.friendlyUpdatedAt}',
                        ),
                        trailing: Text(
                          cart.formattedTotal,
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                      );
                    },
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        if (_open) _buildPanel(),
        const SizedBox(height: 10),
        FloatingActionButton(
          heroTag: 'floating-cart',
          onPressed: _toggle,
          tooltip: _open ? 'Fechar painel de carrinhos' : 'Ver carrinhos',
          child: Icon(_open ? Icons.close : Icons.chat_bubble),
        ),
      ],
    );
  }
}

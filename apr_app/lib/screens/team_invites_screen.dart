import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../config/api_config.dart';
import '../services/api_service.dart';
import '../widgets/app_back_button.dart';

class TeamInvitesScreen extends StatefulWidget {
  const TeamInvitesScreen({super.key});

  @override
  State<TeamInvitesScreen> createState() => _TeamInvitesScreenState();
}

class _TeamInvitesScreenState extends State<TeamInvitesScreen> {
  late final ApiService _api;
  final _emailCtrl = TextEditingController();
  String _role = 'tecnico';
  bool _loading = false;
  bool _creating = false;
  String? _error;
  String? _lastInviteLink;
  List<Map<String, dynamic>> _invites = [];

  @override
  void initState() {
    super.initState();
    _api = ApiService(baseUrl: resolveBaseUrl());
    _loadInvites();
  }

  Future<void> _loadInvites() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final items = await _api.getInvites();
      if (!mounted) return;
      setState(() {
        _invites = items;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = 'Falha ao carregar convites: $e');
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _createInvite() async {
    final email = _emailCtrl.text.trim();
    if (email.isEmpty) {
      setState(() => _error = 'Informe o email');
      return;
    }
    setState(() {
      _creating = true;
      _error = null;
      _lastInviteLink = null;
    });
    try {
      final data = await _api.createInvite(email: email, role: _role);
      if (!mounted) return;
      setState(() {
        _lastInviteLink = data['invite_link']?.toString();
        _emailCtrl.clear();
      });
      await _loadInvites();
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = 'Falha ao criar convite: $e');
    } finally {
      if (mounted) {
        setState(() => _creating = false);
      }
    }
  }

  Future<void> _revokeInvite(int inviteId) async {
    try {
      await _api.revokeInvite(inviteId);
      await _loadInvites();
    } catch (e) {
      setState(() => _error = 'Falha ao revogar convite: $e');
    }
  }

  Future<void> _copyLastLink() async {
    final link = _lastInviteLink;
    if (link == null || link.isEmpty) return;
    await Clipboard.setData(ClipboardData(text: link));
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text('Link copiado')));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: const AppBackButton(),
        title: const Text('Convites da Equipe'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            TextField(
              controller: _emailCtrl,
              decoration: const InputDecoration(
                labelText: 'Email do convidado',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: _role,
              decoration: const InputDecoration(
                labelText: 'Papel',
                border: OutlineInputBorder(),
              ),
              items: const [
                DropdownMenuItem(value: 'tecnico', child: Text('Técnico')),
                DropdownMenuItem(
                  value: 'visualizador',
                  child: Text('Visualizador'),
                ),
                DropdownMenuItem(value: 'admin', child: Text('Admin')),
              ],
              onChanged: (value) {
                setState(() {
                  _role = value ?? 'tecnico';
                });
              },
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              height: 44,
              child: ElevatedButton(
                onPressed: _creating ? null : _createInvite,
                child: _creating
                    ? const SizedBox(
                        height: 18,
                        width: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Gerar convite'),
              ),
            ),
            if (_lastInviteLink != null) ...[
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: Text(
                      _lastInviteLink!,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 8),
                  OutlinedButton(
                    onPressed: _copyLastLink,
                    child: const Text('Copiar'),
                  ),
                ],
              ),
            ],
            if (_error != null) ...[
              const SizedBox(height: 12),
              Align(
                alignment: Alignment.centerLeft,
                child: Text(_error!, style: const TextStyle(color: Colors.red)),
              ),
            ],
            const SizedBox(height: 12),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : ListView.separated(
                      itemCount: _invites.length,
                      separatorBuilder: (_, index) => const Divider(height: 1),
                      itemBuilder: (_, index) {
                        final item = _invites[index];
                        final status = item['status']?.toString() ?? '-';
                        final inviteId = item['id'] is int
                            ? item['id'] as int
                            : int.tryParse(item['id']?.toString() ?? '');
                        return ListTile(
                          title: Text(item['email']?.toString() ?? '-'),
                          subtitle: Text(
                            'role: ${item['role'] ?? '-'} | status: $status',
                          ),
                          trailing: status == 'pending' && inviteId != null
                              ? TextButton(
                                  onPressed: () => _revokeInvite(inviteId),
                                  child: const Text('Revogar'),
                                )
                              : null,
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

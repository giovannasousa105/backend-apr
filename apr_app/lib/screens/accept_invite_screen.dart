import 'package:flutter/material.dart';

import '../config/api_config.dart';
import '../services/api_service.dart';
import '../services/auth_storage.dart';
import '../widgets/app_back_button.dart';

class AcceptInviteScreen extends StatefulWidget {
  final String inviteToken;
  final VoidCallback onAccepted;
  final VoidCallback? onBackToLogin;

  const AcceptInviteScreen({
    super.key,
    required this.inviteToken,
    required this.onAccepted,
    this.onBackToLogin,
  });

  @override
  State<AcceptInviteScreen> createState() => _AcceptInviteScreenState();
}

class _AcceptInviteScreenState extends State<AcceptInviteScreen> {
  late final ApiService _api;
  final _nameCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  bool _hasSession = false;
  bool _verifying = true;
  bool _accepting = false;
  String? _error;
  Map<String, dynamic>? _inviteInfo;

  @override
  void initState() {
    super.initState();
    _api = ApiService(baseUrl: resolveBaseUrl());
    _loadSession();
    _verify();
  }

  Future<void> _loadSession() async {
    final token = await AuthStorage.getToken();
    if (!mounted) return;
    setState(() {
      _hasSession = token != null && token.isNotEmpty;
    });
  }

  Future<void> _verify() async {
    setState(() {
      _verifying = true;
      _error = null;
    });
    try {
      final data = await _api.verifyInvite(widget.inviteToken);
      if (!mounted) return;
      setState(() {
        _inviteInfo = data;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = 'Convite invalido: $e');
    } finally {
      if (mounted) {
        setState(() => _verifying = false);
      }
    }
  }

  Future<void> _accept() async {
    if (!_hasSession && _passwordCtrl.text.isEmpty) {
      setState(() => _error = 'Informe a senha para aceitar o convite');
      return;
    }
    setState(() {
      _accepting = true;
      _error = null;
    });
    try {
      final data = await _api.acceptInvite(
        token: widget.inviteToken,
        name: _nameCtrl.text.trim(),
        password: _passwordCtrl.text,
      );
      final token = data['token']?.toString() ?? '';
      if (token.isEmpty) {
        throw Exception('Token nao retornado');
      }
      await AuthStorage.setToken(token);
      widget.onAccepted();
    } catch (e) {
      setState(() => _error = 'Nao foi possivel aceitar convite: $e');
    } finally {
      if (mounted) {
        setState(() => _accepting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: AppBackButton(onFallback: widget.onBackToLogin),
        title: const Text('Aceitar Convite'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: _verifying
            ? const Center(child: CircularProgressIndicator())
            : ListView(
                children: [
                  if (_inviteInfo != null) ...[
                    Text(
                      'Empresa: ${_inviteInfo!['company_name'] ?? '-'}',
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 4),
                    Text('Email: ${_inviteInfo!['email_masked'] ?? '-'}'),
                    const SizedBox(height: 4),
                    Text('Perfil: ${_inviteInfo!['role'] ?? '-'}'),
                    const SizedBox(height: 16),
                  ],
                  TextField(
                    controller: _nameCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Nome (opcional)',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _passwordCtrl,
                    obscureText: true,
                    decoration: InputDecoration(
                      labelText: _hasSession ? 'Senha (opcional)' : 'Senha',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  if (_error != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Text(
                        _error!,
                        style: const TextStyle(color: Colors.red),
                      ),
                    ),
                  SizedBox(
                    height: 48,
                    child: ElevatedButton(
                      onPressed: _accepting ? null : _accept,
                      child: _accepting
                          ? const SizedBox(
                              height: 20,
                              width: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Text('Aceitar convite'),
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}

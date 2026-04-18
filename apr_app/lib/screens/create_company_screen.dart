import 'package:flutter/material.dart';

import '../config/api_config.dart';
import '../services/api_service.dart';
import '../services/auth_storage.dart';
import '../widgets/app_back_button.dart';

class CreateCompanyScreen extends StatefulWidget {
  final VoidCallback onCreated;
  final bool requireAdminCredentials;
  final bool popOnSuccess;

  const CreateCompanyScreen({
    super.key,
    required this.onCreated,
    this.requireAdminCredentials = true,
    this.popOnSuccess = false,
  });

  @override
  State<CreateCompanyScreen> createState() => _CreateCompanyScreenState();
}

class _CreateCompanyScreenState extends State<CreateCompanyScreen> {
  late final ApiService _api;
  final _companyCtrl = TextEditingController();
  final _cnpjCtrl = TextEditingController();
  final _nameCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _api = ApiService(baseUrl: resolveBaseUrl());
  }

  Future<void> _submit() async {
    final companyName = _companyCtrl.text.trim();
    final adminName = _nameCtrl.text.trim();
    final email = _emailCtrl.text.trim();
    final password = _passwordCtrl.text;
    if (companyName.isEmpty) {
      setState(() => _error = 'Nome da empresa obrigatorio');
      return;
    }
    if (widget.requireAdminCredentials && (email.isEmpty || password.isEmpty)) {
      setState(() => _error = 'Email e senha sao obrigatorios');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await _api.createCompany(
        name: companyName,
        cnpj: _cnpjCtrl.text.trim().isEmpty ? null : _cnpjCtrl.text.trim(),
        adminName: adminName,
        adminEmail: widget.requireAdminCredentials ? email : null,
        adminPassword: widget.requireAdminCredentials ? password : null,
      );
      final token = data['token']?.toString() ?? '';
      if (token.isNotEmpty) {
        await AuthStorage.setToken(token);
      }
      widget.onCreated();
      if (mounted && widget.popOnSuccess && Navigator.of(context).canPop()) {
        Navigator.of(context).pop();
      }
    } catch (e) {
      setState(() => _error = 'Falha ao criar empresa: $e');
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: const AppBackButton(),
        title: const Text('Criar Empresa'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: ListView(
          children: [
            TextField(
              controller: _companyCtrl,
              decoration: const InputDecoration(
                labelText: 'Nome da empresa',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _cnpjCtrl,
              decoration: const InputDecoration(
                labelText: 'CNPJ (opcional)',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _nameCtrl,
              decoration: const InputDecoration(
                labelText: 'Seu nome (opcional)',
                border: OutlineInputBorder(),
              ),
            ),
            if (widget.requireAdminCredentials) ...[
              const SizedBox(height: 12),
              TextField(
                controller: _emailCtrl,
                decoration: const InputDecoration(
                  labelText: 'Email do admin',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _passwordCtrl,
                obscureText: true,
                decoration: const InputDecoration(
                  labelText: 'Senha',
                  border: OutlineInputBorder(),
                ),
              ),
            ],
            const SizedBox(height: 12),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Text(_error!, style: const TextStyle(color: Colors.red)),
              ),
            SizedBox(
              height: 48,
              child: ElevatedButton(
                onPressed: _loading ? null : _submit,
                child: _loading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Criar workspace'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

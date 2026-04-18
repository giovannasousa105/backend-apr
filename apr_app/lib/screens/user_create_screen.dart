import 'package:flutter/material.dart';
import '../config/api_config.dart';
import '../services/api_service.dart';
import '../widgets/app_back_button.dart';

class UserCreateScreen extends StatefulWidget {
  const UserCreateScreen({super.key});

  @override
  State<UserCreateScreen> createState() => _UserCreateScreenState();
}

class _UserCreateScreenState extends State<UserCreateScreen> {
  late final ApiService _api;
  final TextEditingController _email = TextEditingController();
  final TextEditingController _name = TextEditingController();
  final TextEditingController _password = TextEditingController();
  final TextEditingController _company = TextEditingController();
  String _role = 'tecnico';
  List<Map<String, dynamic>> _companies = [];
  String _companySelection = 'default';
  bool _loadingCompanies = false;
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _api = ApiService(baseUrl: resolveBaseUrl());
    _loadCompanies();
  }

  Future<void> _loadCompanies() async {
    setState(() => _loadingCompanies = true);
    try {
      final items = await _api.getCompanies();
      if (!mounted) return;
      setState(() {
        _companies = items;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _companies = [];
      });
    } finally {
      if (mounted) {
        setState(() => _loadingCompanies = false);
      }
    }
  }

  Future<void> _createUser() async {
    final email = _email.text.trim();
    final password = _password.text;
    if (email.isEmpty || password.isEmpty) {
      setState(() => _error = 'Email e senha sao obrigatorios');
      return;
    }

    int? companyId;
    String? companyName;
    if (_companySelection == 'new') {
      companyName = _company.text.trim();
      if (companyName.isEmpty) {
        setState(() => _error = 'Informe o nome da empresa');
        return;
      }
    } else if (_companySelection != 'default') {
      companyId = int.tryParse(_companySelection);
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      await _api.createUser(
        email: email,
        password: password,
        name: _name.text.trim().isEmpty ? null : _name.text.trim(),
        role: _role,
        companyName: companyName,
        companyId: companyId,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Usuario criado com sucesso')),
      );
      Navigator.pop(context);
    } catch (e) {
      setState(() => _error = 'Falha ao criar usuario: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: const AppBackButton(),
        title: const Text('Cadastrar Usuario'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: ListView(
          children: [
            TextField(
              controller: _email,
              decoration: const InputDecoration(
                labelText: 'Email',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _name,
              decoration: const InputDecoration(
                labelText: 'Nome (opcional)',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _password,
              obscureText: true,
              decoration: const InputDecoration(
                labelText: 'Senha',
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
                DropdownMenuItem(value: 'tecnico', child: Text('Tecnico')),
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
            DropdownButtonFormField<String>(
              initialValue: _companySelection,
              decoration: const InputDecoration(
                labelText: 'Empresa',
                border: OutlineInputBorder(),
              ),
              items: [
                const DropdownMenuItem(
                  value: 'default',
                  child: Text('Empresa do admin'),
                ),
                ..._companies.map(
                  (c) => DropdownMenuItem(
                    value: c['id'].toString(),
                    child: Text(c['name'].toString()),
                  ),
                ),
                const DropdownMenuItem(
                  value: 'new',
                  child: Text('Nova empresa'),
                ),
              ],
              onChanged: (value) {
                setState(() {
                  _companySelection = value ?? 'default';
                });
              },
            ),
            if (_loadingCompanies)
              const Padding(
                padding: EdgeInsets.only(top: 6),
                child: Text('Carregando empresas...'),
              ),
            if (_companySelection == 'new')
              Padding(
                padding: const EdgeInsets.only(top: 12),
                child: TextField(
                  controller: _company,
                  decoration: const InputDecoration(
                    labelText: 'Nova empresa',
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
            const SizedBox(height: 12),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Text(_error!, style: const TextStyle(color: Colors.red)),
              ),
            SizedBox(
              width: double.infinity,
              height: 48,
              child: ElevatedButton(
                onPressed: _loading ? null : _createUser,
                child: _loading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Criar Usuario'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

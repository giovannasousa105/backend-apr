import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'dart:async';
import '../config/api_config.dart';
import '../services/api_service.dart';
import '../services/auth_storage.dart';
import '../widgets/app_back_button.dart';

class LoginScreen extends StatefulWidget {
  final VoidCallback onLoggedIn;
  final VoidCallback? onOpenCreateCompany;

  const LoginScreen({
    super.key,
    required this.onLoggedIn,
    this.onOpenCreateCompany,
  });

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  late final ApiService _api;
  final TextEditingController _email = TextEditingController();
  final TextEditingController _password = TextEditingController();
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _api = ApiService(baseUrl: resolveBaseUrl());
  }

  Future<void> _doLogin() async {
    final email = _email.text.trim();
    final password = _password.text;
    if (email.isEmpty || password.isEmpty) {
      setState(() => _error = 'Informe email e senha');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final resp = await _api.login(email: email, password: password);
      final token = resp['token']?.toString();
      if (token == null || token.isEmpty) {
        throw Exception('Token nao recebido');
      }
      await AuthStorage.setToken(token);
      if (kDebugMode) {
        debugPrint('AUTH TOKEN: $token');
      }
      widget.onLoggedIn();
    } on TimeoutException catch (e) {
      final msg = e.message?.toString();
      setState(() {
        _error = msg == null || msg.isEmpty
            ? 'Servidor indisponivel. Tente novamente em instantes.'
            : msg;
      });
    } catch (e) {
      setState(() => _error = 'Login falhou: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: const AppBackButton(),
        title: const Text('Login'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
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
              controller: _password,
              obscureText: true,
              decoration: const InputDecoration(
                labelText: 'Senha',
                border: OutlineInputBorder(),
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
                onPressed: _loading ? null : _doLogin,
                child: _loading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Entrar'),
              ),
            ),
            if (widget.onOpenCreateCompany != null) ...[
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                height: 44,
                child: OutlinedButton(
                  onPressed: _loading ? null : widget.onOpenCreateCompany,
                  child: const Text('Criar empresa'),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

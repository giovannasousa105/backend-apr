import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../widgets/app_back_button.dart';

const _defaultDemoUrl = String.fromEnvironment(
  'DEMO_EXTERNAL_URL',
  defaultValue: 'https://hcsdigital.com.br',
);

class DemoRedirectScreen extends StatefulWidget {
  const DemoRedirectScreen({super.key});

  @override
  State<DemoRedirectScreen> createState() => _DemoRedirectScreenState();
}

class _DemoRedirectScreenState extends State<DemoRedirectScreen> {
  bool _opening = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _openDemo();
  }

  Future<void> _openDemo() async {
    setState(() {
      _opening = true;
      _error = null;
    });

    final uri = Uri.tryParse(_defaultDemoUrl);
    if (uri == null) {
      setState(() {
        _opening = false;
        _error = 'Link de demo inválido: $_defaultDemoUrl';
      });
      return;
    }

    try {
      final ok = await launchUrl(uri, mode: LaunchMode.platformDefault);
      if (!mounted) return;
      setState(() {
        _opening = false;
        if (!ok) {
          _error = 'Não foi possível abrir o link externo.';
        }
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _opening = false;
        _error = 'Falha ao abrir demo: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: const AppBackButton(),
        title: const Text('Solicitar Demo'),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 560),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (_opening) ...[
                  const CircularProgressIndicator(),
                  const SizedBox(height: 16),
                  const Text(
                    'Abrindo canal de demonstração...',
                    textAlign: TextAlign.center,
                  ),
                ] else ...[
                  const Icon(Icons.open_in_new, size: 36),
                  const SizedBox(height: 12),
                  const Text(
                    'Canal de demo',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    _error ??
                        'Se não abriu automaticamente, use o botão abaixo.',
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  FilledButton.icon(
                    onPressed: _openDemo,
                    icon: const Icon(Icons.open_in_new),
                    label: const Text('Abrir link de demo'),
                  ),
                  const SizedBox(height: 8),
                  TextButton(
                    onPressed: () =>
                        Navigator.of(context).pushReplacementNamed('/'),
                    child: const Text('Voltar para início'),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

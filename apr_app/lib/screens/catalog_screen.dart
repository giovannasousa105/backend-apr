import 'package:flutter/material.dart';
import 'user_create_screen.dart';
import '../widgets/app_back_button.dart';

class CatalogScreen extends StatelessWidget {
  final VoidCallback? onBack;

  const CatalogScreen({super.key, this.onBack});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: AppBackButton(onFallback: onBack),
        title: const Text('Catálogos'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            SizedBox(
              height: 50,
              child: OutlinedButton(
                onPressed: () => Navigator.pushNamed(context, '/epis'),
                child: const Text('Ver EPIs', style: TextStyle(fontSize: 16)),
              ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 50,
              child: OutlinedButton(
                onPressed: () => Navigator.pushNamed(context, '/perigos'),
                child: const Text(
                  'Ver Perigos',
                  style: TextStyle(fontSize: 16),
                ),
              ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 50,
              child: OutlinedButton(
                onPressed: () => Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const UserCreateScreen()),
                ),
                child: const Text(
                  'Cadastrar Usuario',
                  style: TextStyle(fontSize: 16),
                ),
              ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 50,
              child: OutlinedButton(
                onPressed: () => Navigator.pushNamed(context, '/team-invites'),
                child: const Text(
                  'Convites da Equipe',
                  style: TextStyle(fontSize: 16),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

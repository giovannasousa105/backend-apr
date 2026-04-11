import 'package:flutter/material.dart';

class AppBackButton extends StatelessWidget {
  final VoidCallback? onFallback;

  const AppBackButton({super.key, this.onFallback});

  void _handleBack(BuildContext context) {
    final navigator = Navigator.of(context);
    if (navigator.canPop()) {
      navigator.pop();
      return;
    }
    onFallback?.call();
  }

  @override
  Widget build(BuildContext context) {
    return IconButton(
      tooltip: 'Voltar',
      onPressed: () => _handleBack(context),
      icon: const Icon(Icons.arrow_back),
    );
  }
}

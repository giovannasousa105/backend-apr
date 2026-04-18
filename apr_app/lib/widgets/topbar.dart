import 'dart:ui';
import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class TopBar extends StatelessWidget {
  final String title;
  final VoidCallback? onMenuTap;

  const TopBar({super.key, required this.title, this.onMenuTap});

  @override
  Widget build(BuildContext context) {
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
        child: Container(
          height: 68,
          padding: const EdgeInsets.symmetric(horizontal: 18),
          decoration: const BoxDecoration(
            color: Color(0x990B1020),
            border: Border(bottom: BorderSide(color: AppTheme.border)),
          ),
          child: Row(
            children: [
              if (onMenuTap != null) ...[
                IconButton(onPressed: onMenuTap, icon: const Icon(Icons.menu)),
                const SizedBox(width: 6),
              ],
              Expanded(
                child: Text(
                  title,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 16,
                    letterSpacing: 0.2,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              _pill('Português', Icons.language),
              const SizedBox(width: 10),
              _pill('Admin', Icons.verified_user_outlined),
            ],
          ),
        ),
      ),
    );
  }

  Widget _pill(String label, IconData icon) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: AppTheme.border),
        color: const Color(0xFF0E1630),
      ),
      child: Row(
        children: [
          Icon(icon, size: 16),
          const SizedBox(width: 8),
          Text(label, style: const TextStyle(fontSize: 13)),
        ],
      ),
    );
  }
}

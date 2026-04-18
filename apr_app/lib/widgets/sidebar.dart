import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../app_shell.dart';

class Sidebar extends StatelessWidget {
  final AppRoute selected;
  final ValueChanged<AppRoute> onSelect;

  const Sidebar({super.key, required this.selected, required this.onSelect});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 292,
      decoration: const BoxDecoration(
        color: AppTheme.surface,
        border: Border(right: BorderSide(color: AppTheme.border)),
      ),
      child: Column(
        children: [
          const SizedBox(height: 18),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: _brand(),
          ),
          const SizedBox(height: 14),
          const Divider(height: 1),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(12),
              children: [
                _section('Navegação'),
                _item(
                  icon: Icons.dashboard_outlined,
                  label: 'Portal',
                  route: AppRoute.portal,
                ),
                const SizedBox(height: 10),
                _section('Parâmetros'),
                _item(
                  icon: Icons.people_alt_outlined,
                  label: 'Usuários',
                  route: AppRoute.users,
                ),
                _item(
                  icon: Icons.location_on_outlined,
                  label: 'Sites',
                  route: AppRoute.sites,
                ),
                _item(
                  icon: Icons.category_outlined,
                  label: 'Características da Atividade',
                  route: AppRoute.activityChars,
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(14),
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.border),
                color: const Color(0xFF0E1630),
              ),
              child: Row(
                children: const [
                  Icon(Icons.security_outlined, size: 18),
                  SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'HCS • APR\nPortal corporativo',
                      style: TextStyle(fontSize: 12, color: AppTheme.subtext),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _brand() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppTheme.border),
        gradient: const LinearGradient(
          colors: [Color(0xFF0E1630), Color(0xFF0B1020)],
        ),
      ),
      child: Row(
        children: const [
          CircleAvatar(
            radius: 18,
            backgroundColor: Color(0xFF101B3B),
            child: Icon(Icons.shield_outlined, size: 18),
          ),
          SizedBox(width: 12),
          Expanded(
            child: Text(
              'HCS • APR',
              style: TextStyle(fontWeight: FontWeight.w700, letterSpacing: 0.4),
            ),
          ),
        ],
      ),
    );
  }

  Widget _section(String t) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 10, 8, 6),
      child: Text(
        t.toUpperCase(),
        style: const TextStyle(
          fontSize: 11,
          letterSpacing: 1.2,
          color: AppTheme.subtext,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  Widget _item({
    required IconData icon,
    required String label,
    required AppRoute route,
  }) {
    final active = selected == route;

    return InkWell(
      borderRadius: BorderRadius.circular(14),
      onTap: () => onSelect(route),
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: active
                ? AppTheme.neonCyan.withValues(alpha: 0.35)
                : AppTheme.border,
          ),
          color: active ? const Color(0xFF0E1630) : Colors.transparent,
        ),
        child: Row(
          children: [
            Icon(
              icon,
              size: 18,
              color: active ? AppTheme.neonCyan : AppTheme.text,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                label,
                style: TextStyle(
                  fontWeight: active ? FontWeight.w700 : FontWeight.w500,
                  color: active ? AppTheme.neonCyan : AppTheme.text,
                ),
              ),
            ),
            if (active)
              Container(
                width: 6,
                height: 6,
                decoration: const BoxDecoration(
                  shape: BoxShape.circle,
                  color: AppTheme.neonCyan,
                ),
              ),
          ],
        ),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import '../widgets/neon_card.dart';
import '../widgets/section_header.dart';
import '../theme/app_theme.dart';

class PortalHome extends StatelessWidget {
  const PortalHome({super.key});

  @override
  Widget build(BuildContext context) {
    final w = MediaQuery.of(context).size.width;
    final cols = w >= 1200 ? 3 : (w >= 800 ? 2 : 1);

    return Padding(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionHeader(
            title: 'Digital Tools',
            subtitle: 'Acesso rápido às ferramentas e módulos.',
          ),
          const SizedBox(height: 12),
          Expanded(
            child: GridView.count(
              crossAxisCount: cols,
              crossAxisSpacing: 14,
              mainAxisSpacing: 14,
              childAspectRatio: cols == 1 ? 2.6 : 2.2,
              children: const [
                _Tile(
                  title: 'Risk Analysis',
                  icon: Icons.troubleshoot_outlined,
                ),
                _Tile(
                  title: 'HCS Web',
                  icon: Icons.assignment_turned_in_outlined,
                ),
                _Tile(
                  title: 'Safety Observations',
                  icon: Icons.visibility_outlined,
                ),
                _Tile(title: 'Action Plan', icon: Icons.fact_check_outlined),
                _Tile(
                  title: 'Water Dams & Reservoirs',
                  icon: Icons.water_outlined,
                ),
                _Tile(title: 'MET Safety Guide', icon: Icons.build_outlined),
              ],
            ),
          ),
          const SizedBox(height: 10),
          const Text(
            'Dica: aqui entra também “APR (HCS)” como tile principal com destaque.',
            style: TextStyle(color: AppTheme.subtext, fontSize: 12),
          ),
        ],
      ),
    );
  }
}

class _Tile extends StatelessWidget {
  final String title;
  final IconData icon;

  const _Tile({required this.title, required this.icon});

  @override
  Widget build(BuildContext context) {
    return NeonCard(
      onTap: () => ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Abrir: $title (wireframe)'))),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(
          children: [
            Container(
              width: 54,
              height: 54,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.border),
                color: const Color(0xFF0B1020),
              ),
              child: Icon(icon, size: 26, color: AppTheme.neonCyan),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Text(
                title,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
            const Icon(
              Icons.arrow_forward_ios,
              size: 16,
              color: AppTheme.subtext,
            ),
          ],
        ),
      ),
    );
  }
}

import 'dart:ui';
import 'package:flutter/material.dart';

class EngesafetyHomePage extends StatelessWidget {
  const EngesafetyHomePage({super.key});

  static const _bg = Color(0xFF07122B);
  static const _surface = Color(0xFF0B1B3F);
  static const _text = Color(0xFFEAF2FF);
  static const _sub = Color(0xFFBFD3FF);
  static const _line = Color(0x1AFFFFFF);

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    final cols = width >= 1200 ? 3 : (width >= 850 ? 2 : 1);
    final wide = width >= 1100;

    return Scaffold(
      backgroundColor: _bg,
      body: Stack(
        children: [
          const _TechBackground(),
          SafeArea(
            child: Column(
              children: [
                const _TopNav(),
                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.fromLTRB(18, 18, 18, 28),
                    child: Center(
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 1200),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (wide)
                              const Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Expanded(flex: 6, child: _HeroLeft()),
                                  SizedBox(width: 14),
                                  Expanded(flex: 4, child: _HeroRight()),
                                ],
                              )
                            else ...const [
                              _HeroLeft(),
                              SizedBox(height: 14),
                              _HeroRight(),
                            ],
                            const SizedBox(height: 16),
                            const _KpiRow(),
                            const SizedBox(height: 16),
                            const _SectionHeader(
                              title: 'Módulos da Plataforma',
                              subtitle:
                                  'Tudo que você precisa para elevar o padrão de segurança com rastreabilidade, padronização e velocidade.',
                            ),
                            const SizedBox(height: 12),
                            _ModuleGrid(cols: cols),
                            const SizedBox(height: 16),
                            const _SectionHeader(
                              title: 'Por que a Engesafety?',
                              subtitle:
                                  'Design limpo, processos claros e controle total para engenharia de segurança.',
                            ),
                            const SizedBox(height: 12),
                            _BenefitsGrid(cols: cols),
                            const SizedBox(height: 16),
                            const _Card(
                              child: Text(
                                '“A plataforma trouxe padrão, rapidez e rastreabilidade. Ficou mais simples cobrar ações, reunir evidências e apresentar resultados.”\n\n— Gestão de Segurança',
                                style: TextStyle(
                                  color: _sub,
                                  height: 1.5,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                            const SizedBox(height: 16),
                            const _FinalCta(),
                            const SizedBox(height: 22),
                            const Text(
                              '© Engesafety • Consultoria em Segurança do Trabalho',
                              style: TextStyle(
                                color: Color(0xFF93A9D8),
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TopNav extends StatelessWidget {
  const _TopNav();

  @override
  Widget build(BuildContext context) {
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
        child: Container(
          height: 72,
          padding: const EdgeInsets.symmetric(horizontal: 18),
          decoration: const BoxDecoration(
            color: Color(0x9908122B),
            border: Border(bottom: BorderSide(color: EngesafetyHomePage._line)),
          ),
          child: Row(
            children: [
              Image.asset(
                'assets/brand/engesafety.png',
                height: 34,
                fit: BoxFit.contain,
              ),
              const SizedBox(width: 14),
              const Expanded(
                child: Text(
                  'ENGESAFETY • Plataforma',
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: EngesafetyHomePage._text,
                    fontWeight: FontWeight.w800,
                    letterSpacing: .6,
                  ),
                ),
              ),
              _chip('PT-BR', Icons.language),
              const SizedBox(width: 10),
              _button(
                context,
                'Entrar',
                Icons.login,
                ghost: true,
                onTap: () => Navigator.of(context).pushNamed('/login'),
              ),
              const SizedBox(width: 10),
              _button(
                context,
                'Solicitar Demo',
                Icons.rocket_launch_outlined,
                onTap: () => Navigator.of(context).pushNamed('/demo'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _chip(String label, IconData icon) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
    decoration: BoxDecoration(
      borderRadius: BorderRadius.circular(999),
      border: Border.all(color: EngesafetyHomePage._line),
      color: EngesafetyHomePage._surface,
    ),
    child: Row(
      children: [
        Icon(icon, size: 16, color: EngesafetyHomePage._text),
        const SizedBox(width: 8),
        Text(
          label,
          style: const TextStyle(color: EngesafetyHomePage._text, fontSize: 13),
        ),
      ],
    ),
  );

  Widget _button(
    BuildContext context,
    String label,
    IconData icon, {
    bool ghost = false,
    required VoidCallback onTap,
  }) => InkWell(
    onTap: onTap,
    borderRadius: BorderRadius.circular(14),
    child: Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        border: ghost ? Border.all(color: const Color(0x33FFFFFF)) : null,
        color: ghost ? const Color(0x1200D2FF) : null,
        gradient: ghost
            ? null
            : const LinearGradient(
                colors: [Color(0xFF2A6BFF), Color(0xFF00D2FF)],
              ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            size: 18,
            color: ghost ? EngesafetyHomePage._text : EngesafetyHomePage._bg,
          ),
          const SizedBox(width: 8),
          Text(
            label,
            style: TextStyle(
              color: ghost ? EngesafetyHomePage._text : EngesafetyHomePage._bg,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    ),
  );
}

class _HeroLeft extends StatelessWidget {
  const _HeroLeft();

  @override
  Widget build(BuildContext context) {
    return const _Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _Tag('Consultoria & Plataforma'),
              _Tag('Rastreabilidade'),
              _Tag('Padrão corporativo'),
            ],
          ),
          SizedBox(height: 12),
          Text(
            'Segurança do trabalho\ncom engenharia de alto nível.',
            style: TextStyle(
              color: EngesafetyHomePage._text,
              fontSize: 34,
              height: 1.08,
              fontWeight: FontWeight.w900,
            ),
          ),
          SizedBox(height: 12),
          Text(
            'Centralize APR, inspeções, planos de ação e evidências em um portal elegante e robusto.\nMenos retrabalho. Mais controle. Decisão rápida.',
            style: TextStyle(
              color: EngesafetyHomePage._sub,
              fontSize: 14.5,
              height: 1.5,
            ),
          ),
          SizedBox(height: 12),
          Text(
            'LGPD • Perfis e permissões • Auditoria de ações • Evidências e versionamento',
            style: TextStyle(color: Color(0xFF93A9D8), fontSize: 12),
          ),
        ],
      ),
    );
  }
}

class _HeroRight extends StatelessWidget {
  const _HeroRight();

  @override
  Widget build(BuildContext context) {
    return const Column(
      children: [
        _Card(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Painel Executivo',
                style: TextStyle(
                  color: EngesafetyHomePage._text,
                  fontWeight: FontWeight.w900,
                ),
              ),
              SizedBox(height: 10),
              _Mini('APR em andamento', '12', '+8%'),
              SizedBox(height: 8),
              _Mini('Planos de ação', '34', 'em dia'),
              SizedBox(height: 8),
              _Mini('Conformidade (30d)', '92%', '+3%'),
            ],
          ),
        ),
        SizedBox(height: 12),
        _Card(
          child: Row(
            children: [
              Icon(Icons.verified_outlined, color: Color(0xFF7FE7FF)),
              SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Padronização + Evidências\nPronto para auditorias e rotina corporativa.',
                  style: TextStyle(color: EngesafetyHomePage._sub, height: 1.4),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _Mini extends StatelessWidget {
  final String l;
  final String v;
  final String t;
  const _Mini(this.l, this.v, this.t);

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      borderRadius: BorderRadius.circular(14),
      color: EngesafetyHomePage._surface,
      border: Border.all(color: EngesafetyHomePage._line),
    ),
    child: Row(
      children: [
        Expanded(
          child: Text(
            '$l\n$v',
            style: const TextStyle(
              color: EngesafetyHomePage._text,
              height: 1.45,
            ),
          ),
        ),
        Text(
          t,
          style: const TextStyle(
            color: Color(0xFF7FE7FF),
            fontWeight: FontWeight.w800,
          ),
        ),
      ],
    ),
  );
}

class _KpiRow extends StatelessWidget {
  const _KpiRow();

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, c) {
      final list = const [
        _Kpi('SLA de resposta', '≤ 10 min'),
        _Kpi('Análise de docs', 'até 24h'),
        _Kpi('Rastreabilidade', 'Total'),
        _Kpi('Governança', 'Enterprise'),
      ];
      if (c.maxWidth >= 900) {
        return Row(
          children: list
              .map(
                (e) => Expanded(
                  child: Padding(padding: const EdgeInsets.all(4), child: e),
                ),
              )
              .toList(),
        );
      }
      return Column(
        children: list
            .map(
              (e) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: e,
              ),
            )
            .toList(),
      );
    },
  );
}

class _Kpi extends StatelessWidget {
  final String t;
  final String v;
  const _Kpi(this.t, this.v);

  @override
  Widget build(BuildContext context) => _Card(
    child: Text(
      '$t\n$v',
      style: const TextStyle(
        color: EngesafetyHomePage._text,
        height: 1.4,
        fontWeight: FontWeight.w800,
      ),
    ),
  );
}

class _SectionHeader extends StatelessWidget {
  final String title;
  final String subtitle;
  const _SectionHeader({required this.title, required this.subtitle});

  @override
  Widget build(BuildContext context) => _Card(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(
            color: EngesafetyHomePage._text,
            fontSize: 16,
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          subtitle,
          style: const TextStyle(color: EngesafetyHomePage._sub, height: 1.4),
        ),
      ],
    ),
  );
}

class _ModuleGrid extends StatelessWidget {
  final int cols;
  const _ModuleGrid({required this.cols});

  @override
  Widget build(BuildContext context) {
    const items = [
      ('APR / Análise de Risco', Icons.shield_outlined),
      ('Inspeções & Checklists', Icons.fact_check_outlined),
      ('Plano de Ação', Icons.task_alt_outlined),
      ('Observações de Segurança', Icons.visibility_outlined),
      ('Documentos & Padrões', Icons.folder_open_outlined),
      ('Dashboards', Icons.monitor_heart_outlined),
    ];
    return GridView.count(
      crossAxisCount: cols,
      crossAxisSpacing: 12,
      mainAxisSpacing: 12,
      childAspectRatio: cols == 1 ? 2.8 : 2.2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      children: items
          .map(
            (e) => _Card(
              child: Row(
                children: [
                  Icon(e.$2, color: const Color(0xFF7FE7FF)),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      e.$1,
                      style: const TextStyle(
                        color: EngesafetyHomePage._text,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          )
          .toList(),
    );
  }
}

class _BenefitsGrid extends StatelessWidget {
  final int cols;
  const _BenefitsGrid({required this.cols});

  @override
  Widget build(BuildContext context) {
    const items = [
      'Arquitetura limpa',
      'Perfis e permissões',
      'Padrões técnicos',
      'Mobile-first',
      'Auditoria pronta',
      'Escalável',
    ];
    return GridView.count(
      crossAxisCount: cols,
      crossAxisSpacing: 12,
      mainAxisSpacing: 12,
      childAspectRatio: cols == 1 ? 3.0 : 2.5,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      children: items
          .map(
            (e) => _Card(
              child: Text(
                e,
                style: const TextStyle(
                  color: EngesafetyHomePage._text,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          )
          .toList(),
    );
  }
}

class _FinalCta extends StatelessWidget {
  const _FinalCta();

  @override
  Widget build(BuildContext context) => const _Card(
    child: Text(
      'Leve a Engesafety para sua operação.\nQueremos te mostrar a plataforma ao vivo, com seu cenário real.',
      style: TextStyle(color: EngesafetyHomePage._sub, height: 1.45),
    ),
  );
}

class _Tag extends StatelessWidget {
  final String label;
  const _Tag(this.label);

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
    decoration: BoxDecoration(
      borderRadius: BorderRadius.circular(999),
      color: const Color(0x1A00D2FF),
      border: Border.all(color: const Color(0x3300D2FF)),
    ),
    child: Text(
      label,
      style: const TextStyle(
        color: Color(0xFF7FE7FF),
        fontWeight: FontWeight.w800,
        fontSize: 12,
      ),
    ),
  );
}

class _Card extends StatelessWidget {
  final Widget child;
  const _Card({required this.child});

  @override
  Widget build(BuildContext context) => ClipRRect(
    borderRadius: BorderRadius.circular(20),
    child: BackdropFilter(
      filter: ImageFilter.blur(sigmaX: 14, sigmaY: 14),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: EngesafetyHomePage._line),
          gradient: const LinearGradient(
            colors: [Color(0xAA0B1B3F), Color(0x7708122B)],
          ),
        ),
        child: child,
      ),
    ),
  );
}

class _TechBackground extends StatelessWidget {
  const _TechBackground();

  @override
  Widget build(BuildContext context) => CustomPaint(
    painter: _TechPainter(),
    child: Container(
      decoration: const BoxDecoration(
        gradient: RadialGradient(
          center: Alignment(-0.35, -0.6),
          radius: 1.2,
          colors: [Color(0xFF0B1B3F), Color(0xFF07122B), Color(0xFF050A18)],
        ),
      ),
    ),
  );
}

class _TechPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final glow = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1
      ..color = const Color(0x2200D2FF);
    for (int i = 0; i < 6; i++) {
      canvas.drawCircle(
        Offset(size.width * 0.78, size.height * 0.22),
        80 + (i * 55),
        glow,
      );
    }
    final line = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1
      ..color = const Color(0x14FFFFFF);
    for (int i = 0; i < 16; i++) {
      final y = i * 46.0;
      canvas.drawLine(Offset(0, y), Offset(size.width, y + 120), line);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

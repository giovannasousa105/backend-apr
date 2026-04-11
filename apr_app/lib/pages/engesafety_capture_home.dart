import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class EngesafetyCaptureHomePage extends StatefulWidget {
  const EngesafetyCaptureHomePage({super.key});

  @override
  State<EngesafetyCaptureHomePage> createState() =>
      _EngesafetyCaptureHomePageState();
}

class _EngesafetyCaptureHomePageState extends State<EngesafetyCaptureHomePage> {
  final _formKey = GlobalKey<FormState>();

  final _name = TextEditingController();
  final _email = TextEditingController();
  final _phone = TextEditingController();
  final _company = TextEditingController();

  String? _role;
  String? _segment;
  String? _sites;
  String? _tooling;
  bool _lgpd = false;
  bool _sending = false;

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _phone.dispose();
    _company.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final w = MediaQuery.of(context).size.width;
    final isWide = w >= 1100;

    return Theme(
      data: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF081A3E),
        textTheme: GoogleFonts.interTextTheme(ThemeData.dark().textTheme).apply(
          bodyColor: const Color(0xFFF3F7FF),
          displayColor: const Color(0xFFF3F7FF),
        ),
        snackBarTheme: const SnackBarThemeData(
          backgroundColor: Color(0xFF0F2B5B),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: const Color(0xFF0F2B5B),
          hintStyle: const TextStyle(color: Color(0xFF9BAECC)),
          labelStyle: const TextStyle(color: Color(0xFFCDDAF2)),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: const BorderSide(color: Color(0x1AFFFFFF)),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: const BorderSide(color: Color(0x1AFFFFFF)),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: const BorderSide(color: Color(0xFF6E89B5), width: 1.2),
          ),
        ),
      ),
      child: Scaffold(
        body: Stack(
          children: [
            const _TechBackground(),
            SafeArea(
              child: Column(
                children: [
                  const _TopBar(),
                  Expanded(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.fromLTRB(18, 18, 18, 28),
                      child: Center(
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 1200),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              if (isWide)
                                Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Expanded(
                                      flex: 6,
                                      child: _heroLeft(context),
                                    ),
                                    const SizedBox(width: 14),
                                    Expanded(
                                      flex: 4,
                                      child: _leadFormCard(context),
                                    ),
                                  ],
                                )
                              else ...[
                                _heroLeft(context),
                                const SizedBox(height: 12),
                                _leadFormCard(context),
                              ],
                              const SizedBox(height: 16),
                              _kpiStrip(),
                              const SizedBox(height: 14),
                              _painSection(),
                              const SizedBox(height: 12),
                              _solutionSection(),
                              const SizedBox(height: 12),
                              _proofSection(),
                              const SizedBox(height: 14),
                              _finalCta(context),
                              const SizedBox(height: 22),
                              const _Footer(),
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
      ),
    );
  }

  Widget _heroLeft(BuildContext context) {
    return _Glass(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: const [
              _Tag('Engenharia fina - HSE'),
              _Tag('APR + Evidencias'),
              _Tag('Governanca corporativa'),
            ],
          ),
          const SizedBox(height: 14),
          const Text(
            'Demonstracao Estrategica\npara Operacoes e Obras',
            style: TextStyle(
              fontSize: 34,
              height: 1.08,
              fontWeight: FontWeight.w900,
              letterSpacing: -0.2,
              color: Color(0xFFF3F7FF),
            ),
          ),
          const SizedBox(height: 10),
          const Text(
            'Padronize APR, inspecoes e planos de acao com rastreabilidade total.\n'
            'Troque o retrabalho e o "achismo" por decisao rapida e segura.',
            style: TextStyle(
              color: Color(0xFFCDDAF2),
              height: 1.5,
              fontSize: 14.5,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              _PrimaryButton(
                label: 'Agendar Demonstracao',
                icon: Icons.rocket_launch_outlined,
                onTap: () => _scrollToFormHint(),
              ),
              _GhostButton(
                label: 'Ver modulos',
                icon: Icons.grid_view_rounded,
                onTap: () => _toast('Scroll: modulos / secoes'),
              ),
              _GhostButton(
                label: 'Falar no WhatsApp',
                icon: Icons.chat_bubble_outline,
                onTap: () => _toast('Acao: WhatsApp (link)'),
              ),
            ],
          ),
          const SizedBox(height: 14),
          const Row(
            children: [
              Icon(Icons.lock_outline, size: 16, color: Color(0xFF9BAECC)),
              SizedBox(width: 8),
              Expanded(
                child: Text(
                  'LGPD - Perfis e permissoes - Auditoria de acoes - Evidencias e versionamento',
                  style: TextStyle(color: Color(0xFF9BAECC), fontSize: 12),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _leadFormCard(BuildContext context) {
    return _Glass(
      padding: const EdgeInsets.all(16),
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Agendar minha demonstracao',
              style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16),
            ),
            const SizedBox(height: 8),
            const Text(
              'Nao e apresentacao de telas.\n'
              'E um diagnostico do seu processo e um plano de implementacao.',
              style: TextStyle(
                color: Color(0xFFCDDAF2),
                height: 1.35,
                fontSize: 12.5,
              ),
            ),
            const SizedBox(height: 12),
            _field(_name, label: 'Nome completo', icon: Icons.person_outline),
            const SizedBox(height: 10),
            _field(
              _email,
              label: 'E-mail corporativo',
              icon: Icons.mail_outline,
              keyboard: TextInputType.emailAddress,
            ),
            const SizedBox(height: 10),
            _field(
              _phone,
              label: 'Telefone',
              icon: Icons.phone_outlined,
              keyboard: TextInputType.phone,
            ),
            const SizedBox(height: 10),
            _field(
              _company,
              label: 'Nome da empresa',
              icon: Icons.apartment_outlined,
            ),
            const SizedBox(height: 10),
            _dropdown(
              label: 'Qual o seu cargo?',
              value: _role,
              items: const [
                'Gestor (Socio/Diretor)',
                'Engenharia/Obras',
                'HSE / Seguranca',
                'Administrativo/Financeiro',
                'Consultoria Externa',
                'Outros',
              ],
              onChanged: (v) => setState(() => _role = v),
            ),
            const SizedBox(height: 10),
            _dropdown(
              label: 'Segmento',
              value: _segment,
              items: const [
                'Construcao / Obras',
                'Industria',
                'Servicos especializados',
                'Obras publicas',
                'Consultoria',
                'Outros',
              ],
              onChanged: (v) => setState(() => _segment = v),
            ),
            const SizedBox(height: 10),
            _dropdown(
              label: 'Quantos sites/obras em andamento?',
              value: _sites,
              items: const ['Nenhum', '1-2', '3-5', '+5'],
              onChanged: (v) => setState(() => _sites = v),
            ),
            const SizedBox(height: 10),
            _dropdown(
              label: 'Voce usa alguma ferramenta hoje?',
              value: _tooling,
              items: const ['Ja uso sistema', 'Uso planilhas', 'Nao uso'],
              onChanged: (v) => setState(() => _tooling = v),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Checkbox(
                  value: _lgpd,
                  onChanged: (v) => setState(() => _lgpd = v ?? false),
                ),
                const Expanded(
                  child: Text(
                    'Aceito e concordo com a Politica de Privacidade (LGPD).',
                    style: TextStyle(color: Color(0xFFCDDAF2), fontSize: 12.5),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            SizedBox(
              width: double.infinity,
              child: _PrimaryButton(
                label: _sending ? 'Enviando...' : 'Agendar Demonstracao',
                icon: Icons.calendar_month_outlined,
                disabled: _sending,
                onTap: _sending ? null : _submit,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _kpiStrip() {
    return Row(
      children: const [
        Expanded(
          child: _Kpi(title: 'SLA de resposta', value: '<= 10 min'),
        ),
        SizedBox(width: 10),
        Expanded(
          child: _Kpi(title: 'Analise de docs', value: 'ate 24h'),
        ),
        SizedBox(width: 10),
        Expanded(
          child: _Kpi(title: 'Rastreabilidade', value: 'Total'),
        ),
      ],
    );
  }

  Widget _painSection() {
    return _Glass(
      padding: const EdgeInsets.all(16),
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Os 5 viloes da rotina de seguranca',
            style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16),
          ),
          SizedBox(height: 10),
          _Bullet(
            'Dados fragmentados: planilhas, fotos soltas e versoes que nao batem.',
          ),
          _Bullet(
            "Decisao no 'feeling': sem indicadores confiaveis e auditaveis.",
          ),
          _Bullet(
            'Guerra interna: campo diferente do escritorio e evidencia perdida.',
          ),
          _Bullet(
            'Profissional caro virando digitador: tempo perdido com burocracia.',
          ),
          _Bullet(
            'Invisibilidade de risco: voce descobre tarde que a acao nao foi feita.',
          ),
        ],
      ),
    );
  }

  Widget _solutionSection() {
    return _Glass(
      padding: const EdgeInsets.all(16),
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'O diagnostico Engesafety',
            style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16),
          ),
          SizedBox(height: 8),
          Text(
            'Na demonstracao, a gente entende seu fluxo real '
            '(APR -> evidencia -> acao -> aprovacao) e desenha o plano de '
            'implementacao com governanca e padroes.',
            style: TextStyle(color: Color(0xFFCDDAF2), height: 1.4),
          ),
          SizedBox(height: 12),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              _MiniPill('Padroes tecnicos'),
              _MiniPill('Perfis e permissoes'),
              _MiniPill('Trilha de auditoria'),
              _MiniPill('Dashboards por site'),
            ],
          ),
        ],
      ),
    );
  }

  Widget _proofSection() {
    return _Glass(
      padding: const EdgeInsets.all(16),
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Prova e confianca',
            style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16),
          ),
          SizedBox(height: 10),
          _Quote(
            'Agora a evidencia fica amarrada na acao. O gestor acompanha e cobra '
            'com clareza, e a auditoria virou rotina sem correria.',
          ),
          SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: _Stat(
                  value: 'Enterprise',
                  label: 'governanca e padroes',
                ),
              ),
              SizedBox(width: 10),
              Expanded(
                child: _Stat(
                  value: 'Mobile-first',
                  label: 'campo -> evidencia',
                ),
              ),
              SizedBox(width: 10),
              Expanded(
                child: _Stat(
                  value: 'Rastreavel',
                  label: 'responsavel + versao',
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _finalCta(BuildContext context) {
    return _Glass(
      padding: const EdgeInsets.all(18),
      child: Row(
        children: [
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Pronta para profissionalizar a seguranca?',
                  style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16),
                ),
                SizedBox(height: 8),
                Text(
                  'Agende uma demonstracao estrategica e saia com um plano '
                  'de acao claro para sua operacao.',
                  style: TextStyle(color: Color(0xFFCDDAF2), height: 1.4),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          _PrimaryButton(
            label: 'Agendar agora',
            icon: Icons.rocket_launch_outlined,
            onTap: _scrollToFormHint,
          ),
        ],
      ),
    );
  }

  Widget _field(
    TextEditingController c, {
    required String label,
    required IconData icon,
    TextInputType? keyboard,
  }) {
    return TextFormField(
      controller: c,
      keyboardType: keyboard,
      validator: (v) {
        if (v == null || v.trim().isEmpty) return 'Obrigatorio';
        if (label.contains('E-mail') && !v.contains('@')) {
          return 'E-mail invalido';
        }
        return null;
      },
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon, color: const Color(0xFF9BAECC)),
      ),
    );
  }

  Widget _dropdown({
    required String label,
    required String? value,
    required List<String> items,
    required ValueChanged<String?> onChanged,
  }) {
    return DropdownButtonFormField<String>(
      initialValue: value,
      validator: (v) => (v == null || v.isEmpty) ? 'Obrigatorio' : null,
      decoration: InputDecoration(labelText: label),
      items: items
          .map((e) => DropdownMenuItem(value: e, child: Text(e)))
          .toList(),
      onChanged: onChanged,
    );
  }

  Future<void> _submit() async {
    final ok = _formKey.currentState?.validate() ?? false;
    if (!ok) return;

    if (!_lgpd) {
      _toast('Marque a concordancia com a Politica de Privacidade (LGPD).');
      return;
    }

    setState(() => _sending = true);
    await Future.delayed(const Duration(milliseconds: 900));
    if (!mounted) return;
    setState(() => _sending = false);
    _toast('Solicitacao enviada! (mock) - conectar backend aqui.');
  }

  void _toast(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  void _scrollToFormHint() {
    _toast('Dica: esta Home ja tem o formulario no topo (hero).');
  }
}

class _TopBar extends StatelessWidget {
  const _TopBar();

  @override
  Widget build(BuildContext context) {
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
        child: Container(
          height: 72,
          padding: const EdgeInsets.symmetric(horizontal: 18),
          decoration: const BoxDecoration(
            color: Color(0xAA0D2753),
            border: Border(bottom: BorderSide(color: Color(0x1AFFFFFF))),
          ),
          child: Row(
            children: [
              Image.asset(
                'assets/brand/engesafety.png',
                height: 34,
                fit: BoxFit.contain,
              ),
              const SizedBox(width: 12),
              const Expanded(
                child: Text(
                  'ENGESAFETY - Consultoria e Plataforma',
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontWeight: FontWeight.w900,
                    letterSpacing: 0.4,
                  ),
                ),
              ),
              const _Pill('PT-BR', Icons.language),
              const SizedBox(width: 10),
              const _Pill('Enterprise', Icons.verified_user_outlined),
            ],
          ),
        ),
      ),
    );
  }
}

class _Pill extends StatelessWidget {
  final String text;
  final IconData icon;
  const _Pill(this.text, this.icon);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: const Color(0x1AFFFFFF)),
        color: const Color(0xFF0F2B5B),
      ),
      child: Row(
        children: [
          Icon(icon, size: 16, color: const Color(0xFFF3F7FF)),
          const SizedBox(width: 8),
          Text(text, style: const TextStyle(fontSize: 13)),
        ],
      ),
    );
  }
}

class _Glass extends StatelessWidget {
  final Widget child;
  final EdgeInsets padding;
  const _Glass({required this.child, required this.padding});

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(22),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 14, sigmaY: 14),
        child: Container(
          padding: padding,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(22),
            border: Border.all(color: const Color(0x1AFFFFFF)),
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Color(0xCC113060), Color(0x99203A66)],
            ),
          ),
          child: child,
        ),
      ),
    );
  }
}

class _Tag extends StatelessWidget {
  final String text;
  const _Tag(this.text);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: const Color(0x334D6A99)),
        color: const Color(0x1A5E79A6),
      ),
      child: Text(
        text,
        style: const TextStyle(
          color: Color(0xFF9FB5D7),
          fontWeight: FontWeight.w800,
          fontSize: 12,
        ),
      ),
    );
  }
}

class _Kpi extends StatelessWidget {
  final String title;
  final String value;
  const _Kpi({required this.title, required this.value});

  @override
  Widget build(BuildContext context) {
    return _Glass(
      padding: const EdgeInsets.all(14),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: const Color(0x334D6A99)),
              color: const Color(0x1A5E79A6),
            ),
            child: const Icon(
              Icons.insights_outlined,
              color: Color(0xFF9FB5D7),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: Color(0xFFCDDAF2),
                    fontSize: 12,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  value,
                  style: const TextStyle(
                    fontWeight: FontWeight.w900,
                    fontSize: 16,
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

class _Bullet extends StatelessWidget {
  final String text;
  const _Bullet(this.text);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(
            Icons.check_circle_outline,
            size: 18,
            color: Color(0xFF9FB5D7),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: const TextStyle(color: Color(0xFFCDDAF2), height: 1.35),
            ),
          ),
        ],
      ),
    );
  }
}

class _MiniPill extends StatelessWidget {
  final String t;
  const _MiniPill(this.t);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: const Color(0x1AFFFFFF)),
        color: const Color(0xFF0F2B5B),
      ),
      child: Text(
        t,
        style: const TextStyle(
          color: Color(0xFFCDDAF2),
          fontWeight: FontWeight.w700,
          fontSize: 12,
        ),
      ),
    );
  }
}

class _Quote extends StatelessWidget {
  final String text;
  const _Quote(this.text);

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Icon(
          Icons.format_quote_rounded,
          color: Color(0xFF9FB5D7),
          size: 28,
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            text,
            style: const TextStyle(
              color: Color(0xFFCDDAF2),
              height: 1.5,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ],
    );
  }
}

class _Stat extends StatelessWidget {
  final String value;
  final String label;
  const _Stat({required this.value, required this.label});

  @override
  Widget build(BuildContext context) {
    return _Glass(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            value,
            style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16),
          ),
          const SizedBox(height: 6),
          Text(
            label,
            style: const TextStyle(
              color: Color(0xFFCDDAF2),
              height: 1.35,
              fontSize: 12.5,
            ),
          ),
        ],
      ),
    );
  }
}

class _PrimaryButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback? onTap;
  final bool disabled;

  const _PrimaryButton({
    required this.label,
    required this.icon,
    required this.onTap,
    this.disabled = false,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: disabled ? null : onTap,
      borderRadius: BorderRadius.circular(16),
      child: Opacity(
        opacity: disabled ? 0.7 : 1,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Color(0xFF274A7A), Color(0xFF5E769D)],
            ),
            boxShadow: const [
              BoxShadow(
                blurRadius: 16,
                offset: Offset(0, 10),
                color: Color(0x334D6A99),
              ),
            ],
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, color: const Color(0xFFF3F7FF), size: 18),
              const SizedBox(width: 10),
              Text(
                label,
                style: const TextStyle(
                  color: Color(0xFFF3F7FF),
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _GhostButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback onTap;

  const _GhostButton({
    required this.label,
    required this.icon,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0x33FFFFFF)),
          color: const Color(0x1A5E79A6),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: const Color(0xFFF3F7FF), size: 18),
            const SizedBox(width: 10),
            Text(
              label,
              style: const TextStyle(
                color: Color(0xFFF3F7FF),
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Footer extends StatelessWidget {
  const _Footer();

  @override
  Widget build(BuildContext context) {
    return const Text(
      '(c) Engesafety - Consultoria em Seguranca do Trabalho - Plataforma corporativa\\n'
      'Landing captura (demo) com governanca, rastreabilidade e padrao enterprise.',
      style: TextStyle(color: Color(0xFF9BAECC), fontSize: 12, height: 1.4),
    );
  }
}

class _TechBackground extends StatelessWidget {
  const _TechBackground();

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: _TechPainter(),
      child: Container(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(-0.35, -0.6),
            radius: 1.2,
            colors: [Color(0xFF0F2B5B), Color(0xFF081A3E), Color(0xFF050A18)],
          ),
        ),
      ),
    );
  }
}

class _TechPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final line = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1
      ..color = const Color(0x1AFFFFFF);

    final dots = Paint()..color = const Color(0x1A9EBBE8);

    for (int i = 0; i < 18; i++) {
      final y = (i * 42).toDouble();
      canvas.drawLine(Offset(0, y), Offset(size.width, y + 120), line);
    }

    for (int x = 0; x < 20; x++) {
      for (int y = 0; y < 12; y++) {
        final dx = x * (size.width / 20);
        final dy = y * (size.height / 12);
        if ((x + y) % 3 == 0) {
          canvas.drawCircle(Offset(dx, dy), 1.4, dots);
        }
      }
    }

    final glow = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1
      ..color = const Color(0x225E79A6);

    final c = Offset(size.width * 0.78, size.height * 0.22);
    for (int i = 0; i < 6; i++) {
      canvas.drawCircle(c, 80 + i * 55, glow);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

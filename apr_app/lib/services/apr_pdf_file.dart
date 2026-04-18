import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:flutter/services.dart';
import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:open_filex/open_filex.dart';

class AprPdf {
  // ================== CORES ==================
  static final PdfColor corCapa = PdfColors.blue900;
  static final PdfColor corHeaderTabela = PdfColors.grey300;

  // ================== FONTES ==================
  static late pw.Font fontRegular;
  static late pw.Font fontBold;

  static Future<void> _loadFonts() async {
    fontRegular = pw.Font.ttf(await rootBundle.load('assets/fonts/times.ttf'));
    fontBold = pw.Font.ttf(await rootBundle.load('assets/fonts/timesbd.ttf'));
  }

  // ================== ESTILOS ==================
  static pw.TextStyle titulo = pw.TextStyle(
    fontSize: 14,
    fontWeight: pw.FontWeight.bold,
    color: corCapa,
  );

  static pw.TextStyle texto = pw.TextStyle(fontSize: 12);

  static pw.TextStyle headerTabela = pw.TextStyle(
    fontSize: 11,
    fontWeight: pw.FontWeight.bold,
  );

  static const Map<String, String> _energyLabels = {
    'hydraulic': 'Hidráulica',
    'residual': 'Residual',
    'kinetic': 'Cinética',
    'mechanical': 'Mecânica',
    'electrical': 'Elétrica',
    'gravitational_potential': 'Potencial gravitacional',
    'thermal': 'Térmica',
    'pneumatic': 'Pneumática',
  };

  // ================== FUNÇÃO PRINCIPAL ==================
  static Future<void> generate(Map<String, dynamic> apr) async {
    await _loadFonts();

    final pdf = pw.Document();

    pdf.addPage(_capa(apr));
    pdf.addPage(_paginaPadrao(_identificacao(apr), apr));
    pdf.addPage(_paginaPadrao(_etapasEnergia(apr), apr));
    pdf.addPage(_paginaPadrao(_analiseRiscos(apr), apr));
    pdf.addPage(_paginaPadrao(_medidasResumo(apr), apr));

    final pdfBytes = await pdf.save();

    // ============================
    // SALVAR PDF NO WINDOWS
    // ============================
    final directory = await getApplicationDocumentsDirectory();
    final filePath =
        '${directory.path}/APR_${apr['empresa']}_${apr['data']}.pdf';

    final file = File(filePath);
    await file.writeAsBytes(pdfBytes);

    // ============================
    // ABRIR PDF AUTOMATICAMENTE
    // ============================
    await OpenFilex.open(filePath);
  }

  // ================== CAPA ==================
  static pw.Page _capa(Map<String, dynamic> apr) {
    return pw.Page(
      pageFormat: PdfPageFormat.a4,
      build: (_) {
        return pw.Container(
          color: corCapa,
          padding: pw.EdgeInsets.all(30),
          child: pw.Column(
            mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
            crossAxisAlignment: pw.CrossAxisAlignment.start,
            children: [
              pw.Row(
                mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
                children: [
                  pw.Text(
                    'LOGO HCS',
                    style: pw.TextStyle(color: PdfColors.white),
                  ),
                  pw.Text(
                    'LOGO CLIENTE',
                    style: pw.TextStyle(color: PdfColors.white),
                  ),
                ],
              ),
              pw.Text(
                'HAZARD CONTROL SYSTEM (HCS)\nANÁLISE PRELIMINAR DE RISCO',
                style: pw.TextStyle(
                  color: PdfColors.white,
                  fontSize: 18,
                  fontWeight: pw.FontWeight.bold,
                ),
              ),
              pw.Text(
                'EMPRESA: ${apr['empresa']}\nATIVIDADE: ${apr['atividade']}\nDATA: ${apr['data']}',
                style: pw.TextStyle(color: PdfColors.white),
              ),
            ],
          ),
        );
      },
    );
  }

  // ================== PÁGINA PADRÃO COM RODAPÉ ==================
  static pw.Page _paginaPadrao(pw.Widget content, Map<String, dynamic> apr) {
    return pw.Page(
      pageFormat: PdfPageFormat.a4,
      margin: pw.EdgeInsets.fromLTRB(30, 30, 30, 45),
      build: (context) {
        return pw.Stack(
          children: [
            pw.Positioned.fill(child: content),
            pw.Positioned(
              bottom: 10,
              left: 0,
              right: 0,
              child: pw.Text(
                'Hazard Control System | ${apr['empresa']} | ${apr['data']} | Página ${context.pageNumber}',
                textAlign: pw.TextAlign.center,
                style: pw.TextStyle(fontSize: 9, color: PdfColors.grey700),
              ),
            ),
          ],
        );
      },
    );
  }

  // ================== IDENTIFICAÇÃO ==================
  static pw.Widget _identificacao(Map<String, dynamic> apr) {
    return pw.Column(
      crossAxisAlignment: pw.CrossAxisAlignment.start,
      children: [
        _titulo('IDENTIFICAÇÃO DO DOCUMENTO'),
        _tabela([
          ['EMPRESA', apr['empresa'] ?? ''],
          ['ATIVIDADE', apr['atividade'] ?? ''],
          ['LOCAL', apr['local'] ?? ''],
          ['DATA DE ELABORAÇÃO', apr['data'] ?? ''],
        ]),
        pw.SizedBox(height: 16),
        _titulo('DESCRIÇÃO DA ATIVIDADE'),
        pw.Text(apr['descricao'] ?? '', style: texto),
      ],
    );
  }

  // ================== ETAPAS + ENERGIAS ==================
  static pw.Widget _etapasEnergia(Map<String, dynamic> apr) {
    return pw.Column(
      crossAxisAlignment: pw.CrossAxisAlignment.start,
      children: [
        _titulo('ETAPAS DA ATIVIDADE'),
        _tabelaEtapas(apr['etapas'] ?? []),
        pw.SizedBox(height: 16),
        _titulo('ANÁLISE DE ENERGIAS PERIGOSAS'),
        _tabelaEnergia(_resolveEnergiaTable(apr)),
      ],
    );
  }

  // ================== ANÁLISE DE RISCOS ==================
  static pw.Widget _analiseRiscos(Map<String, dynamic> apr) {
    return pw.Column(
      crossAxisAlignment: pw.CrossAxisAlignment.start,
      children: [
        _titulo('ANÁLISE DE RISCOS'),
        _tabelaRiscos(apr['riscos'] ?? []),
        pw.SizedBox(height: 16),
        _titulo('MATRIZ DE RISCO'),
        _matrizRisco(),
      ],
    );
  }

  // ================== MEDIDAS ==================
  static pw.Widget _medidasResumo(Map<String, dynamic> apr) {
    return pw.Column(
      crossAxisAlignment: pw.CrossAxisAlignment.start,
      children: [
        _titulo('MEDIDAS DE CONTROLE'),
        _tabelaMedidas(apr['medidas'] ?? []),
      ],
    );
  }

  // ================== COMPONENTES ==================
  static pw.Widget _titulo(String t) {
    return pw.Column(
      crossAxisAlignment: pw.CrossAxisAlignment.start,
      children: [
        pw.Text(t, style: titulo),
        pw.Container(height: 1, color: corCapa),
        pw.SizedBox(height: 8),
      ],
    );
  }

  static pw.Widget _tabela(List<List<String>> dados) {
    return pw.Table(
      border: pw.TableBorder.all(),
      children: dados.map((linha) {
        final isHeader = dados.indexOf(linha) == 0;
        return pw.TableRow(
          decoration: isHeader
              ? pw.BoxDecoration(color: corHeaderTabela)
              : null,
          children: linha.map((celula) {
            return pw.Padding(
              padding: pw.EdgeInsets.all(6),
              child: pw.Text(celula, style: isHeader ? headerTabela : texto),
            );
          }).toList(),
        );
      }).toList(),
    );
  }

  static pw.Widget _tabelaEtapas(List etapas) => _tabela(
    etapas.map<List<String>>((e) {
      return ['${e['numero']}', e['descricao'] ?? ''];
    }).toList(),
  );

  static pw.Widget _tabelaEnergia(List energias) => _tabela(
    energias.map<List<String>>((e) {
      return [e['tipo'] ?? '', e['existe'] ?? '', e['controle'] ?? ''];
    }).toList(),
  );

  static List<Map<String, String>> _resolveEnergiaTable(
    Map<String, dynamic> apr,
  ) {
    final checklist = apr['dangerous_energies_checklist'];
    if (checklist is Map) {
      final rows = <Map<String, String>>[];
      for (final entry in _energyLabels.entries) {
        final value = checklist[entry.key];
        final selected = value == true;
        rows.add({
          'tipo': entry.value,
          'existe': selected ? 'Sim' : 'Não',
          'controle': '',
        });
      }
      return rows;
    }

    final energias = apr['energias'];
    if (energias is List) {
      return energias
          .map<Map<String, String>>(
            (e) => {
              'tipo': (e['tipo'] ?? '').toString(),
              'existe': (e['existe'] ?? '').toString(),
              'controle': (e['controle'] ?? '').toString(),
            },
          )
          .toList();
    }

    return [];
  }

  static pw.Widget _tabelaMedidas(List medidas) => _tabela(
    medidas.map<List<String>>((m) {
      return [m['tipo'] ?? '', m['descricao'] ?? ''];
    }).toList(),
  );

  static pw.Widget _tabelaRiscos(List riscos) {
    return pw.Table(
      border: pw.TableBorder.all(),
      children: [
        pw.TableRow(
          decoration: pw.BoxDecoration(color: corHeaderTabela),
          children: [
            _cell('PERIGO'),
            _cell('CAUSA'),
            _cell('CONSEQUÊNCIA'),
            _cell('P'),
            _cell('S'),
            _cell('NÍVEL'),
          ],
        ),
        ...riscos.map<pw.TableRow>((r) {
          final nivel = r['nivel'] ?? 0;
          return pw.TableRow(
            children: [
              _cell(r['perigo']),
              _cell(r['causa']),
              _cell(r['consequencia']),
              _cell(r['p'].toString()),
              _cell(r['s'].toString()),
              pw.Container(
                alignment: pw.Alignment.center,
                color: _corRiscoNivel(nivel),
                child: pw.Text(nivel.toString()),
              ),
            ],
          );
        }),
      ],
    );
  }

  static pw.Widget _matrizRisco() {
    return pw.Table(
      border: pw.TableBorder.all(),
      children: List.generate(6, (row) {
        return pw.TableRow(
          children: List.generate(6, (col) {
            if (row == 0 && col == 0) return _cell('S \\ P');
            if (row == 0) return _cell(col.toString());
            if (col == 0) return _cell(row.toString());
            final nivel = row * col;
            return pw.Container(
              height: 22,
              alignment: pw.Alignment.center,
              color: _corRiscoNivel(nivel),
              child: pw.Text(nivel.toString()),
            );
          }),
        );
      }),
    );
  }

  static pw.Widget _cell(String? text) {
    return pw.Padding(
      padding: pw.EdgeInsets.all(5),
      child: pw.Text(text ?? ''),
    );
  }

  static PdfColor _corRiscoNivel(int nivel) {
    if (nivel <= 4) return PdfColors.green;
    if (nivel <= 9) return PdfColors.yellow;
    if (nivel <= 16) return PdfColors.orange;
    return PdfColors.red;
  }
}

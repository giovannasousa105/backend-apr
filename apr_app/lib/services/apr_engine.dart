import '../models/perigo.dart';
import '../models/epi.dart';
import '../models/salvaguarda.dart';

class AprEngine {
  /// 🔹 HOJE: dados mockados
  /// 🔹 AMANHÃ: dados do Excel / banco
  static AprResult gerarAnalise(String atividade) {
    final perigos = [
      Perigo(
        descricao: 'Queda em diferença de nível',
        consequencia: 'Ferimentos graves ou fatais',
      ),
      Perigo(
        descricao: 'Queda de objetos',
        consequencia: 'Lesões em trabalhadores abaixo',
      ),
    ];

    final epis = [
      Epi('Capacete'),
      Epi('Cinto de segurança'),
      Epi('Botina de segurança'),
      Epi('Óculos de proteção'),
    ];

    final salvaguardas = [
      Salvaguarda('Isolamento e sinalização da área'),
      Salvaguarda('Linha de vida instalada'),
      Salvaguarda('Permissão de trabalho'),
    ];

    return AprResult(perigos: perigos, epis: epis, salvaguardas: salvaguardas);
  }
}

class AprResult {
  final List<Perigo> perigos;
  final List<Epi> epis;
  final List<Salvaguarda> salvaguardas;

  AprResult({
    required this.perigos,
    required this.epis,
    required this.salvaguardas,
  });
}

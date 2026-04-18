class Perigo {
  final String descricao;
  final String consequencia;

  int probabilidade;
  int severidade;

  Perigo({
    required this.descricao,
    required this.consequencia,
    this.probabilidade = 1,
    this.severidade = 1,
  });

  // 🔢 Cálculo do risco
  int get risco => probabilidade * severidade;

  // 🎨 Classificação do risco
  String get classificacao {
    if (risco <= 4) return 'Baixo';
    if (risco <= 9) return 'Médio';
    if (risco <= 16) return 'Alto';
    return 'Crítico';
  }
}

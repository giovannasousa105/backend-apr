class Apr {
  final int? id;
  final String empresa;
  final String atividade;
  final String? atividadeId;
  final String plano;
  final String? source;

  Apr({
    this.id,
    required this.empresa,
    required this.atividade,
    this.atividadeId,
    required this.plano,
    this.source,
  });
}

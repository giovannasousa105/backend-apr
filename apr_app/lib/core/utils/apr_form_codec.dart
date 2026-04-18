class AprFormFields {
  const AprFormFields({
    this.site = '',
    this.area = '',
    this.characteristic = '',
    this.description = '',
    this.contractUnit = '',
    this.shift = '',
    this.evaluator = '',
  });

  final String site;
  final String area;
  final String characteristic;
  final String description;
  final String contractUnit;
  final String shift;
  final String evaluator;

  AprFormFields copyWith({
    String? site,
    String? area,
    String? characteristic,
    String? description,
    String? contractUnit,
    String? shift,
    String? evaluator,
  }) {
    return AprFormFields(
      site: site ?? this.site,
      area: area ?? this.area,
      characteristic: characteristic ?? this.characteristic,
      description: description ?? this.description,
      contractUnit: contractUnit ?? this.contractUnit,
      shift: shift ?? this.shift,
      evaluator: evaluator ?? this.evaluator,
    );
  }
}

class AprFormCodec {
  const AprFormCodec._();

  static String buildLocation({required String site, required String area}) {
    return _joinSections([('Site', site), ('Area/Setor', area)]);
  }

  static String buildActivity({
    required String characteristic,
    required String description,
    required String contractUnit,
    required String shift,
    required String evaluator,
  }) {
    return _joinSections([
      ('Caracteristica da atividade', characteristic),
      ('Descricao do projeto/atividade', description),
      ('Contrato/Unidade', contractUnit),
      ('Turno', shift),
      ('Elaboradores/Avaliadores', evaluator),
    ]);
  }

  static AprFormFields decode({String? location, String? activity}) {
    final locationMap = _extractSections(location);
    final activityMap = _extractSections(activity);
    return AprFormFields(
      site: locationMap['Site'] ?? '',
      area: locationMap['Area/Setor'] ?? '',
      characteristic: activityMap['Caracteristica da atividade'] ?? '',
      description: activityMap['Descricao do projeto/atividade'] ?? '',
      contractUnit: activityMap['Contrato/Unidade'] ?? '',
      shift: activityMap['Turno'] ?? '',
      evaluator: activityMap['Elaboradores/Avaliadores'] ?? '',
    );
  }

  static List<String> splitLines(String? source) {
    return (source ?? '')
        .split(RegExp(r'[\n;]+'))
        .map((value) => value.trim())
        .where((value) => value.isNotEmpty)
        .toList();
  }

  static Map<String, String> _extractSections(String? source) {
    final result = <String, String>{};
    final sections = (source ?? '').split('\n');
    for (final rawLine in sections) {
      final line = rawLine.trim();
      if (line.isEmpty || !line.contains(':')) {
        continue;
      }
      final parts = line.split(':');
      final key = parts.first.trim();
      final value = parts.sublist(1).join(':').trim();
      if (key.isNotEmpty && value.isNotEmpty) {
        result[key] = value;
      }
    }
    return result;
  }

  static String _joinSections(List<(String, String)> parts) {
    return parts
        .where((entry) => entry.$2.trim().isNotEmpty)
        .map((entry) => '${entry.$1}: ${entry.$2.trim()}')
        .join('\n');
  }
}

class ApiEpi {
  final int id;
  final String epi;
  final String? descricao;
  final String? normas;

  ApiEpi({required this.id, required this.epi, this.descricao, this.normas});

  factory ApiEpi.fromJson(Map<String, dynamic> json) {
    return ApiEpi(
      id: json['id'] as int,
      epi: (json['epi'] ?? json['name']) as String,
      descricao: json['descricao'] as String?,
      normas: json['normas'] as String?,
    );
  }
}

class ApiPerigo {
  final int id;
  final String perigo;
  final String? consequencias;
  final String? salvaguardas;
  final int defaultProbability;
  final int defaultSeverity;

  ApiPerigo({
    required this.id,
    required this.perigo,
    this.consequencias,
    this.salvaguardas,
    this.defaultProbability = 0,
    this.defaultSeverity = 0,
  });

  factory ApiPerigo.fromJson(Map<String, dynamic> json) {
    return ApiPerigo(
      id: json['id'] as int,
      perigo: (json['perigo'] ?? json['name']) as String,
      consequencias: json['consequencias'] as String?,
      salvaguardas: json['salvaguardas'] as String?,
      defaultProbability: (json['default_probability'] as num?)?.toInt() ?? 0,
      defaultSeverity: (json['default_severity'] as num?)?.toInt() ?? 0,
    );
  }
}

class ApiApr {
  final String id;
  final String titulo;
  final String risco;
  final String? local;
  final String? descricao;
  final String status;

  ApiApr({
    required this.id,
    required this.titulo,
    required this.risco,
    this.local,
    this.descricao,
    required this.status,
  });

  factory ApiApr.fromJson(Map<String, dynamic> json) {
    final idValue = json['id'];
    final tituloValue = json['titulo'] ?? json['title'];
    final riscoValue = json['risco'] ?? 'mvp';
    final descricaoValue = json['descricao'] ?? json['activity'];
    final localValue = json['worksite'] ?? json['location'] ?? json['sector'];

    return ApiApr(
      id: idValue?.toString() ?? '',
      titulo: tituloValue?.toString() ?? '',
      risco: riscoValue?.toString() ?? 'mvp',
      local: localValue?.toString(),
      descricao: descricaoValue?.toString(),
      status: json['status']?.toString() ?? 'draft',
    );
  }
}

class Paginated<T> {
  final List<T> items;
  final int total;
  final int skip;
  final int limit;

  Paginated({
    required this.items,
    required this.total,
    required this.skip,
    required this.limit,
  });
}

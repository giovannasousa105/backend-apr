import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart';
import 'auth_storage.dart';
import '../text_normalizer.dart';

class ApiService {
  final String baseUrl;

  ApiService({required this.baseUrl});

  static const String _retryPromptReforcado =
      'Exija UTF-8 v\u00e1lido e pro\u00edba o caractere de substitui\u00e7\u00e3o '
      '\uFFFD e as sequ\u00eancias \u00C3 e \u00C2.';
  static const int _defaultMaxRetries = 3;
  static const String _telemetryPath = '/v1/telemetry';
  static const Duration _requestTimeout = Duration(seconds: 25);
  static const Duration _authRequestTimeout = Duration(seconds: 60);
  static const Duration _retryDelay = Duration(seconds: 2);

  Future<http.Response> _withTimeout(
    Future<http.Response> request, {
    Duration? timeout,
    String? timeoutMessage,
  }) async {
    try {
      return await request.timeout(timeout ?? _requestTimeout);
    } on TimeoutException {
      throw TimeoutException(
        timeoutMessage ??
            'Tempo de resposta excedido. Verifique a conexao e tente novamente.',
      );
    }
  }

  Future<http.Response> _withAuthTimeout(Future<http.Response> request) {
    return _withTimeout(
      request,
      timeout: _authRequestTimeout,
      timeoutMessage:
          'Servidor iniciando. Aguarde alguns segundos e tente novamente.',
    );
  }

  Future<http.Response> _withAuthTimeoutRetry(
    Future<http.Response> Function() requestFactory,
  ) async {
    try {
      return await _withAuthTimeout(requestFactory());
    } on TimeoutException {
      await Future<void>.delayed(_retryDelay);
      return _withAuthTimeout(requestFactory());
    }
  }

  String _errorMessage(http.Response res, String fallback) {
    try {
      final decoded = json.decode(res.body);
      if (decoded is Map<String, dynamic>) {
        final message = decoded['message']?.toString();
        if (message != null && message.isNotEmpty) {
          return message;
        }
      }
    } catch (_) {}
    return fallback;
  }

  Uri _u(String path, [Map<String, dynamic>? query]) {
    final q = query?.map((k, v) => MapEntry(k, v.toString()));
    return Uri.parse(baseUrl + path).replace(queryParameters: q);
  }

  Future<Map<String, String>> _headers({bool json = false}) async {
    final headers = <String, String>{};
    if (json) {
      headers['Content-Type'] = 'application/json';
    }
    final token = await AuthStorage.getToken();
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  Future<void> _logTelemetryEvent(
    String event,
    Map<String, dynamic> data,
  ) async {
    try {
      final payload = <String, dynamic>{
        'event': event,
        'data': data,
        'ts': DateTime.now().toUtc().toIso8601String(),
      };
      final res = await http.post(
        _u(_telemetryPath),
        headers: await _headers(json: true),
        body: json.encode(payload),
      );
      if (res.statusCode >= 400) {
        debugPrint('Telemetry failed: ${res.statusCode} ${res.body}');
      }
    } catch (e) {
      debugPrint('Telemetry failed: $e');
    }
  }

  Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    final res = await _withAuthTimeoutRetry(
      () => http.post(
        _u('/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'email': email, 'password': password}),
      ),
    );
    if (res.statusCode != 200) {
      throw Exception(_errorMessage(res, 'Erro login: ${res.statusCode}'));
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> refreshSession() async {
    final headers = await _headers();
    final res = await _withAuthTimeoutRetry(
      () => http.post(_u('/auth/refresh'), headers: headers),
    );
    if (res.statusCode != 200) {
      throw Exception(_errorMessage(res, 'Erro refresh: ${res.statusCode}'));
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> createCompany({
    required String name,
    String? cnpj,
    String plan = 'free',
    String? adminName,
    String? adminEmail,
    String? adminPassword,
  }) async {
    final payload = <String, dynamic>{'name': name, 'cnpj': cnpj, 'plan': plan};
    if (adminName != null && adminName.isNotEmpty) {
      payload['admin_name'] = adminName;
    }
    if (adminEmail != null && adminEmail.isNotEmpty) {
      payload['admin_email'] = adminEmail;
    }
    if (adminPassword != null && adminPassword.isNotEmpty) {
      payload['admin_password'] = adminPassword;
    }
    final res = await http.post(
      _u('/companies'),
      headers: await _headers(json: true),
      body: json.encode(payload),
    );
    if (res.statusCode != 200) {
      throw Exception(
        _errorMessage(res, 'Erro createCompany: ${res.statusCode}'),
      );
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getMe() async {
    final headers = await _headers();
    final res = await _withAuthTimeoutRetry(
      () => http.get(_u('/auth/me'), headers: headers),
    );
    if (res.statusCode != 200) {
      throw Exception('Erro getMe: ${res.statusCode}');
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> updateApr({
    required int aprId,
    required Map<String, dynamic> payload,
  }) async {
    final res = await http.patch(
      _u('/v1/aprs/$aprId'),
      headers: await _headers(json: true),
      body: json.encode(payload),
    );
    if (res.statusCode != 200) {
      throw Exception('Erro updateApr: ${res.statusCode}');
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> updateAprStatus({
    required int aprId,
    required String status,
    String? reason,
  }) async {
    final payload = <String, dynamic>{'status': status};
    if (reason != null && reason.isNotEmpty) {
      payload['reason'] = reason;
    }
    final res = await http.patch(
      _u('/v1/aprs/$aprId/status'),
      headers: await _headers(json: true),
      body: json.encode(payload),
    );
    if (res.statusCode != 200) {
      throw Exception('Erro updateAprStatus: ${res.statusCode}');
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> replaceAprSteps({
    required int aprId,
    required List<Map<String, dynamic>> items,
  }) async {
    final res = await _withTimeout(
      http.post(
        _u('/v1/aprs/$aprId/steps/bulk'),
        headers: await _headers(json: true),
        body: json.encode({'replace': true, 'items': items}),
      ),
    );
    if (res.statusCode != 200) {
      throw Exception('Erro replaceAprSteps: ${res.statusCode}');
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<void> deleteApr(int aprId) async {
    final res = await http.delete(
      _u('/v1/aprs/$aprId'),
      headers: await _headers(),
    );
    if (res.statusCode != 200) {
      throw Exception('Erro deleteApr: ${res.statusCode}');
    }
  }

  Future<List<Map<String, dynamic>>> getAprHistory(int aprId) async {
    final res = await http.get(
      _u('/v1/aprs/$aprId/history'),
      headers: await _headers(),
    );
    if (res.statusCode != 200) {
      throw Exception('Erro getAprHistory: ${res.statusCode}');
    }
    final list = json.decode(res.body) as List<dynamic>;
    return list.map((e) => e as Map<String, dynamic>).toList();
  }

  Future<List<Map<String, dynamic>>> getActivities() async {
    final res = await http.get(_u('/v1/activities'), headers: await _headers());
    if (res.statusCode != 200) {
      throw Exception('Erro getActivities: ${res.statusCode}');
    }
    final list = json.decode(res.body) as List<dynamic>;
    return list.map((e) => e as Map<String, dynamic>).toList();
  }

  Future<Map<String, dynamic>> getActivitySuggestions(String activityId) async {
    final res = await http.get(
      _u('/v1/activities/$activityId/suggestions'),
      headers: await _headers(),
    );
    if (res.statusCode != 200) {
      throw Exception('Erro getActivitySuggestions: ${res.statusCode}');
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> resolveNormProfile({
    String? contractId,
    String? unitId,
  }) async {
    final query = <String, dynamic>{};
    if (contractId != null && contractId.trim().isNotEmpty) {
      query['contractId'] = contractId.trim();
    }
    if (unitId != null && unitId.trim().isNotEmpty) {
      query['unitId'] = unitId.trim();
    }
    final res = await http.get(
      _u('/v1/norm-profiles/resolve', query.isEmpty ? null : query),
      headers: await _headers(),
    );
    if (res.statusCode != 200) {
      throw Exception(
        _errorMessage(res, 'Erro resolveNormProfile: ${res.statusCode}'),
      );
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> updateNormProfile({
    required int profileId,
    required List<String> optionalFrameworkIds,
    String? riskEngineMode,
  }) async {
    final payload = <String, dynamic>{
      'optional_framework_ids': optionalFrameworkIds,
      if (riskEngineMode != null && riskEngineMode.trim().isNotEmpty)
        'risk_engine_mode': riskEngineMode.trim(),
    };
    final res = await http.put(
      _u('/v1/norm-profiles/$profileId'),
      headers: await _headers(json: true),
      body: json.encode(payload),
    );
    if (res.statusCode != 200) {
      throw Exception(
        _errorMessage(res, 'Erro updateNormProfile: ${res.statusCode}'),
      );
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> createUser({
    required String email,
    required String password,
    String? name,
    String role = 'tecnico',
    String? companyName,
    int? companyId,
  }) async {
    final payload = <String, dynamic>{
      'email': email,
      'password': password,
      'role': role,
    };
    if (name != null && name.isNotEmpty) {
      payload['name'] = name;
    }
    if (companyId != null) {
      payload['company_id'] = companyId;
    }
    if (companyName != null && companyName.isNotEmpty) {
      payload['company_name'] = companyName;
    }

    final res = await http.post(
      _u('/auth/users'),
      headers: await _headers(json: true),
      body: json.encode(payload),
    );
    if (res.statusCode != 200) {
      throw Exception('Erro createUser: ${res.statusCode}');
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> getCompanies() async {
    final res = await http.get(
      _u('/auth/companies'),
      headers: await _headers(),
    );
    if (res.statusCode != 200) {
      throw Exception('Erro getCompanies: ${res.statusCode}');
    }
    final list = json.decode(res.body) as List<dynamic>;
    return list.map((e) => e as Map<String, dynamic>).toList();
  }

  Future<List<Map<String, dynamic>>> getCompanyUsers() async {
    final res = await http.get(_u('/auth/users'), headers: await _headers());
    if (res.statusCode != 200) {
      throw Exception(
        _errorMessage(res, 'Erro getCompanyUsers: ${res.statusCode}'),
      );
    }
    final list = json.decode(res.body) as List<dynamic>;
    return list.map((e) => e as Map<String, dynamic>).toList();
  }

  Future<Map<String, dynamic>> createInvite({
    required String email,
    String role = 'tecnico',
  }) async {
    final res = await http.post(
      _u('/invites'),
      headers: await _headers(json: true),
      body: json.encode({'email': email, 'role': role}),
    );
    if (res.statusCode != 200) {
      throw Exception(
        _errorMessage(res, 'Erro createInvite: ${res.statusCode}'),
      );
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> getInvites() async {
    final res = await http.get(_u('/invites'), headers: await _headers());
    if (res.statusCode != 200) {
      throw Exception(_errorMessage(res, 'Erro getInvites: ${res.statusCode}'));
    }
    final list = json.decode(res.body) as List<dynamic>;
    return list.map((e) => e as Map<String, dynamic>).toList();
  }

  Future<void> revokeInvite(int inviteId) async {
    final res = await http.post(
      _u('/invites/$inviteId/revoke'),
      headers: await _headers(),
    );
    if (res.statusCode != 200) {
      throw Exception(
        _errorMessage(res, 'Erro revokeInvite: ${res.statusCode}'),
      );
    }
  }

  Future<Map<String, dynamic>> verifyInvite(String token) async {
    final res = await http.get(
      _u('/invites/verify', {'token': token}),
      headers: {'Content-Type': 'application/json'},
    );
    if (res.statusCode != 200) {
      throw Exception(
        _errorMessage(res, 'Erro verifyInvite: ${res.statusCode}'),
      );
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> acceptInvite({
    required String token,
    String? name,
    String? password,
  }) async {
    final payload = <String, dynamic>{'token': token};
    if (name != null && name.isNotEmpty) {
      payload['name'] = name;
    }
    if (password != null && password.isNotEmpty) {
      payload['password'] = password;
    }
    final res = await http.post(
      _u('/invites/accept'),
      headers: await _headers(json: true),
      body: json.encode(payload),
    );
    if (res.statusCode != 200) {
      throw Exception(
        _errorMessage(res, 'Erro acceptInvite: ${res.statusCode}'),
      );
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getEpis({int limit = 50, String? search}) async {
    final headers = await _headers();

    // Fonte principal: contrato v1 (catálogo alimentado pelo Excel no backend).
    final v1Res = await http.get(
      _u('/v1/epis', {
        'skip': 0,
        'limit': limit,
        if (search != null && search.isNotEmpty) 'search': search,
      }),
      headers: headers,
    );

    if (v1Res.statusCode == 200) {
      return json.decode(v1Res.body) as Map<String, dynamic>;
    }

    // Compatibilidade com rota legada.
    if (v1Res.statusCode == 404 || v1Res.statusCode == 405) {
      final legacyRes = await http.get(
        _u('/catalogo/epis', {
          'limit': limit,
          if (search != null && search.isNotEmpty) 'q': search,
        }),
        headers: headers,
      );
      if (legacyRes.statusCode != 200) {
        throw Exception('Erro getEpis: ${legacyRes.statusCode}');
      }
      final list = json.decode(legacyRes.body) as List<dynamic>;
      return {
        'items': list,
        'total': list.length,
        'skip': 0,
        'limit': list.length,
      };
    }

    throw Exception('Erro getEpis: ${v1Res.statusCode}');
  }

  Future<Map<String, dynamic>> getFerramentas({
    int limit = 50,
    String? search,
  }) async {
    final res = await http.get(
      _u('/catalogo/ferramentas', {
        'limit': limit,
        if (search != null && search.isNotEmpty) 'q': search,
      }),
      headers: await _headers(),
    );
    if (res.statusCode == 404 || res.statusCode == 405) {
      return _deriveFerramentasFromActivities(limit: limit, search: search);
    }
    if (res.statusCode != 200) {
      throw Exception('Erro getFerramentas: ${res.statusCode}');
    }
    final list = json.decode(res.body) as List<dynamic>;
    return {
      'items': list,
      'total': list.length,
      'skip': 0,
      'limit': list.length,
    };
  }

  static const List<String> _defaultFerramentas = <String>[
    'Furadeira',
    'Esmerilhadeira',
    'Escada',
    'Talha',
    'Ferramentas manuais',
  ];

  static const Map<String, String> _toolKeywords = <String, String>{
    'furadeira': 'Furadeira',
    'esmerilhadeira': 'Esmerilhadeira',
    'escada': 'Escada',
    'talha': 'Talha',
    'ferramentas manuais': 'Ferramentas manuais',
    'ferramenta manual': 'Ferramentas manuais',
    'ferramenta isolada': 'Ferramentas isoladas',
    'ferramentas isoladas': 'Ferramentas isoladas',
    'multimetro': 'Multimetro',
    'alicate': 'Alicate',
    'chave de fenda': 'Chave de fenda',
    'andaime': 'Andaime',
  };

  String _foldToolText(String value) {
    final normalized = TextNormalizer.normalize(value).toLowerCase();
    final map = <String, String>{
      'á': 'a',
      'à': 'a',
      'â': 'a',
      'ã': 'a',
      'é': 'e',
      'ê': 'e',
      'í': 'i',
      'ó': 'o',
      'ô': 'o',
      'õ': 'o',
      'ú': 'u',
      'ç': 'c',
    };
    var folded = normalized;
    for (final entry in map.entries) {
      folded = folded.replaceAll(entry.key, entry.value);
    }
    return folded;
  }

  Iterable<String> _extractToolsFromTexts(Iterable<String> texts) {
    final out = <String>{};
    for (final text in texts) {
      final folded = _foldToolText(text);
      if (folded.trim().isEmpty) continue;
      for (final entry in _toolKeywords.entries) {
        if (folded.contains(entry.key)) {
          out.add(entry.value);
        }
      }
    }
    return out;
  }

  Future<Map<String, dynamic>> _deriveFerramentasFromActivities({
    required int limit,
    String? search,
  }) async {
    final names = <String>{};
    final activities = await getActivities();
    final maxActivities = activities.length > 12 ? 12 : activities.length;

    for (var i = 0; i < maxActivities; i++) {
      final id = activities[i]['id']?.toString() ?? '';
      if (id.isEmpty) continue;
      try {
        final suggestion = await getActivitySuggestions(id);
        final summary =
            suggestion['suggestions'] as Map<String, dynamic>? ?? {};
        final measures = (summary['measures'] as List<dynamic>? ?? <dynamic>[])
            .map((e) => e.toString());
        final steps = (suggestion['steps'] as List<dynamic>? ?? <dynamic>[])
            .whereType<Map<String, dynamic>>();

        final texts = <String>[...measures];
        for (final step in steps) {
          texts.add(step['description']?.toString() ?? '');
          final stepMeasures =
              (step['measures'] as List<dynamic>? ?? <dynamic>[]).map(
                (e) => e.toString(),
              );
          texts.addAll(stepMeasures);
        }

        names.addAll(_extractToolsFromTexts(texts));
      } catch (_) {
        // best effort: continue with other activities
      }
    }

    names.addAll(_defaultFerramentas);
    var sorted = names.toList()..sort((a, b) => a.compareTo(b));
    if (search != null && search.trim().isNotEmpty) {
      final foldedSearch = _foldToolText(search);
      sorted = sorted
          .where((item) => _foldToolText(item).contains(foldedSearch))
          .toList();
    }
    if (sorted.length > limit) {
      sorted = sorted.sublist(0, limit);
    }
    final items = <Map<String, dynamic>>[
      for (var i = 0; i < sorted.length; i++) {'id': i + 1, 'name': sorted[i]},
    ];
    return {
      'items': items,
      'total': items.length,
      'skip': 0,
      'limit': items.length,
    };
  }

  Future<Map<String, dynamic>> getPerigos({
    int limit = 50,
    String? search,
  }) async {
    final res = await http.get(
      _u('/catalogo/perigos', {
        'limit': limit,
        if (search != null && search.isNotEmpty) 'q': search,
      }),
      headers: await _headers(),
    );
    if (res.statusCode != 200) {
      throw Exception('Erro getPerigos: ${res.statusCode}');
    }
    final list = json.decode(res.body) as List<dynamic>;
    return {
      'items': list,
      'total': list.length,
      'skip': 0,
      'limit': list.length,
    };
  }

  Future<Map<String, dynamic>> getPerigosAdmin({
    int skip = 0,
    int limit = 50,
    String? search,
  }) async {
    final res = await http.get(
      _u('/v1/perigos', {
        'skip': skip,
        'limit': limit,
        if (search != null && search.isNotEmpty) 'search': search,
      }),
      headers: await _headers(),
    );
    if (res.statusCode != 200) {
      throw Exception('Erro getPerigosAdmin: ${res.statusCode}');
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> updatePerigoDefaults({
    required int perigoId,
    int? defaultProbability,
    int? defaultSeverity,
  }) async {
    final payload = <String, dynamic>{};
    if (defaultProbability != null) {
      payload['default_probability'] = defaultProbability;
    }
    if (defaultSeverity != null) {
      payload['default_severity'] = defaultSeverity;
    }
    if (payload.isEmpty) {
      throw Exception('Payload vazio');
    }
    final res = await http.patch(
      _u('/v1/perigos/$perigoId'),
      headers: await _headers(json: true),
      body: json.encode(payload),
    );
    if (res.statusCode != 200) {
      throw Exception(
        'Erro updatePerigoDefaults: ${res.statusCode} ${res.body}',
      );
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getAprs({int skip = 0, int limit = 20}) async {
    final res = await _withTimeout(
      http.get(
        _u('/v1/aprs', {'skip': skip, 'limit': limit}),
        headers: await _headers(),
      ),
    );
    if (res.statusCode != 200) {
      throw Exception('Erro getAprs: ${res.statusCode}');
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> listAprsMvp() async {
    final res = await _withTimeout(
      http.get(_u('/aprs'), headers: await _headers()),
    );
    if (res.statusCode != 200) {
      throw Exception(
        _errorMessage(res, 'Erro listAprsMvp: ${res.statusCode}'),
      );
    }
    final decoded = json.decode(res.body);
    if (decoded is List<dynamic>) {
      return decoded.map((e) => e as Map<String, dynamic>).toList();
    }
    throw Exception('Resposta invalida em /aprs');
  }

  Future<Map<String, dynamic>> getAprMvpByExternalId(String aprId) async {
    final res = await _withTimeout(
      http.get(_u('/aprs/$aprId'), headers: await _headers()),
    );
    if (res.statusCode != 200) {
      throw Exception(_errorMessage(res, 'Erro getAprMvp: ${res.statusCode}'));
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<int?> resolveLegacyAprIdFromMvpId(String aprId) async {
    final mvp = await getAprMvpByExternalId(aprId);
    final createdAt = mvp['created_at']?.toString();
    final title = mvp['title']?.toString() ?? '';
    final location = mvp['location']?.toString() ?? '';
    final activity = mvp['activity']?.toString() ?? '';

    final legacy = await getAprs(skip: 0, limit: 200);
    final items = (legacy['items'] as List<dynamic>? ?? [])
        .whereType<Map<String, dynamic>>()
        .toList();

    Map<String, dynamic>? match;

    if (createdAt != null && createdAt.isNotEmpty) {
      for (final item in items) {
        if (item['criado_em']?.toString() == createdAt) {
          match = item;
          break;
        }
      }
    }

    match ??= items.cast<Map<String, dynamic>?>().firstWhere(
      (item) =>
          item != null &&
          item['titulo']?.toString() == title &&
          (item['worksite']?.toString() ?? '') == location &&
          (item['descricao']?.toString() ?? '') == activity,
      orElse: () => null,
    );

    if (match == null) {
      return null;
    }
    return int.tryParse(match['id']?.toString() ?? '');
  }

  Future<Map<String, dynamic>> getApr(int aprId) async {
    final res = await _withTimeout(
      http.get(_u('/v1/aprs/$aprId'), headers: await _headers()),
    );
    if (res.statusCode != 200) {
      throw Exception('Erro getApr: ${res.statusCode}');
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> createApr({
    required String obra,
    required String local,
    required String responsavel,
    required String data,
    required String atividadeId,
    required String atividadeNome,
    required String titulo,
    required String risco,
    required String descricao,
  }) async {
    final res = await http.post(
      _u('/apr'),
      headers: await _headers(json: true),
      body: json.encode({
        'obra': obra,
        'local': local,
        'responsavel': responsavel,
        'data': data,
        'atividade_id': atividadeId,
        'atividade_nome': atividadeNome,
        'titulo': titulo,
        'risco': risco,
        'descricao': descricao,
      }),
    );
    if (res.statusCode != 200) {
      throw Exception('Erro createApr: ${res.statusCode}');
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> createAprMvp({
    required String title,
    String? location,
    String? activity,
    List<Map<String, dynamic>> hazards = const [],
    List<Map<String, dynamic>> controls = const [],
  }) async {
    final res = await _withTimeout(
      http.post(
        _u('/aprs'),
        headers: await _headers(json: true),
        body: json.encode({
          'title': title,
          'location': location,
          'activity': activity,
          'hazards': hazards,
          'controls': controls,
        }),
      ),
    );
    if (res.statusCode != 200) {
      throw Exception(
        _errorMessage(res, 'Erro createAprMvp: ${res.statusCode}'),
      );
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> updateAprMvp({
    required String aprId,
    String? title,
    String? location,
    String? activity,
    List<Map<String, dynamic>>? hazards,
    List<Map<String, dynamic>>? controls,
  }) async {
    final payload = <String, dynamic>{};
    if (title != null) payload['title'] = title;
    if (location != null) payload['location'] = location;
    if (activity != null) payload['activity'] = activity;
    if (hazards != null) payload['hazards'] = hazards;
    if (controls != null) payload['controls'] = controls;

    final res = await _withTimeout(
      http.put(
        _u('/aprs/$aprId'),
        headers: await _headers(json: true),
        body: json.encode(payload),
      ),
    );
    if (res.statusCode != 200) {
      throw Exception(
        _errorMessage(res, 'Erro updateAprMvp: ${res.statusCode}'),
      );
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> submitAprMvp(String aprId) async {
    final res = await _withTimeout(
      http.post(_u('/aprs/$aprId/submit'), headers: await _headers()),
    );
    if (res.statusCode != 200) {
      throw Exception(
        _errorMessage(res, 'Erro submitAprMvp: ${res.statusCode}'),
      );
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> decideAprApproval({
    required int aprId,
    required String decision,
    String? reason,
    int? approvedByUserId,
    String? approvedByName,
    DateTime? dueAt,
  }) async {
    final payload = <String, dynamic>{
      'decision': decision,
      if (reason != null && reason.trim().isNotEmpty) 'reason': reason.trim(),
      if (approvedByUserId != null) 'approved_by_user_id': approvedByUserId,
      if (approvedByName != null && approvedByName.trim().isNotEmpty)
        'approved_by_name': approvedByName.trim(),
      if (dueAt != null) 'due_at': dueAt.toUtc().toIso8601String(),
    };

    final res = await _withTimeout(
      http.post(
        _u('/v1/aprs/$aprId/approval/decision'),
        headers: await _headers(json: true),
        body: json.encode(payload),
      ),
    );
    if (res.statusCode != 200) {
      throw Exception(
        _errorMessage(res, 'Erro decideAprApproval: ${res.statusCode}'),
      );
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> addPasso({
    required int aprId,
    required String descricao,
    String perigos = '',
    String riscos = '',
    String medidasControle = '',
    String epis = '',
    String normas = '',
  }) async {
    final res = await http.post(
      _u('/apr/$aprId/itens'),
      headers: await _headers(json: true),
      body: json.encode({
        'descricao': descricao,
        'perigos': perigos,
        'riscos': riscos,
        'medidas': medidasControle,
        'epis': epis,
        'normas': normas,
      }),
    );
    if (res.statusCode != 200) {
      throw Exception('Erro addPasso: ${res.statusCode}');
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<Uint8List> generatePdf({required int aprId}) async {
    final res = await http.post(
      _u('/apr/$aprId/gerar-pdf'),
      headers: await _headers(),
    );
    if (res.statusCode != 200) {
      throw Exception('Erro gerar PDF: ${res.statusCode}');
    }
    return res.bodyBytes;
  }

  Future<Uint8List> generateFinalPdfV1({required int aprId}) async {
    final res = await _withTimeout(
      http.get(_u('/v1/aprs/$aprId/pdf'), headers: await _headers()),
    );
    if (res.statusCode != 200) {
      throw Exception(
        _errorMessage(res, 'Erro gerar PDF final: ${res.statusCode}'),
      );
    }
    return res.bodyBytes;
  }

  Future<Map<String, dynamic>> createAprShare({required int aprId}) async {
    final res = await _withTimeout(
      http.post(_u('/v1/aprs/$aprId/share'), headers: await _headers()),
    );
    if (res.statusCode != 200) {
      throw Exception(
        _errorMessage(res, 'Erro createAprShare: ${res.statusCode}'),
      );
    }
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> uploadEvidence({
    required int aprId,
    required int passoId,
    required String filename,
    String? filePath,
    List<int>? bytes,
    String? caption,
  }) async {
    final uri = _u('/v1/aprs/$aprId/passos/$passoId/evidencia');
    final req = http.MultipartRequest('POST', uri);
    req.headers.addAll(await _headers());
    if (caption != null) {
      final normalizedCaption = TextNormalizer.normalize(caption);
      if (normalizedCaption.isNotEmpty) {
        req.fields['caption'] = normalizedCaption;
      }
    }
    if (filePath != null && filePath.isNotEmpty) {
      req.files.add(
        await http.MultipartFile.fromPath('file', filePath, filename: filename),
      );
    } else if (bytes != null) {
      req.files.add(
        http.MultipartFile.fromBytes('file', bytes, filename: filename),
      );
    } else {
      throw Exception('Arquivo de evidencia invalido');
    }

    final res = await req.send();
    final body = await res.stream.bytesToString();
    if (res.statusCode != 200) {
      throw Exception('Erro upload evidencia: ${res.statusCode} $body');
    }
    return json.decode(body) as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> gerarPassosIA({
    required int aprId,
    required String atividade,
    required String descricao,
    List<String> ferramentas = const [],
    List<String> energias = const [],
    Map<String, bool>? dangerousEnergiesChecklist,
    List<int>? imageBytes,
    int maxSteps = 6,
    int maxRetries = _defaultMaxRetries,
  }) async {
    final hasImage = imageBytes != null && imageBytes.isNotEmpty;

    if (hasImage || descricao.trim().isNotEmpty) {
      try {
        final viaV1 = await _gerarPassosIAV1(
          aprId: aprId,
          descricao: descricao.trim(),
          maxSteps: maxSteps,
          imageBytes: imageBytes,
        );
        if (viaV1.isNotEmpty) {
          return viaV1;
        }
      } catch (e) {
        debugPrint('IA /v1/aprs/$aprId/ai-steps falhou. Fallback legado: $e');
      }
    }

    final retries = maxRetries < 0 ? 0 : maxRetries;
    final attempts = retries + 1;

    for (var attempt = 0; attempt < attempts; attempt++) {
      final isRetry = attempt > 0;
      final payload = <String, dynamic>{
        'atividade': atividade,
        'descricao': descricao,
        'ferramentas': ferramentas,
        'energias': energias,
        'max_steps': maxSteps,
      };
      if (dangerousEnergiesChecklist != null) {
        payload['dangerous_energies_checklist'] = dangerousEnergiesChecklist;
      }
      if (isRetry) {
        payload['prompt_reinforced'] = _retryPromptReforcado;
        payload['forbid_chars'] = ['\uFFFD', '\u00C3', '\u00C2'];
        payload['retry_attempt'] = attempt;
      }

      final res = await http.post(
        _u('/apr/$aprId/ia-sugestoes'),
        headers: await _headers(json: true),
        body: json.encode(payload),
      );
      if (res.statusCode != 200) {
        throw Exception(_errorMessage(res, 'Erro IA: ${res.statusCode}'));
      }

      final data = json.decode(res.body) as Map<String, dynamic>;
      final legacySteps = _toLegacyAiSteps(data['passos'] ?? data['steps']);
      final normalized = TextNormalizer.normalizeAiStepsWithStatus(legacySteps);

      if (normalized.hadReplacementChar) {
        debugPrint(
          'IA output invalido (U+FFFD) apos normalizacao. '
          'Tentativa ${attempt + 1}/$attempts.',
        );
        if (attempt >= attempts - 1) {
          await _logTelemetryEvent('AI_TEXT_INVALID_ENCODING', {
            'apr_id': aprId,
            'activity': atividade,
            'max_steps': maxSteps,
            'retries': retries,
            'attempts': attempts,
          });
          throw AiTextInvalidEncodingException();
        }
        continue;
      }

      return normalized.steps;
    }

    throw AiTextInvalidEncodingException();
  }

  Future<List<Map<String, dynamic>>> _gerarPassosIAV1({
    required int aprId,
    required String descricao,
    required int maxSteps,
    List<int>? imageBytes,
  }) async {
    final req = http.MultipartRequest('POST', _u('/v1/aprs/$aprId/ai-steps'));
    req.headers.addAll(await _headers());
    req.fields['descricao'] = descricao;
    req.fields['max_steps'] = maxSteps.toString();

    if (imageBytes != null && imageBytes.isNotEmpty) {
      req.files.add(
        http.MultipartFile.fromBytes(
          'file',
          imageBytes,
          filename: 'evidencia.jpg',
        ),
      );
    }

    final streamed = await req.send();
    final body = await streamed.stream.bytesToString();
    if (streamed.statusCode != 200) {
      final parsed = http.Response(body, streamed.statusCode);
      throw Exception(
        _errorMessage(parsed, 'Erro IA v1: ${streamed.statusCode}'),
      );
    }

    final data = json.decode(body) as Map<String, dynamic>;
    final legacySteps = _toLegacyAiSteps(data['steps'] ?? data['passos']);
    final normalized = TextNormalizer.normalizeAiStepsWithStatus(legacySteps);
    if (normalized.hadReplacementChar) {
      throw AiTextInvalidEncodingException();
    }
    return normalized.steps;
  }

  List<Map<String, dynamic>> _toLegacyAiSteps(dynamic rawSteps) {
    if (rawSteps is! List) {
      return const [];
    }
    final output = <Map<String, dynamic>>[];
    for (final item in rawSteps) {
      final map = _toStringKeyedMap(item);
      if (map.isEmpty) {
        continue;
      }
      final legacy = <String, dynamic>{
        'passo': _firstNonEmpty([
          map['passo'],
          map['description'],
          map['step'],
          map['title'],
          map['titulo'],
        ]),
        'perigo': _firstNonEmpty([
          map['perigo'],
          map['hazard'],
          map['hazards'],
        ]),
        'consequencia': _firstNonEmpty([
          map['consequencia'],
          map['risk'],
          map['risks'],
          map['consequence'],
          map['consequences'],
        ]),
        'salvaguarda': _firstNonEmpty([
          map['salvaguarda'],
          map['measure'],
          map['measures'],
          map['safeguard'],
          map['safeguards'],
          map['controls'],
        ]),
        'epi': _firstNonEmpty([
          map['epi'],
          map['epis'],
          map['ppe'],
          map['ppes'],
        ]),
        'normas': _firstNonEmpty([
          map['normas'],
          map['regulations'],
          map['references'],
          map['nrs'],
          map['nr'],
        ]),
      };

      final hasAnyContent = legacy.values.any(
        (value) => value.toString().trim().isNotEmpty,
      );
      if (hasAnyContent) {
        output.add(legacy);
      }
    }
    return output;
  }

  Map<String, dynamic> _toStringKeyedMap(dynamic value) {
    if (value is! Map) {
      return const {};
    }
    final out = <String, dynamic>{};
    for (final entry in value.entries) {
      out[entry.key.toString()] = entry.value;
    }
    return out;
  }

  String _firstNonEmpty(List<dynamic> candidates) {
    for (final candidate in candidates) {
      final text = _normalizeCandidate(candidate);
      if (text.isNotEmpty) {
        return text;
      }
    }
    return '';
  }

  String _normalizeCandidate(dynamic value) {
    if (value == null) {
      return '';
    }
    if (value is List) {
      return value
          .map((e) => TextNormalizer.normalize(e.toString()))
          .where((e) => e.trim().isNotEmpty)
          .join('; ');
    }
    return TextNormalizer.normalize(value.toString());
  }
}

class AiTextInvalidEncodingException implements Exception {
  final String code;
  final String message;
  final String field;

  AiTextInvalidEncodingException({
    this.code = 'AI_TEXT_INVALID_ENCODING',
    this.message = 'Texto inv\u00e1lido retornado pela IA ap\u00f3s retries',
    this.field = 'ai_output',
  });

  Map<String, String> toJson() => {
    'code': code,
    'message': message,
    'field': field,
  };

  @override
  String toString() => json.encode(toJson());
}

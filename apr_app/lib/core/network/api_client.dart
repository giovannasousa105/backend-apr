import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../../config/api_config.dart';
import '../../features/auth/data/local/session_token_store.dart';
import 'api_exception.dart';

class ApiClient {
  ApiClient(this._tokenStore, {http.Client? httpClient})
    : _httpClient = httpClient ?? http.Client(),
      _baseUrl = resolveBaseUrl().replaceAll(RegExp(r'/+$'), '');

  final SessionTokenStore _tokenStore;
  final http.Client _httpClient;
  final String _baseUrl;

  Future<Map<String, dynamic>> get(String path) async => _sendMap('GET', path);

  Future<List<dynamic>> getList(String path) async => _sendList('GET', path);

  Future<Uint8List> getBytes(String path) async {
    final response = await _sendRaw('GET', path);
    return response.bodyBytes;
  }

  Future<Map<String, dynamic>> post(String path, {Object? body}) async =>
      _sendMap('POST', path, body: body);

  Future<Map<String, dynamic>> put(String path, {Object? body}) async =>
      _sendMap('PUT', path, body: body);

  Future<Map<String, dynamic>> patch(String path, {Object? body}) async =>
      _sendMap('PATCH', path, body: body);

  Future<Map<String, dynamic>> postMultipart(
    String path, {
    Map<String, String> fields = const {},
    String? fileField,
    String? fileName,
    List<int>? bytes,
  }) async {
    final uri = Uri.parse(_composeUrl(path));
    final request = http.MultipartRequest('POST', uri);
    request.headers.addAll(await _headers(jsonRequest: false));
    request.fields.addAll(fields);
    if (fileField != null && bytes != null && fileName != null) {
      request.files.add(
        http.MultipartFile.fromBytes(fileField, bytes, filename: fileName),
      );
    }

    final streamed = await _httpClient.send(request);
    final response = await http.Response.fromStream(streamed);
    _throwIfNeeded(response);
    final decoded = _decode(response);
    return decoded is Map<String, dynamic> ? decoded : <String, dynamic>{};
  }

  Future<Map<String, String>> _headers({bool jsonRequest = true}) async {
    final token = await _tokenStore.read();
    return <String, String>{
      if (jsonRequest) 'Content-Type': 'application/json; charset=utf-8',
      'Accept': 'application/json',
      if (token != null && token.isNotEmpty) 'Authorization': 'Bearer $token',
    };
  }

  String _composeUrl(String path) {
    if (path.startsWith('http')) {
      return path;
    }
    return '$_baseUrl/${path.replaceFirst(RegExp(r'^/+'), '')}';
  }

  Future<http.Response> _sendRaw(
    String method,
    String path, {
    Object? body,
  }) async {
    final uri = Uri.parse(_composeUrl(path));
    final headers = await _headers();
    late http.Response response;

    if (method == 'GET') {
      response = await _httpClient.get(uri, headers: headers);
    } else if (method == 'POST') {
      response = await _httpClient.post(
        uri,
        headers: headers,
        body: body == null ? null : jsonEncode(body),
      );
    } else if (method == 'PUT') {
      response = await _httpClient.put(
        uri,
        headers: headers,
        body: body == null ? null : jsonEncode(body),
      );
    } else if (method == 'PATCH') {
      response = await _httpClient.patch(
        uri,
        headers: headers,
        body: body == null ? null : jsonEncode(body),
      );
    } else {
      throw ArgumentError.value(method, 'method', 'Unsupported method');
    }

    _throwIfNeeded(response);
    return response;
  }

  Future<Map<String, dynamic>> _sendMap(
    String method,
    String path, {
    Object? body,
  }) async {
    final response = await _sendRaw(method, path, body: body);
    final decoded = _decode(response);
    return decoded is Map<String, dynamic> ? decoded : <String, dynamic>{};
  }

  Future<List<dynamic>> _sendList(
    String method,
    String path, {
    Object? body,
  }) async {
    final response = await _sendRaw(method, path, body: body);
    final decoded = _decode(response);
    return decoded is List ? decoded : <dynamic>[];
  }

  dynamic _decode(http.Response response) {
    if (response.bodyBytes.isEmpty) {
      return null;
    }
    final text = utf8.decode(response.bodyBytes);
    if (text.trim().isEmpty) {
      return null;
    }
    return jsonDecode(text);
  }

  void _throwIfNeeded(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return;
    }
    dynamic decoded;
    try {
      decoded = _decode(response);
    } catch (_) {
      decoded = null;
    }
    throw ApiException(
      message: decoded is Map<String, dynamic>
          ? (decoded['message']?.toString() ??
                decoded['detail']?.toString() ??
                'Falha na comunicacao com a API.')
          : 'Falha na comunicacao com a API.',
      statusCode: response.statusCode,
      code: decoded is Map<String, dynamic>
          ? decoded['code']?.toString()
          : null,
      field: decoded is Map<String, dynamic>
          ? decoded['field']?.toString()
          : null,
    );
  }
}

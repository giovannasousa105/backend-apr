class ApiException implements Exception {
  ApiException({required this.message, this.statusCode, this.code, this.field});

  final String message;
  final int? statusCode;
  final String? code;
  final String? field;

  @override
  String toString() => message;
}

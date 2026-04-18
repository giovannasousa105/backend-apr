import 'api_config_stub.dart' if (dart.library.io) 'api_config_io.dart';

String resolveBaseUrl() {
  const rawOverride = String.fromEnvironment('API_BASE_URL');
  final override = rawOverride.trim();
  return resolveBaseUrlImpl(override.isEmpty ? null : override);
}

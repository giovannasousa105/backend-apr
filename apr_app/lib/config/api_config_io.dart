import 'dart:io';

String resolveBaseUrlImpl(String? override) {
  const androidEmulatorHost = '10.0.2.2';
  if (override != null && override.isNotEmpty) {
    if (Platform.isAndroid &&
        (override.contains('127.0.0.1') || override.contains('localhost'))) {
      return override
          .replaceFirst('127.0.0.1', androidEmulatorHost)
          .replaceFirst('localhost', androidEmulatorHost);
    }
    return override;
  }
  if (Platform.isAndroid) {
    return 'http://$androidEmulatorHost:8000';
  }
  return 'http://127.0.0.1:8000';
}

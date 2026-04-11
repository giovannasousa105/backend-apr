import 'dart:io';

String resolveBaseUrlImpl(String? override) {
  const localLanIp = '192.168.1.67';
  if (override != null && override.isNotEmpty) {
    if (Platform.isAndroid &&
        (override.contains('127.0.0.1') || override.contains('localhost'))) {
      return override
          .replaceFirst('127.0.0.1', '10.0.2.2')
          .replaceFirst('localhost', '10.0.2.2');
    }
    return override;
  }
  if (Platform.isAndroid) {
    return 'http://$localLanIp:8000';
  }
  return 'http://127.0.0.1:8000';
}

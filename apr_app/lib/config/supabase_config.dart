class SupabaseConfig {
  SupabaseConfig._();

  /// Defaults that you should replace with values from your Supabase project.
  static const _localUrl = 'https://hrtpniackgdogtmrgrop.supabase.co';
  static const _localAnonKey = 'sb_publishable_KP6E26haQmh9p7WuzLOqgw__50ekqo4';
  static const _prodUrl = '';
  static const _prodAnonKey = '';

  static const _urlOverride = String.fromEnvironment(
    'SUPABASE_URL',
    defaultValue: '',
  );
  static const _anonKeyOverride = String.fromEnvironment(
    'SUPABASE_ANON_KEY',
    defaultValue: '',
  );
  static const _forceProduction = bool.fromEnvironment(
    'SUPABASE_PRODUCTION',
    defaultValue: false,
  );

  static bool get useProduction => _forceProduction;

  static String get url {
    if (_urlOverride.isNotEmpty) return _urlOverride;
    return useProduction ? _prodUrl : _localUrl;
  }

  static String get anonKey {
    if (_anonKeyOverride.isNotEmpty) return _anonKeyOverride;
    return useProduction ? _prodAnonKey : _localAnonKey;
  }

  static String get analyticsTag => useProduction
      ? String.fromEnvironment(
          'SUPABASE_ANALYTICS_PROD',
          defaultValue: 'prod-cart-reader',
        )
      : String.fromEnvironment(
          'SUPABASE_ANALYTICS_DEV',
          defaultValue: 'dev-cart-reader',
        );

  static void validate() {
    if (url.isEmpty || anonKey.isEmpty) {
      throw StateError(
        'Supabase credentials are missing. Define SUPABASE_URL/SUPABASE_ANON_KEY '
        'or set the production defaults in supabase_config.dart.',
      );
    }
  }
}

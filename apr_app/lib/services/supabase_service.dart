import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../config/supabase_config.dart';
import '../models/supabase_cart.dart';

class SupabaseService {
  SupabaseService._();

  static bool _initialized = false;

  static Future<void> initialize() async {
    if (_initialized) return;
    SupabaseConfig.validate();
    await Supabase.initialize(
      url: SupabaseConfig.url,
      anonKey: SupabaseConfig.anonKey,
      debug: kDebugMode,
    );
    _initialized = true;
  }

  static Future<List<SupabaseCart>> fetchCarts({int limit = 5}) async {
    final client = Supabase.instance.client;
    final response = await client
        .from('carts')
        .select()
        .order('updated_at', ascending: false)
        .limit(limit)
        .execute();

    final payload = response.data;
    final items = payload is List ? payload : <dynamic>[];
    await trackAnalytics('cart.fetch', data: {'items': items.length});
    return items
        .cast<Map<String, dynamic>>()
        .map(SupabaseCart.fromJson)
        .toList();
  }

  static Future<void> trackAnalytics(
    String event, {
    Map<String, dynamic> data = const {},
  }) async {
    final tag = SupabaseConfig.analyticsTag;
    if (tag.isEmpty) return;
    debugPrint('[$tag] $event ${data.isNotEmpty ? data : ''}');
  }
}

class SupabaseCart {
  final int id;
  final String status;
  final double total;
  final String label;
  final DateTime? updatedAt;
  final Map<String, dynamic> raw;

  SupabaseCart({
    required this.id,
    required this.status,
    required this.total,
    required this.label,
    required this.raw,
    this.updatedAt,
  });

  factory SupabaseCart.fromJson(Map<String, dynamic> json) {
    final id =
        json['id'] as int? ??
        json['cart_id'] as int? ??
        (json['id_cart'] as num?)?.toInt() ??
        0;
    final status =
        (json['status'] as String?) ?? (json['state'] as String?) ?? 'pendente';
    final total =
        (json['total'] as num?)?.toDouble() ??
        (json['value'] as num?)?.toDouble() ??
        0.0;
    final name =
        json['name'] ??
        json['label'] ??
        json['user_email'] ??
        'Usuário ${json['user_id'] ?? 'desconhecido'}';
    final updated =
        _parseDate(json['updated_at']) ?? _parseDate(json['created_at']);

    final displayLabel = 'Carrinho #$id · $name';
    return SupabaseCart(
      id: id,
      status: status,
      total: total,
      label: displayLabel,
      raw: json,
      updatedAt: updated,
    );
  }

  String get formattedTotal => 'R\$ ${total.toStringAsFixed(2)}';

  String get friendlyUpdatedAt {
    if (updatedAt == null) return '';
    return '${updatedAt!.day.toString().padLeft(2, '0')}/'
        '${updatedAt!.month.toString().padLeft(2, '0')} '
        '${updatedAt!.hour.toString().padLeft(2, '0')}:'
        '${updatedAt!.minute.toString().padLeft(2, '0')}';
  }

  static DateTime? _parseDate(Object? value) {
    if (value is DateTime) return value.toUtc();
    if (value is String) {
      return DateTime.tryParse(value)?.toUtc();
    }
    return null;
  }
}

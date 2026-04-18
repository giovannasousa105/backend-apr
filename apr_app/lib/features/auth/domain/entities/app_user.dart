class AppUser {
  const AppUser({
    required this.id,
    required this.email,
    required this.role,
    this.name,
    this.companyId,
    this.companyName,
  });

  final int id;
  final String email;
  final String role;
  final String? name;
  final int? companyId;
  final String? companyName;

  String get firstName {
    final value = (name ?? '').trim();
    if (value.isEmpty) {
      return email.split('@').first;
    }
    return value.split(' ').first;
  }
}

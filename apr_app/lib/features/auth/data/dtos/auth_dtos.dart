import '../../domain/entities/app_user.dart';
import '../../domain/entities/user_session.dart';

class AuthUserDto {
  const AuthUserDto({
    required this.id,
    required this.email,
    required this.role,
    this.name,
    this.companyId,
    this.companyName,
  });

  factory AuthUserDto.fromJson(Map<String, dynamic> json) {
    return AuthUserDto(
      id: (json['id'] as num?)?.toInt() ?? 0,
      email: json['email']?.toString() ?? '',
      role: json['role']?.toString() ?? 'tecnico',
      name: json['name']?.toString(),
      companyId: (json['company_id'] as num?)?.toInt(),
      companyName: json['company_name']?.toString(),
    );
  }

  final int id;
  final String email;
  final String role;
  final String? name;
  final int? companyId;
  final String? companyName;

  AppUser toEntity() {
    return AppUser(
      id: id,
      email: email,
      role: role,
      name: name,
      companyId: companyId,
      companyName: companyName,
    );
  }
}

class AuthSessionDto {
  const AuthSessionDto({required this.token, required this.user});

  factory AuthSessionDto.fromJson(Map<String, dynamic> json) {
    return AuthSessionDto(
      token: json['token']?.toString() ?? '',
      user: AuthUserDto.fromJson(
        (json['user'] as Map?)?.cast<String, dynamic>() ?? const {},
      ),
    );
  }

  final String token;
  final AuthUserDto user;

  UserSession toEntity() => UserSession(token: token, user: user.toEntity());
}

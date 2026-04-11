import '../../../../core/network/api_client.dart';
import '../../domain/entities/app_user.dart';
import '../../domain/entities/user_session.dart';
import '../../domain/repositories/auth_repository.dart';
import '../dtos/auth_dtos.dart';
import '../local/session_token_store.dart';

class AuthRepositoryImpl implements AuthRepository {
  AuthRepositoryImpl(this._apiClient, this._tokenStore);

  final ApiClient _apiClient;
  final SessionTokenStore _tokenStore;

  @override
  Future<UserSession> login({
    required String email,
    required String password,
  }) async {
    final response = await _apiClient.post(
      '/auth/login',
      body: <String, dynamic>{'email': email.trim(), 'password': password},
    );
    final session = AuthSessionDto.fromJson(response).toEntity();
    await _tokenStore.write(session.token);
    return session;
  }

  @override
  Future<UserSession?> restoreSession() async {
    final token = await _tokenStore.read();
    if (token == null) {
      return null;
    }

    try {
      final refreshed = await _apiClient.post('/auth/refresh');
      final session = AuthSessionDto.fromJson(refreshed).toEntity();
      await _tokenStore.write(session.token);
      return session;
    } catch (_) {
      try {
        final user = await currentUser();
        return UserSession(token: token, user: user);
      } catch (_) {
        await _tokenStore.clear();
        return null;
      }
    }
  }

  @override
  Future<AppUser> currentUser() async {
    final response = await _apiClient.get('/auth/me');
    return AuthUserDto.fromJson(response).toEntity();
  }

  @override
  Future<void> logout() async {
    await _tokenStore.clear();
  }
}

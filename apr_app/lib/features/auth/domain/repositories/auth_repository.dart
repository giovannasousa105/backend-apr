import '../entities/app_user.dart';
import '../entities/user_session.dart';

abstract class AuthRepository {
  Future<UserSession> login({required String email, required String password});

  Future<UserSession?> restoreSession();

  Future<void> logout();

  Future<AppUser> currentUser();
}

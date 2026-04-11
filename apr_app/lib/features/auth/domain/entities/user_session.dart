import 'app_user.dart';

class UserSession {
  const UserSession({required this.token, required this.user});

  final String token;
  final AppUser user;
}

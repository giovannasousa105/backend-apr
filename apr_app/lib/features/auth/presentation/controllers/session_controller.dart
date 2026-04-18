import 'package:flutter/foundation.dart';

import '../../domain/entities/app_user.dart';
import '../../domain/entities/user_session.dart';
import '../../domain/repositories/auth_repository.dart';

class SessionController extends ChangeNotifier {
  SessionController(this._repository);

  final AuthRepository _repository;

  bool _bootstrapping = true;
  bool _busy = false;
  String? _errorMessage;
  UserSession? _session;

  bool get isBootstrapping => _bootstrapping;
  bool get isBusy => _busy;
  bool get isAuthenticated => _session != null;
  String? get errorMessage => _errorMessage;
  AppUser? get currentUser => _session?.user;

  Future<void> bootstrap() async {
    if (!_bootstrapping) {
      return;
    }
    try {
      _session = await _repository.restoreSession();
    } catch (error) {
      _errorMessage = error.toString();
    } finally {
      _bootstrapping = false;
      notifyListeners();
    }
  }

  Future<bool> login({required String email, required String password}) async {
    _busy = true;
    _errorMessage = null;
    notifyListeners();
    try {
      _session = await _repository.login(email: email, password: password);
      return true;
    } catch (error) {
      _errorMessage = error.toString();
      return false;
    } finally {
      _busy = false;
      notifyListeners();
    }
  }

  Future<void> logout() async {
    _busy = true;
    notifyListeners();
    try {
      await _repository.logout();
      _session = null;
    } finally {
      _busy = false;
      notifyListeners();
    }
  }
}

import 'package:flutter/foundation.dart';

import '../../../../core/utils/view_state.dart';
import '../../../auth/presentation/controllers/session_controller.dart';
import '../../domain/entities/apr_models.dart';
import '../../domain/repositories/apr_repository.dart';

class HomePayload {
  const HomePayload({required this.items, required this.analytics});

  final List<AprSummary> items;
  final AprAnalytics analytics;
}

class HomeController extends ChangeNotifier {
  HomeController(this._repository, this.sessionController);

  final AprRepository _repository;
  final SessionController sessionController;

  ViewState<HomePayload> state = const ViewState<HomePayload>(loading: true);

  Future<void> load() async {
    state = state.copyWith(loading: true, clearError: true);
    notifyListeners();
    try {
      final items = await _repository.listAprs();
      final analytics = await _repository.loadAnalytics();
      state = ViewState<HomePayload>(
        data: HomePayload(items: items, analytics: analytics),
      );
    } catch (error) {
      state = ViewState<HomePayload>(error: error.toString());
    }
    notifyListeners();
  }
}

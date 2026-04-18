import 'package:flutter/foundation.dart';

import '../../../../core/utils/view_state.dart';
import '../../domain/entities/apr_models.dart';
import '../../domain/repositories/apr_repository.dart';

class DashboardPayload {
  const DashboardPayload({required this.analytics, required this.items});

  final AprAnalytics analytics;
  final List<AprSummary> items;
}

class DashboardController extends ChangeNotifier {
  DashboardController(this._repository);

  final AprRepository _repository;

  ViewState<DashboardPayload> state = const ViewState<DashboardPayload>(
    loading: true,
  );

  Future<void> load() async {
    state = state.copyWith(loading: true, clearError: true);
    notifyListeners();
    try {
      state = ViewState<DashboardPayload>(
        data: DashboardPayload(
          analytics: await _repository.loadAnalytics(),
          items: await _repository.listAprs(),
        ),
      );
    } catch (error) {
      state = ViewState<DashboardPayload>(error: error.toString());
    }
    notifyListeners();
  }
}

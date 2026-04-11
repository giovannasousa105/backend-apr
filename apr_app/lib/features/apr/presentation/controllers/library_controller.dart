import 'package:flutter/foundation.dart';

import '../../../../core/utils/view_state.dart';
import '../../domain/entities/apr_models.dart';
import '../../domain/repositories/apr_repository.dart';

class LibraryController extends ChangeNotifier {
  LibraryController(this._repository);

  final AprRepository _repository;

  ViewState<List<AprSummary>> state = const ViewState<List<AprSummary>>(
    loading: true,
  );
  String query = '';
  AprStatus? filter;

  List<AprSummary> get filteredItems {
    final items = state.data ?? const <AprSummary>[];
    return items.where((item) {
      final matchesQuery =
          query.trim().isEmpty ||
          item.title.toLowerCase().contains(query.trim().toLowerCase()) ||
          (item.location ?? '').toLowerCase().contains(
            query.trim().toLowerCase(),
          );
      final matchesFilter = filter == null || item.status == filter;
      return matchesQuery && matchesFilter;
    }).toList();
  }

  Future<void> load() async {
    state = state.copyWith(loading: true, clearError: true);
    notifyListeners();
    try {
      state = ViewState<List<AprSummary>>(data: await _repository.listAprs());
    } catch (error) {
      state = ViewState<List<AprSummary>>(error: error.toString());
    }
    notifyListeners();
  }

  void setQuery(String value) {
    query = value;
    notifyListeners();
  }

  void setFilter(AprStatus? value) {
    filter = value;
    notifyListeners();
  }
}

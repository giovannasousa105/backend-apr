import 'package:flutter/foundation.dart';

import '../../../../core/utils/view_state.dart';
import '../../domain/entities/apr_models.dart';
import '../../domain/repositories/apr_repository.dart';

class WorkflowController extends ChangeNotifier {
  WorkflowController(this._repository, this.aprId);

  final AprRepository _repository;
  final String aprId;

  ViewState<AprDetail> state = const ViewState<AprDetail>(loading: true);
  bool actionBusy = false;

  Future<void> load({bool ensureLegacy = false}) async {
    state = state.copyWith(loading: true, clearError: true);
    notifyListeners();
    try {
      state = ViewState<AprDetail>(
        data: await _repository.loadAprDetail(
          aprId,
          ensureLegacy: ensureLegacy,
        ),
      );
    } catch (error) {
      state = ViewState<AprDetail>(error: error.toString());
    }
    notifyListeners();
  }

  Future<void> saveBase(AprFormDraft draft) async {
    await _guard(() async {
      state = ViewState<AprDetail>(
        data: await _repository.saveAprBase(aprId, draft),
      );
    });
  }

  Future<void> saveControls(ControlsDraft draft) async {
    await _guard(() async {
      state = ViewState<AprDetail>(
        data: await _repository.saveControls(aprId, draft),
      );
    });
  }

  Future<void> submitForApproval() async {
    await _guard(() async {
      state = ViewState<AprDetail>(
        data: await _repository.submitForApproval(aprId),
      );
    });
  }

  Future<void> approve({required String approver, String? note}) async {
    await _guard(() async {
      state = ViewState<AprDetail>(
        data: await _repository.approve(aprId, approver: approver, note: note),
      );
    });
  }

  Future<void> updateExecution({
    DateTime? startedAt,
    DateTime? pausedAt,
    DateTime? finishedAt,
    String? notes,
    List<bool>? checklist,
  }) async {
    await _guard(() async {
      state = ViewState<AprDetail>(
        data: await _repository.updateExecution(
          aprId,
          startedAt: startedAt,
          pausedAt: pausedAt,
          finishedAt: finishedAt,
          notes: notes,
          checklist: checklist,
        ),
      );
    });
  }

  Future<List<int>> exportPdf() async {
    List<int>? bytes;
    await _guard(() async {
      bytes = await _repository.exportPdf(aprId);
    });
    return bytes ?? const <int>[];
  }

  Future<String> sharePdf() async {
    String? value;
    await _guard(() async {
      value = await _repository.sharePdf(aprId);
    });
    return value ?? '';
  }

  Future<void> _guard(Future<void> Function() action) async {
    actionBusy = true;
    state = state.copyWith(clearError: true);
    notifyListeners();
    try {
      await action();
    } catch (error) {
      state = state.copyWith(error: error.toString());
    } finally {
      actionBusy = false;
      notifyListeners();
    }
  }
}

import '../entities/apr_models.dart';

abstract class AprRepository {
  Future<List<AprSummary>> listAprs();

  Future<AprDetail> loadAprDetail(String aprId, {bool ensureLegacy = false});

  Future<AprSummary> createApr(AprFormDraft draft);

  Future<AprDetail> saveAprBase(String aprId, AprFormDraft draft);

  Future<AprDetail> saveControls(String aprId, ControlsDraft draft);

  Future<AprDetail> submitForApproval(String aprId);

  Future<AprDetail> approve(
    String aprId, {
    required String approver,
    String? note,
  });

  Future<AprDetail> updateExecution(
    String aprId, {
    DateTime? startedAt,
    DateTime? pausedAt,
    DateTime? finishedAt,
    String? notes,
    List<bool>? checklist,
  });

  Future<List<int>> exportPdf(String aprId);

  Future<String> sharePdf(String aprId);

  Future<AprAnalytics> loadAnalytics();
}

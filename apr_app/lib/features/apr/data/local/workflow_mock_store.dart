import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../../domain/entities/apr_models.dart';

class WorkflowMockStore {
  static const _approvalPrefix = 'workflow_approval_';
  static const _executionPrefix = 'workflow_execution_';

  Future<ApprovalMeta> readApproval(String aprId) async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString('$_approvalPrefix$aprId');
    if (raw == null || raw.isEmpty) {
      return const ApprovalMeta();
    }
    final json = jsonDecode(raw) as Map<String, dynamic>;
    return ApprovalMeta(
      approvedBy: json['approvedBy']?.toString(),
      approvedAt: DateTime.tryParse(json['approvedAt']?.toString() ?? ''),
      lastComment: json['lastComment']?.toString(),
    );
  }

  Future<void> writeApproval(String aprId, ApprovalMeta meta) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      '$_approvalPrefix$aprId',
      jsonEncode(<String, dynamic>{
        'approvedBy': meta.approvedBy,
        'approvedAt': meta.approvedAt?.toIso8601String(),
        'lastComment': meta.lastComment,
      }),
    );
  }

  Future<ExecutionMeta> readExecution(String aprId) async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString('$_executionPrefix$aprId');
    if (raw == null || raw.isEmpty) {
      return const ExecutionMeta();
    }
    final json = jsonDecode(raw) as Map<String, dynamic>;
    return ExecutionMeta(
      startedAt: DateTime.tryParse(json['startedAt']?.toString() ?? ''),
      pausedAt: DateTime.tryParse(json['pausedAt']?.toString() ?? ''),
      finishedAt: DateTime.tryParse(json['finishedAt']?.toString() ?? ''),
      notes: json['notes']?.toString() ?? '',
      checklist: ((json['checklist'] as List?) ?? const <dynamic>[])
          .map((item) => item == true)
          .toList(),
    );
  }

  Future<void> writeExecution(String aprId, ExecutionMeta meta) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      '$_executionPrefix$aprId',
      jsonEncode(<String, dynamic>{
        'startedAt': meta.startedAt?.toIso8601String(),
        'pausedAt': meta.pausedAt?.toIso8601String(),
        'finishedAt': meta.finishedAt?.toIso8601String(),
        'notes': meta.notes,
        'checklist': meta.checklist,
      }),
    );
  }
}

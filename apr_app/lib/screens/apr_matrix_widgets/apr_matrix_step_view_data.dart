import 'dart:typed_data';

import 'package:flutter/material.dart';

class AprMatrixStepViewData {
  final int keyId;
  final int index;
  final String title;
  final String hazards;
  final String consequences;
  final String safeguards;
  final String epis;
  final String norms;
  final String? evidenceName;
  final Uint8List? evidencePreviewBytes;
  final bool hasEvidence;
  final int riskScore;
  final String riskLevel;
  final Color riskColor;
  final bool generatingEvidence;

  const AprMatrixStepViewData({
    required this.keyId,
    required this.index,
    required this.title,
    required this.hazards,
    required this.consequences,
    required this.safeguards,
    required this.epis,
    required this.norms,
    required this.evidenceName,
    required this.evidencePreviewBytes,
    required this.hasEvidence,
    required this.riskScore,
    required this.riskLevel,
    required this.riskColor,
    required this.generatingEvidence,
  });
}

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'app_colors.dart';

class AppTextStyles {
  const AppTextStyles._();

  static TextTheme textTheme() {
    final bodyBase = GoogleFonts.manrope(
      color: AppColors.text,
      fontWeight: FontWeight.w600,
      letterSpacing: 0,
    );
    final displayBase = GoogleFonts.sora(
      color: AppColors.text,
      fontWeight: FontWeight.w600,
      letterSpacing: 0,
    );

    return TextTheme(
      displayLarge: displayBase.copyWith(
        fontSize: 48,
        height: 1.08,
        fontWeight: FontWeight.w600,
      ),
      displayMedium: displayBase.copyWith(
        fontSize: 36,
        height: 1.12,
        fontWeight: FontWeight.w600,
      ),
      displaySmall: displayBase.copyWith(
        fontSize: 28,
        height: 1.18,
        fontWeight: FontWeight.w600,
      ),
      headlineLarge: displayBase.copyWith(
        fontSize: 24,
        height: 1.2,
        fontWeight: FontWeight.w600,
      ),
      headlineMedium: displayBase.copyWith(
        fontSize: 20,
        height: 1.22,
        fontWeight: FontWeight.w600,
      ),
      headlineSmall: displayBase.copyWith(
        fontSize: 18,
        height: 1.26,
        fontWeight: FontWeight.w600,
      ),
      titleLarge: bodyBase.copyWith(
        fontSize: 18,
        height: 1.24,
        fontWeight: FontWeight.w700,
      ),
      titleMedium: bodyBase.copyWith(
        fontSize: 16,
        height: 1.3,
        fontWeight: FontWeight.w700,
      ),
      titleSmall: bodyBase.copyWith(
        fontSize: 14,
        height: 1.3,
        fontWeight: FontWeight.w700,
      ),
      bodyLarge: bodyBase.copyWith(
        fontSize: 15,
        height: 1.5,
        fontWeight: FontWeight.w600,
      ),
      bodyMedium: bodyBase.copyWith(
        fontSize: 14,
        height: 1.5,
        fontWeight: FontWeight.w500,
      ),
      bodySmall: bodyBase.copyWith(
        fontSize: 12,
        height: 1.45,
        fontWeight: FontWeight.w500,
      ),
      labelLarge: bodyBase.copyWith(
        fontSize: 14,
        height: 1.2,
        fontWeight: FontWeight.w700,
      ),
      labelMedium: bodyBase.copyWith(
        fontSize: 12,
        height: 1.2,
        fontWeight: FontWeight.w700,
      ),
      labelSmall: bodyBase.copyWith(
        fontSize: 11,
        height: 1.2,
        fontWeight: FontWeight.w700,
      ),
    );
  }
}

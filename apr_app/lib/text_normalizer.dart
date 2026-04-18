import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:unorm_dart/unorm_dart.dart' as unorm;

class TextNormalizer {
  static const String defaultReplacementChar = '';
  static const String _replacementChar = '\uFFFD';

  static const Map<String, String> _mojibakeReplacements = {
    '\u00c3\u00a7': '\u00e7',
    '\u00c3\u00a3': '\u00e3',
    '\u00c3\u00a1': '\u00e1',
    '\u00c3\u00a0': '\u00e0',
    '\u00c3\u00a2': '\u00e2',
    '\u00c3\u00a4': '\u00e4',
    '\u00c3\u00a9': '\u00e9',
    '\u00c3\u00aa': '\u00ea',
    '\u00c3\u00a8': '\u00e8',
    '\u00c3\u00ad': '\u00ed',
    '\u00c3\u00b3': '\u00f3',
    '\u00c3\u00b4': '\u00f4',
    '\u00c3\u00b5': '\u00f5',
    '\u00c3\u00ba': '\u00fa',
    '\u00c3\u00bc': '\u00fc',
    '\u00c3\u00b1': '\u00f1',
    '\u00c3\u0087': '\u00c7',
    '\u00c3\u0083': '\u00c3',
    '\u00c3\u0081': '\u00c1',
    '\u00c3\u0080': '\u00c0',
    '\u00c3\u0082': '\u00c2',
    '\u00c3\u0084': '\u00c4',
    '\u00c3\u0089': '\u00c9',
    '\u00c3\u008a': '\u00ca',
    '\u00c3\u0088': '\u00c8',
    '\u00c3\u008d': '\u00cd',
    '\u00c3\u0093': '\u00d3',
    '\u00c3\u0094': '\u00d4',
    '\u00c3\u0095': '\u00d5',
    '\u00c3\u009a': '\u00da',
    '\u00c3\u009c': '\u00dc',
    '\u00c3\u0091': '\u00d1',
    '\u00c2\u00b0': '\u00b0',
    '\u00c2\u00ba': '\u00ba',
    '\u00c2\u00aa': '\u00aa',
    '\u00c2\u00b4': '\u00b4',
    '\u00c2\u00b7': '\u00b7',
    '\u00c2\u00a0': ' ',
    '\u00e2\u0080\u009c': '\u201c',
    '\u00e2\u0080\u009d': '\u201d',
    '\u00e2\u0080\u0098': '\u2018',
    '\u00e2\u0080\u0099': '\u2019',
    '\u00e2\u0080\u0093': '\u2013',
    '\u00e2\u0080\u0094': '\u2014',
    '\u00e2\u0080\u00a6': '\u2026',
    '\u00e2\u0080\u00a2': '\u2022',
    '\u00e2\u0082\u00ac': '\u20ac',
    '\u00e2\u0084\u00a2': '\u2122',
  };

  static const Set<int> _invisibleChars = {
    0x00AD, // soft hyphen
    0x200B, // zero-width space
    0x200C, // zero-width non-joiner
    0x200D, // zero-width joiner
    0x2060, // word joiner
    0xFEFF, // BOM / zero-width no-break space
  };

  static String normalize(
    String input, {
    String replacementChar = defaultReplacementChar,
  }) {
    return normalizeWithStatus(input, replacementChar: replacementChar).text;
  }

  static ({String text, bool hadReplacementChar}) normalizeWithStatus(
    String input, {
    String replacementChar = defaultReplacementChar,
  }) {
    if (input.isEmpty) return (text: '', hadReplacementChar: false);

    var text = _fixMojibake(input);
    text = unorm.nfkc(text);
    text = _stripInvalid(text);
    text = _normalizeNewlines(text);
    text = _cleanupSpaces(text);

    final hasReplacementChar = text.contains(_replacementChar);
    if (hasReplacementChar) {
      debugPrint('TextNormalizer: replacement char found after normalization.');
      text = text.replaceAll(_replacementChar, replacementChar);
    }

    return (text: text, hadReplacementChar: hasReplacementChar);
  }

  static String normalizeValue(
    dynamic value, {
    String replacementChar = defaultReplacementChar,
  }) {
    if (value == null) return '';
    if (value is List) {
      final joined = value
          .map((e) => e.toString().trim())
          .where((e) => e.isNotEmpty)
          .join('; ');
      return normalize(joined, replacementChar: replacementChar);
    }
    return normalize(value.toString(), replacementChar: replacementChar);
  }

  static ({String text, bool hadReplacementChar}) normalizeValueWithStatus(
    dynamic value, {
    String replacementChar = defaultReplacementChar,
  }) {
    if (value == null) {
      return (text: '', hadReplacementChar: false);
    }
    if (value is List) {
      final joined = value
          .map((e) => e.toString().trim())
          .where((e) => e.isNotEmpty)
          .join('; ');
      return normalizeWithStatus(joined, replacementChar: replacementChar);
    }
    return normalizeWithStatus(
      value.toString(),
      replacementChar: replacementChar,
    );
  }

  static List<Map<String, dynamic>> normalizeAiSteps(
    List<dynamic> steps, {
    String replacementChar = defaultReplacementChar,
  }) {
    return normalizeAiStepsWithStatus(
      steps,
      replacementChar: replacementChar,
    ).steps;
  }

  static ({List<Map<String, dynamic>> steps, bool hadReplacementChar})
  normalizeAiStepsWithStatus(
    List<dynamic> steps, {
    String replacementChar = defaultReplacementChar,
  }) {
    var hadReplacementChar = false;
    final normalized = <Map<String, dynamic>>[];

    for (final step in steps) {
      final map = <String, dynamic>{};
      if (step is Map) {
        for (final entry in step.entries) {
          map[entry.key.toString()] = entry.value;
        }
      }

      final passoRes = normalizeValueWithStatus(
        map['passo'],
        replacementChar: replacementChar,
      );
      final perigoRes = normalizeValueWithStatus(
        map['perigo'],
        replacementChar: replacementChar,
      );
      final consequenciaRes = normalizeValueWithStatus(
        map['consequencia'],
        replacementChar: replacementChar,
      );
      final salvaguardaRes = normalizeValueWithStatus(
        map['salvaguarda'],
        replacementChar: replacementChar,
      );
      final epiRes = normalizeValueWithStatus(
        map['epi'],
        replacementChar: replacementChar,
      );

      hadReplacementChar =
          hadReplacementChar ||
          passoRes.hadReplacementChar ||
          perigoRes.hadReplacementChar ||
          consequenciaRes.hadReplacementChar ||
          salvaguardaRes.hadReplacementChar ||
          epiRes.hadReplacementChar;

      final normalizedMap = <String, dynamic>{};
      for (final entry in map.entries) {
        final key = entry.key;
        if (key == 'passo' ||
            key == 'perigo' ||
            key == 'consequencia' ||
            key == 'salvaguarda' ||
            key == 'epi') {
          continue;
        }
        if (entry.value is String || entry.value is List) {
          final res = normalizeValueWithStatus(
            entry.value,
            replacementChar: replacementChar,
          );
          hadReplacementChar = hadReplacementChar || res.hadReplacementChar;
          normalizedMap[key] = res.text;
        } else {
          normalizedMap[key] = entry.value;
        }
      }

      normalizedMap['passo'] = passoRes.text;
      normalizedMap['perigo'] = perigoRes.text;
      normalizedMap['consequencia'] = consequenciaRes.text;
      normalizedMap['salvaguarda'] = salvaguardaRes.text;
      normalizedMap['epi'] = epiRes.text;

      normalized.add(normalizedMap);
    }

    return (steps: normalized, hadReplacementChar: hadReplacementChar);
  }

  static String _fixMojibake(String text) {
    var currentScore = _mojibakeScore(text);
    if (currentScore == 0) return text;

    var result = text;

    if (_isLatin1(result)) {
      for (var i = 0; i < 2; i++) {
        final decoded = _latin1ToUtf8(result);
        if (decoded == result) break;
        final decodedScore = _mojibakeScore(decoded);
        if (decodedScore >= currentScore) break;
        result = decoded;
        currentScore = decodedScore;
      }
    }

    if (currentScore > 0) {
      for (final entry in _mojibakeReplacements.entries) {
        result = result.replaceAll(entry.key, entry.value);
      }
    }

    return result;
  }

  static int _mojibakeScore(String text) {
    var score = 0;
    for (final rune in text.runes) {
      if (rune == 0x00C3 || rune == 0x00C2) {
        score += 2;
      } else if (rune == 0x00E2) {
        score += 1;
      }
    }
    if (text.contains(_replacementChar)) {
      score += 5;
    }
    return score;
  }

  static bool _isLatin1(String text) {
    for (final unit in text.codeUnits) {
      if (unit > 0xFF) return false;
    }
    return true;
  }

  static String _latin1ToUtf8(String text) {
    final bytes = latin1.encode(text);
    return utf8.decode(bytes, allowMalformed: true);
  }

  static String _stripInvalid(String text) {
    final buffer = StringBuffer();
    for (final rune in text.runes) {
      if (rune == 0x0A || rune == 0x0D) {
        buffer.writeCharCode(rune);
        continue;
      }
      if (rune == 0x09) {
        buffer.write(' ');
        continue;
      }
      if (rune <= 0x1F || (rune >= 0x7F && rune <= 0x9F)) {
        continue;
      }
      if (_invisibleChars.contains(rune)) {
        continue;
      }
      buffer.writeCharCode(rune);
    }
    return buffer.toString();
  }

  static String _normalizeNewlines(String text) {
    final normalized = text.replaceAll('\r\n', '\n').replaceAll('\r', '\n');
    final lines = normalized.split('\n');
    final buffer = StringBuffer();
    var wroteContent = false;
    var previousBlank = false;

    for (final rawLine in lines) {
      final line = rawLine.trim();
      if (line.isEmpty) {
        if (wroteContent && !previousBlank) {
          buffer.write('\n\n');
          previousBlank = true;
        }
        continue;
      }

      if (wroteContent && !previousBlank) {
        buffer.write(' ');
      }
      buffer.write(line);
      wroteContent = true;
      previousBlank = false;
    }

    return buffer.toString();
  }

  static String _cleanupSpaces(String text) {
    var result = text.replaceAll(RegExp(r'[ \t]{2,}'), ' ');
    result = result.replaceAll(RegExp(r' *\n *'), '\n');
    return result.trim();
  }
}

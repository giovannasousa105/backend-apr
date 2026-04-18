import 'package:intl/intl.dart';

class AppFormatters {
  const AppFormatters._();

  static final DateFormat _date = DateFormat('dd/MM/yyyy');
  static final DateFormat _dateTime = DateFormat('dd/MM/yyyy • HH:mm');

  static String date(DateTime? value) {
    if (value == null) {
      return 'Sem data';
    }
    return _date.format(value.toLocal());
  }

  static String dateTime(DateTime? value) {
    if (value == null) {
      return 'Sem registro';
    }
    return _dateTime.format(value.toLocal());
  }

  static String compactInt(num value) {
    if (value >= 1000000) {
      return '${(value / 1000000).toStringAsFixed(1)}M';
    }
    if (value >= 1000) {
      return '${(value / 1000).toStringAsFixed(1)}k';
    }
    return value.toStringAsFixed(value.truncateToDouble() == value ? 0 : 1);
  }

  static String percent(num value) {
    return '${value.toStringAsFixed(value.truncateToDouble() == value ? 0 : 1)}%';
  }
}

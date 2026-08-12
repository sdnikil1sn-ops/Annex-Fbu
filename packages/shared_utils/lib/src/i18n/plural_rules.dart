/// ICU plural category selection (ADR-0007).
///
/// The backend stores one canonical plural form per key; clients expand
/// placeholders and pick the right form using these categories
/// (`zero | one | two | few | many | other`), the standard ICU set.
library;

/// Returns the ICU plural category for [count] in [locale].
///
/// Rules approximate CLDR cardinal rules for the seeded languages; the
/// fallback (`one`/`other`) matches English and most Romance languages.
String pluralCategory(String locale, int count) {
  final code = _baseCode(locale);
  switch (code) {
    case 'ar':
      if (count == 0) {
        return 'zero';
      }
      if (count == 1) {
        return 'one';
      }
      if (count == 2) {
        return 'two';
      }
      final mod100 = count % 100;
      if (mod100 >= 3 && mod100 <= 10) {
        return 'few';
      }
      if (mod100 >= 11 && mod100 <= 99) {
        return 'many';
      }
      return 'other';
    case 'fr':
      // French counts 0 and 1 as singular.
      if (count == 0 || count == 1) {
        return 'one';
      }
      return 'other';
    case 'ru':
    case 'uk':
      final mod10 = count % 10;
      final mod100 = count % 100;
      if (mod10 == 1 && mod100 != 11) {
        return 'one';
      }
      if (mod10 >= 2 && mod10 <= 4 && !(mod100 >= 12 && mod100 <= 14)) {
        return 'few';
      }
      if (mod10 == 0 ||
          (mod10 >= 5 && mod10 <= 9) ||
          (mod100 >= 11 && mod100 <= 14)) {
        return 'many';
      }
      return 'other';
    case 'ja':
    case 'zh':
    case 'ko':
      // No grammatical number.
      return 'other';
    default:
      return count == 1 ? 'one' : 'other';
  }
}

/// The primary language subtag of a locale tag (`pt-BR` -> `pt`).
String _baseCode(String locale) {
  final normalized = locale.trim().toLowerCase();
  final dash = normalized.indexOf('-');
  return dash == -1 ? normalized : normalized.substring(0, dash);
}

/// Pure-Dart utilities shared by all ANNEX apps.
///
/// No Flutter imports and no platform channels — everything here runs
/// anywhere Dart runs (ADR-0007 key registry and locale resolution).
library;

export 'src/i18n/locale_resolver.dart';
export 'src/i18n/plural_rules.dart';
export 'src/i18n/string_keys.dart';
export 'src/validation/language_tag.dart';

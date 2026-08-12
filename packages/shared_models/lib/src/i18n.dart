/// Runtime i18n models (ADR-0007).
///
/// Shapes mirror the backend bundle endpoints:
/// `GET /v1/i18n/locales` and `GET /v1/i18n/bundles/{locale}`.
library;

/// One enabled locale with its fallback parent.
class LocaleInfo {
  const LocaleInfo({required this.code, this.fallbackCode});

  final String code;

  /// Parent locale code, or null for the default locale.
  final String? fallbackCode;

  factory LocaleInfo.fromJson(Map<String, dynamic> json) {
    final code = json['code'];
    if (code is! String || code.isEmpty) {
      throw const FormatException('Locale requires a code');
    }
    return LocaleInfo(
        code: code, fallbackCode: json['fallback_code'] as String?);
  }

  Map<String, dynamic> toJson() =>
      {'code': code, 'fallback_code': fallbackCode};
}

/// The locale registry served by `GET /v1/i18n/locales`.
class LocaleList {
  const LocaleList({required this.defaultLocale, required this.locales});

  final String defaultLocale;
  final List<LocaleInfo> locales;

  factory LocaleList.fromJson(Map<String, dynamic> json) {
    final defaultLocale = json['default_locale'];
    final locales = json['locales'];
    if (defaultLocale is! String) {
      throw const FormatException('Locale list requires default_locale');
    }
    if (locales is! List) {
      throw const FormatException('Locale list requires a locales list');
    }
    return LocaleList(
      defaultLocale: defaultLocale,
      locales: locales
          .map((item) =>
              LocaleInfo.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() => {
        'default_locale': defaultLocale,
        'locales': locales.map((locale) => locale.toJson()).toList(),
      };
}

/// One translated string: the value plus its ICU plural category.
class BundleEntry {
  const BundleEntry({required this.value, required this.plural});

  final String value;

  /// ICU plural category of the stored form (`none` when invariant).
  final String plural;

  factory BundleEntry.fromJson(Map<String, dynamic> json) {
    final value = json['value'];
    if (value is! String) {
      throw const FormatException('Bundle entry requires a value');
    }
    return BundleEntry(
        value: value, plural: json['plural'] as String? ?? 'none');
  }

  Map<String, dynamic> toJson() => {'value': value, 'plural': plural};
}

/// A resolved translation bundle served by `GET /v1/i18n/bundles/{locale}`.
///
/// `entries` are keyed by full `namespace.key` and already resolved over
/// the fallback chain server-side.
class TranslationBundle {
  const TranslationBundle({
    required this.locale,
    this.fallbackLocale,
    required this.version,
    required this.entries,
  });

  final String locale;
  final String? fallbackLocale;
  final int version;
  final Map<String, BundleEntry> entries;

  /// Look up a key; returns null when absent from the bundle.
  BundleEntry? operator [](String key) => entries[key];

  factory TranslationBundle.fromJson(Map<String, dynamic> json) {
    final locale = json['locale'];
    final entries = json['entries'];
    if (locale is! String) {
      throw const FormatException('Bundle requires a locale');
    }
    if (entries is! Map) {
      throw const FormatException('Bundle requires an entries map');
    }
    return TranslationBundle(
      locale: locale,
      fallbackLocale: json['fallback_locale'] as String?,
      version: (json['version'] as num).toInt(),
      entries: entries.map(
        (key, value) => MapEntry(
          key as String,
          BundleEntry.fromJson(Map<String, dynamic>.from(value as Map)),
        ),
      ),
    );
  }

  Map<String, dynamic> toJson() => {
        'locale': locale,
        'fallback_locale': fallbackLocale,
        'version': version,
        'entries': entries.map((key, entry) => MapEntry(key, entry.toJson())),
      };
}

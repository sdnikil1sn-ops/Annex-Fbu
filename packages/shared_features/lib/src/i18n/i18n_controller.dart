/// Runtime i18n controller (ADR-0007).
///
/// Loads the locale registry and translation bundles from the backend at
/// runtime — adding a language never requires a rebuild. Keys resolve
/// through the typed [StringKeys] registry with the bundle's already
/// server-resolved fallbacks; the key itself is the last-resort fallback
/// so missing translations never render raw.
library;

import 'package:flutter/foundation.dart';
import 'package:shared_models/shared_models.dart';
import 'package:shared_utils/shared_utils.dart';

import '../api/analysis_api.dart';

/// Loads and serves runtime translations for one locale.
class I18nController extends ChangeNotifier {
  I18nController({required this._api, String locale = 'en'}) {
    _locale = locale.toLowerCase();
  }

  final AnalysisApi _api;

  String _locale = 'en';
  LocaleList? _locales;
  TranslationBundle? _bundle;
  bool _loading = false;
  String? _error;

  /// The active locale code.
  String get locale => _locale;

  /// Whether a bundle fetch is in flight.
  bool get loading => _loading;

  /// The last load error, if any.
  String? get error => _error;

  /// The enabled locales (null until the registry loads).
  List<LocaleInfo>? get locales => _locales?.locales;

  /// Translate a typed key for the active locale.
  ///
  /// Falls back to the bundle's resolved entries, then to the key itself.
  String t(String key) {
    final entry = _bundle?[key];
    if (entry != null) return entry.value;
    if (StringKeys.isKnown(key)) return key;
    return key;
  }

  /// (Re)load the locale registry and the bundle for [locale].
  Future<void> load([String? locale]) async {
    _locale = (locale ?? _locale).toLowerCase();
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      _locales = await _api.fetchLocales();
      _bundle = await _api.fetchBundle(_locale);
    } catch (error) {
      _error = error.toString();
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  /// Resolve the fallback chain for the active locale (loading states).
  ///
  /// Uses the same algorithm as the backend (shared_utils) so the UI can
  /// fall back `requested -> parent -> en` while a bundle is in flight.
  List<String> fallbackChain() {
    final nodes = <String, LocaleNode>{
      for (final locale in _locales?.locales ?? const <LocaleInfo>[])
        locale.code: LocaleNode(locale.code, fallbackCode: locale.fallbackCode),
    };
    return resolveFallbackChain(
      _locale,
      nodes,
      defaultLocale: _locales?.defaultLocale ?? 'en',
    );
  }
}

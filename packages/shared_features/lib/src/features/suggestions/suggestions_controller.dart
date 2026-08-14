/// Translation suggestion flow controller — community contributions
/// (Phase 18/21).
///
/// Mirrors the Phase 18 backend contract: `GET /i18n/suggestions/missing`
/// lists keys the default locale defines that the active locale lacks
/// (public), `POST /i18n/suggestions` submits a proposal (idempotent per
/// user/locale/key), and `GET /i18n/suggestions` lists the caller's
/// submissions with their review status.
library;

import 'package:flutter/foundation.dart';
import 'package:shared_models/shared_models.dart';

import '../../api/analysis_api.dart';

/// The lifecycle state of the suggestions UI flow.
enum SuggestionsFlowState { idle, loading, loaded, failed }

/// Drives the missing-key list, submission, and own-suggestion reads.
class SuggestionsController extends ChangeNotifier {
  SuggestionsController({required this._api});

  final AnalysisApi _api;

  SuggestionsFlowState _state = SuggestionsFlowState.idle;
  List<MissingKey> _missing = const [];
  List<TranslationSuggestion> _submissions = const [];
  bool _busy = false;
  String? _error;

  SuggestionsFlowState get state => _state;

  /// Keys the active locale has not translated yet.
  List<MissingKey> get missing => _missing;

  /// The caller's submissions, newest first.
  List<TranslationSuggestion> get submissions => _submissions;

  /// Whether a submit action is in flight.
  bool get busy => _busy;

  /// The last load/action error, or null.
  String? get error => _error;

  /// Whether the missing list has been loaded at least once.
  bool get hasLoaded => _state == SuggestionsFlowState.loaded;

  /// Load the missing keys and the caller's submissions for [locale].
  Future<void> load(String locale) async {
    if (_state == SuggestionsFlowState.loading) return;
    _state = SuggestionsFlowState.loading;
    _error = null;
    notifyListeners();
    try {
      final missing = await _api.fetchMissingKeys(locale);
      _missing = List.unmodifiable(missing);
      _submissions = List.unmodifiable(await _api.fetchMySuggestions());
      _state = SuggestionsFlowState.loaded;
    } catch (error) {
      _error = error.toString();
      _state = SuggestionsFlowState.failed;
    }
    notifyListeners();
  }

  /// Submit a translation for [key] in [locale]; refreshes the caller's
  /// submissions on success.
  Future<bool> submit({
    required String locale,
    required MissingKey key,
    required String value,
  }) async {
    if (_busy) return false;
    _busy = true;
    _error = null;
    notifyListeners();
    try {
      final suggestion = await _api.submitSuggestion(
        locale: locale,
        namespace: key.namespace,
        key: key.key,
        value: value,
      );
      // The submitted key is now covered by a pending proposal: refresh
      // both the missing list and the submissions in one pass.
      final missing = await _api.fetchMissingKeys(locale);
      _missing = List.unmodifiable(
        missing.where((item) => item.fullKey != suggestion.fullKey),
      );
      _submissions = List.unmodifiable([
        suggestion,
        ..._submissions.where((item) => item.fullKey != suggestion.fullKey),
      ]);
      return true;
    } catch (error) {
      _error = error.toString();
      return false;
    } finally {
      _busy = false;
      notifyListeners();
    }
  }
}

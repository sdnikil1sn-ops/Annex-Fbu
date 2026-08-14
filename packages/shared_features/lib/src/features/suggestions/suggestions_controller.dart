/// Translation suggestion flow controller — community contributions
/// (Phase 18/21/23).
///
/// Mirrors the Phase 18 backend contract: `GET /i18n/suggestions/missing`
/// lists keys the default locale defines that the active locale lacks
/// (public), `POST /i18n/suggestions` submits a proposal (idempotent per
/// user/locale/key), and `GET /i18n/suggestions` lists the caller's
/// submissions with their review status. Moderators (Phase 23) run the
/// pending review queue (`GET /i18n/suggestions/pending` +
/// `POST /i18n/suggestions/{id}/review`); the caller's role comes from
/// `GET /users/me`.
library;

import 'package:flutter/foundation.dart';
import 'package:shared_models/shared_models.dart';

import '../../api/analysis_api.dart';

/// The lifecycle state of the suggestions UI flow.
enum SuggestionsFlowState { idle, loading, loaded, failed }

/// Drives the missing-key list, submission, own-suggestion reads, and
/// (for moderators) the review queue.
class SuggestionsController extends ChangeNotifier {
  SuggestionsController({required this._api});

  final AnalysisApi _api;

  SuggestionsFlowState _state = SuggestionsFlowState.idle;
  List<MissingKey> _missing = const [];
  List<TranslationSuggestion> _submissions = const [];
  List<TranslationSuggestion> _pending = const [];
  UserProfile? _profile;
  bool _busy = false;
  String? _error;

  SuggestionsFlowState get state => _state;

  /// Keys the active locale has not translated yet.
  List<MissingKey> get missing => _missing;

  /// The caller's submissions, newest first.
  List<TranslationSuggestion> get submissions => _submissions;

  /// The moderator review queue, oldest first (empty for non-moderators).
  List<TranslationSuggestion> get pending => _pending;

  /// The hydrated caller profile, when loaded.
  UserProfile? get profile => _profile;

  /// Whether the caller may run the moderator review queue.
  bool get isModerator => _profile?.isModerator ?? false;

  /// Whether a submit/review action is in flight.
  bool get busy => _busy;

  /// The last load/action error, or null.
  String? get error => _error;

  /// Whether the missing list has been loaded at least once.
  bool get hasLoaded => _state == SuggestionsFlowState.loaded;

  /// Load the missing keys, the caller's submissions, and — for
  /// moderators — the pending review queue for [locale].
  Future<void> load(String locale) async {
    if (_state == SuggestionsFlowState.loading) return;
    _state = SuggestionsFlowState.loading;
    _error = null;
    notifyListeners();
    try {
      final missing = await _api.fetchMissingKeys(locale);
      _missing = List.unmodifiable(missing);
      _submissions = List.unmodifiable(await _api.fetchMySuggestions());
      await _hydrateReview();
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

  /// Approve or reject a pending suggestion (moderator only); approval
  /// publishes the value into the live bundles. Removes the reviewed
  /// suggestion from the queue.
  Future<bool> review(String id, {required bool approved}) async {
    if (_busy) return false;
    _busy = true;
    _error = null;
    notifyListeners();
    try {
      await _api.reviewSuggestion(id, approved);
      _pending = List.unmodifiable(_pending.where((item) => item.id != id));
      return true;
    } catch (error) {
      _error = error.toString();
      return false;
    } finally {
      _busy = false;
      notifyListeners();
    }
  }

  /// Refresh the pending queue (moderator only).
  Future<void> refreshPending() async {
    if (!isModerator) return;
    try {
      _pending = List.unmodifiable(await _api.fetchPendingSuggestions());
      notifyListeners();
    } catch (error) {
      _error = error.toString();
      notifyListeners();
    }
  }

  /// Hydrate the caller's role and, when a moderator, the review queue.
  Future<void> _hydrateReview() async {
    _profile = null;
    _pending = const [];
    try {
      _profile = await _api.fetchMyProfile();
    } catch (_) {
      // Profile hydration is best-effort (e.g. anonymous callers whose
      // token was not yet hydrated); the review queue simply stays hidden.
      return;
    }
    if (_profile!.isModerator) {
      try {
        _pending = List.unmodifiable(await _api.fetchPendingSuggestions());
      } catch (_) {
        _pending = const [];
      }
    }
  }
}

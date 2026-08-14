/// Source registry flow controller — credibility (Phase 14/19/22).
///
/// Mirrors the backend sources contract: `GET /sources/search` finds
/// publishers by domain/name, `GET /sources/{domain}` opens a profile
/// with the model credibility score and the community aggregate (count,
/// average, the caller's own rating), and `POST /sources/{domain}/rate`
/// records one voice per user.
library;

import 'package:flutter/foundation.dart';
import 'package:shared_models/shared_models.dart';

import '../../api/analysis_api.dart';

/// The lifecycle state of the sources UI flow.
enum SourcesFlowState { idle, loading, loaded, failed }

/// Drives source search, profile reads, and community rating.
class SourcesController extends ChangeNotifier {
  SourcesController({required this._api});

  final AnalysisApi _api;

  SourcesFlowState _state = SourcesFlowState.idle;
  List<Source> _results = const [];
  Source? _selected;
  String _query = '';
  bool _busy = false;
  String? _error;

  SourcesFlowState get state => _state;

  /// The last search results.
  List<Source> get results => _results;

  /// The source whose profile is currently open, or null.
  Source? get selected => _selected;

  /// The query of the last search.
  String get query => _query;

  /// Whether a search/profile/rate action is in flight.
  bool get busy => _busy;

  /// The last action error, or null.
  String? get error => _error;

  /// Whether a search has completed at least once.
  bool get hasSearched => _state == SourcesFlowState.loaded;

  /// Search sources by domain or name.
  Future<void> search(String query) async {
    final trimmed = query.trim();
    if (trimmed.isEmpty || _state == SourcesFlowState.loading) return;
    _query = trimmed;
    _state = SourcesFlowState.loading;
    _error = null;
    notifyListeners();
    try {
      final results = await _api.searchSources(trimmed);
      _results = List.unmodifiable(results);
      _state = SourcesFlowState.loaded;
    } catch (error) {
      _error = error.toString();
      _state = SourcesFlowState.failed;
    }
    notifyListeners();
  }

  /// Open a source profile.
  Future<void> open(String domain) async {
    if (_busy) return;
    _busy = true;
    _error = null;
    notifyListeners();
    try {
      _selected = await _api.fetchSource(domain);
    } catch (error) {
      _error = error.toString();
    } finally {
      _busy = false;
      notifyListeners();
    }
  }

  /// Close the open profile.
  void closeProfile() {
    _selected = null;
    notifyListeners();
  }

  /// Rate the open source (1–5); updates the community aggregate.
  Future<bool> rate(int rating) async {
    final selected = _selected;
    if (_busy || selected == null) return false;
    _busy = true;
    _error = null;
    notifyListeners();
    try {
      final updated = await _api.rateSource(selected.domain, rating);
      _selected = updated;
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

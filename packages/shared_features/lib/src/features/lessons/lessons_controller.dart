/// Lessons flow controller — curriculum list, detail, completion.
///
/// Mirrors the Phase 15 backend contract: `GET /lessons` returns the
/// localized list with progress, `GET /lessons/{id or slug}` returns
/// content, and `POST /lessons/{id or slug}/complete` marks a lesson
/// complete (idempotent — the first completion wins).
library;

import 'package:flutter/foundation.dart';
import 'package:shared_models/shared_models.dart';

import '../../api/analysis_api.dart';

/// The lifecycle state of the lessons UI flow.
enum LessonsFlowState { idle, loading, loaded, failed }

/// Drives the curriculum list, detail, and completion actions.
class LessonsController extends ChangeNotifier {
  LessonsController({required this._api});

  final AnalysisApi _api;

  LessonsFlowState _state = LessonsFlowState.idle;
  List<Lesson> _lessons = const [];
  Lesson? _selected;
  bool _busy = false;
  String? _error;

  LessonsFlowState get state => _state;
  List<Lesson> get lessons => _lessons;

  /// The lesson whose detail is currently open, or null.
  Lesson? get selected => _selected;

  /// Whether a detail/completion action is in flight.
  bool get busy => _busy;

  /// The last load/action error, or null.
  String? get error => _error;

  /// Whether the list has been loaded at least once.
  bool get hasLoaded => _state == LessonsFlowState.loaded;

  /// Load the localized curriculum list for [locale].
  Future<void> load(String locale) async {
    if (_state == LessonsFlowState.loading) return;
    _state = LessonsFlowState.loading;
    _error = null;
    notifyListeners();
    try {
      final lessons = await _api.fetchLessons(locale: locale);
      _lessons = List.unmodifiable(lessons);
      _state = LessonsFlowState.loaded;
    } catch (error) {
      _error = error.toString();
      _state = LessonsFlowState.failed;
    }
    notifyListeners();
  }

  /// Open a lesson by id or slug, loading its localized content.
  Future<void> open(String idOrSlug, {required String locale}) async {
    if (_busy) return;
    _busy = true;
    _error = null;
    notifyListeners();
    try {
      _selected = await _api.fetchLesson(idOrSlug, locale: locale);
    } catch (error) {
      _error = error.toString();
    } finally {
      _busy = false;
      notifyListeners();
    }
  }

  /// Close the open detail view.
  void closeDetail() {
    _selected = null;
    notifyListeners();
  }

  /// Mark the selected lesson complete; refreshes its progress.
  ///
  /// Completion is idempotent server-side; the client re-reads the lesson
  /// so `completed` reflects the stored timestamp, and keeps the list in
  /// sync so navigating back shows the checkmark.
  Future<void> complete({required String locale}) async {
    final selected = _selected;
    if (_busy || selected == null) return;
    _busy = true;
    _error = null;
    notifyListeners();
    try {
      await _api.completeLesson(selected.id);
      _selected = await _api.fetchLesson(selected.id, locale: locale);
      _lessons = List.unmodifiable(
        _lessons.map(
          (lesson) => lesson.id == selected.id ? _selected! : lesson,
        ),
      );
    } catch (error) {
      _error = error.toString();
    } finally {
      _busy = false;
      notifyListeners();
    }
  }
}

/// Classes flow controller — educator tools (Phase 17/20).
///
/// Mirrors the Phase 17 backend contract: `GET /classes` lists the
/// caller's classes with their membership role, `GET /classes/{id}`
/// adds the roster and assignments, `POST /classes/{id}/join` joins by
/// invite code, and teachers assign lessons and read completion progress.
library;

import 'package:flutter/foundation.dart';
import 'package:shared_models/shared_models.dart';

import '../../api/analysis_api.dart';

/// The lifecycle state of the classes UI flow.
enum ClassesFlowState { idle, loading, loaded, failed }

/// Drives the class list, detail, and educator actions.
class ClassesController extends ChangeNotifier {
  ClassesController({required this._api});

  final AnalysisApi _api;

  ClassesFlowState _state = ClassesFlowState.idle;
  List<ClassRoom> _classes = const [];
  ClassRoom? _selected;
  List<AssignmentProgress> _progress = const [];
  bool _busy = false;
  String? _error;

  ClassesFlowState get state => _state;
  List<ClassRoom> get classes => _classes;

  /// The class whose detail is currently open, or null.
  ClassRoom? get selected => _selected;

  /// Per-assignment completion for the open class (teacher only).
  List<AssignmentProgress> get progress => _progress;

  /// Whether an action is in flight.
  bool get busy => _busy;

  /// The last load/action error, or null.
  String? get error => _error;

  /// Whether the list has been loaded at least once.
  bool get hasLoaded => _state == ClassesFlowState.loaded;

  /// Load the caller's classes.
  Future<void> load() async {
    if (_state == ClassesFlowState.loading) return;
    _state = ClassesFlowState.loading;
    _error = null;
    notifyListeners();
    try {
      final classes = await _api.fetchClasses();
      _classes = List.unmodifiable(classes);
      _state = ClassesFlowState.loaded;
    } catch (error) {
      _error = error.toString();
      _state = ClassesFlowState.failed;
    }
    notifyListeners();
  }

  /// Create a class; the caller becomes its teacher. On success the new
  /// class is selected so its invite code is immediately visible.
  Future<bool> create(String name, String description) async {
    if (_busy) return false;
    _busy = true;
    _error = null;
    notifyListeners();
    try {
      final room = await _api.createClass(name, description);
      _classes = List.unmodifiable([..._classes, room]);
      _selected = room;
      return true;
    } catch (error) {
      _error = error.toString();
      return false;
    } finally {
      _busy = false;
      notifyListeners();
    }
  }

  /// Join a class by its invite code; selects the joined class.
  Future<bool> join(String classId, String inviteCode) async {
    if (_busy) return false;
    _busy = true;
    _error = null;
    notifyListeners();
    try {
      final member = await _api.joinClass(classId, inviteCode);
      await load();
      final joined = _classes.where((room) => room.id == classId).toList();
      _selected = joined.isEmpty ? null : joined.first;
      return member.userId.isNotEmpty;
    } catch (error) {
      _error = error.toString();
      return false;
    } finally {
      _busy = false;
      notifyListeners();
    }
  }

  /// Open a class, loading its roster and assignments.
  Future<void> open(String id) async {
    if (_busy) return;
    _busy = true;
    _error = null;
    notifyListeners();
    try {
      _selected = await _api.fetchClass(id);
      _progress = const [];
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
    _progress = const [];
    notifyListeners();
  }

  /// Assign a lesson to the open class (teacher only).
  Future<bool> assignLesson(String lessonRef) async {
    final selected = _selected;
    if (_busy || selected == null) return false;
    _busy = true;
    _error = null;
    notifyListeners();
    try {
      final assignment = await _api.assignLesson(selected.id, lessonRef);
      // Refresh the detail directly: `open` is guarded by `_busy`, which
      // is still true here.
      _selected = await _api.fetchClass(selected.id);
      _progress = const [];
      return assignment.lessonId.isNotEmpty;
    } catch (error) {
      _error = error.toString();
      return false;
    } finally {
      _busy = false;
      notifyListeners();
    }
  }

  /// Load per-assignment completion for the open class (teacher only).
  Future<void> loadProgress() async {
    final selected = _selected;
    if (_busy || selected == null) return;
    _busy = true;
    _error = null;
    notifyListeners();
    try {
      _progress = List.unmodifiable(await _api.fetchClassProgress(selected.id));
    } catch (error) {
      _error = error.toString();
    } finally {
      _busy = false;
      notifyListeners();
    }
  }

  /// Remove an assignment from the open class (teacher only).
  Future<bool> deleteAssignment(String assignmentId) async {
    final selected = _selected;
    if (_busy || selected == null) return false;
    _busy = true;
    _error = null;
    notifyListeners();
    try {
      await _api.deleteAssignment(selected.id, assignmentId);
      _selected = await _api.fetchClass(selected.id);
      _progress = const [];
      return true;
    } catch (error) {
      _error = error.toString();
      return false;
    } finally {
      _busy = false;
      notifyListeners();
    }
  }

  /// Remove a member from the open class (teacher only).
  Future<bool> removeMember(String memberId) async {
    final selected = _selected;
    if (_busy || selected == null) return false;
    _busy = true;
    _error = null;
    notifyListeners();
    try {
      await _api.removeMember(selected.id, memberId);
      _selected = await _api.fetchClass(selected.id);
      _progress = const [];
      return true;
    } catch (error) {
      _error = error.toString();
      return false;
    } finally {
      _busy = false;
      notifyListeners();
    }
  }

  /// Delete the open class and return to the list (owner only).
  Future<bool> deleteClass() async {
    final selected = _selected;
    if (_busy || selected == null) return false;
    _busy = true;
    _error = null;
    notifyListeners();
    try {
      await _api.deleteClass(selected.id);
      _selected = null;
      _progress = const [];
      await load();
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

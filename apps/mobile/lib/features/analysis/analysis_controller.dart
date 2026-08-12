/// Analysis flow controller — submit text, poll until terminal, report.
///
/// Mirrors the backend contract: `POST /analysis` returns a pending
/// analysis; the client polls `GET /analysis/{id}` (respecting
/// `meta.retry_after`) until it completes or fails. A timer drives the
/// polling so the UI stays responsive.
library;

import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:shared_models/shared_models.dart';

import '../../core/api/analysis_api.dart';

/// The lifecycle state of the analysis UI flow.
enum AnalysisFlowState { idle, submitting, polling, completed, failed }

/// Drives one analysis submission end to end.
class AnalysisController extends ChangeNotifier {
  AnalysisController({
    required this._api,
    this.pollInterval = const Duration(seconds: 2),
    this.maxPolls = 60,
  });

  final AnalysisApi _api;

  /// Interval between polling requests.
  final Duration pollInterval;

  /// Safety cap on polling attempts before giving up.
  final int maxPolls;

  AnalysisFlowState _state = AnalysisFlowState.idle;
  Analysis? _analysis;
  String? _error;
  Timer? _pollTimer;
  int _polls = 0;

  AnalysisFlowState get state => _state;
  Analysis? get analysis => _analysis;

  /// The completed report, or null.
  AnalysisReport? get report => _analysis?.report;

  /// Structured failure reason when the analysis failed.
  String? get failureReason => _analysis?.failureReason;

  /// The last error message (network/validation), or null.
  String? get error => _error;

  /// Whether a submission or poll is in flight.
  bool get busy =>
      _state == AnalysisFlowState.submitting ||
      _state == AnalysisFlowState.polling;

  /// Submit text and start polling until the analysis is terminal.
  Future<void> submit(String text, {String locale = 'en'}) async {
    if (busy || text.trim().isEmpty) return;
    _cancelPolling();
    _state = AnalysisFlowState.submitting;
    _analysis = null;
    _error = null;
    _polls = 0;
    notifyListeners();

    try {
      _analysis = await _api.submitText(text.trim(), locale: locale);
    } catch (error) {
      _error = error.toString();
      _state = AnalysisFlowState.failed;
      notifyListeners();
      return;
    }

    _state = AnalysisFlowState.polling;
    notifyListeners();
    _startPolling();
  }

  void _startPolling() {
    _pollTimer = Timer.periodic(pollInterval, (_) => _pollOnce());
  }

  Future<void> _pollOnce() async {
    final analysis = _analysis;
    if (analysis == null) return;
    try {
      _analysis = await _api.fetchAnalysis(analysis.id);
    } catch (error) {
      _error = error.toString();
      // Keep polling on transient failures; give up after the cap.
      if (++_polls >= maxPolls) {
        _cancelPolling();
        _state = AnalysisFlowState.failed;
        notifyListeners();
      }
      return;
    }

    _polls++;
    if (_analysis!.isTerminal || _polls >= maxPolls) {
      _cancelPolling();
      _state = _analysis!.hasFailed
          ? AnalysisFlowState.failed
          : AnalysisFlowState.completed;
      if (_polls >= maxPolls && !_analysis!.isTerminal) {
        _error = 'Polling limit reached';
        _state = AnalysisFlowState.failed;
      }
      notifyListeners();
      return;
    }
    notifyListeners();
  }

  void _cancelPolling() {
    _pollTimer?.cancel();
    _pollTimer = null;
  }

  @override
  void dispose() {
    _cancelPolling();
    super.dispose();
  }
}

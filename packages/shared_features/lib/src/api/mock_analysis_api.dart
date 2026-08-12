/// Explicit in-memory mock of the backend API for tests and local dev.
///
/// Implements [AnalysisApi] behind the same interface as the HTTP client
/// and simulates the async pipeline: submissions start `pending`, become
/// `processing`, then complete with a deterministic report (unless the
/// input is flagged to fail).
library;

import 'package:shared_models/shared_models.dart';

import 'analysis_api.dart';

/// A deterministic fake backend.
///
/// Optionally simulates provider failures: texts containing the
/// `failTrigger` substring complete with `failed` status.
class MockAnalysisApi implements AnalysisApi {
  MockAnalysisApi({
    this.failTrigger = '!!!',
    this.initialReport,
    this.delay = const Duration(milliseconds: 10),
  });

  /// Substring that makes submitted text fail analysis.
  final String failTrigger;

  /// The report produced for successful analyses.
  final AnalysisReport? initialReport;

  /// Simulated processing latency per transition.
  final Duration delay;

  final List<Analysis> _analyses = [];
  final List<String> _inputs = [];
  int _nextId = 1;

  /// Whether the last submission was recorded (test hook).
  String? lastSubmittedText;
  String? lastSubmittedLocale;

  static final _report = AnalysisReport(
    summary: 'The text makes two checkable claims with verifiable evidence.',
    claims: const [
      ClaimItem(text: 'The Earth orbits the Sun', verifiability: 0.95),
      ClaimItem(text: 'The claim cites an outdated study', verifiability: 0.45),
    ],
  );

  @override
  Future<Analysis> submitText(String text, {String locale = 'en'}) async {
    lastSubmittedText = text;
    lastSubmittedLocale = locale;
    await Future<void>.delayed(delay);
    final now = DateTime.now().toUtc();
    final analysis = Analysis(
      id: 'mock-${_nextId++}',
      inputType: AnalysisInputType.text,
      status: AnalysisStatus.pending,
      locale: locale,
      createdAt: now,
    );
    _analyses.add(analysis);
    _inputs.add(text);
    return analysis;
  }

  @override
  Future<Analysis> fetchAnalysis(String id) async {
    await Future<void>.delayed(delay);
    final index = _analyses.indexWhere((a) => a.id == id);
    if (index < 0) {
      throw const ApiException('analysis.not_found', 'Analysis not found');
    }
    final current = _analyses[index];
    if (current.status.isTerminal) return current;

    // Advance the simulated state machine: pending -> processing -> done.
    // Failure is driven by the input captured at submit time, so each
    // analysis is evaluated independently.
    final failed = _inputs[index].contains(failTrigger);
    final updated = failed
        ? Analysis(
            id: current.id,
            inputType: current.inputType,
            status: AnalysisStatus.failed,
            locale: current.locale,
            failureReason: 'analysis.processing_failed',
            createdAt: current.createdAt,
            completedAt: DateTime.now().toUtc(),
          )
        : Analysis(
            id: current.id,
            inputType: current.inputType,
            status: AnalysisStatus.completed,
            locale: current.locale,
            report: initialReport ?? _report,
            createdAt: current.createdAt,
            completedAt: DateTime.now().toUtc(),
          );
    _analyses[index] = updated;
    return updated;
  }

  @override
  Future<LocaleList> fetchLocales() async {
    return const LocaleList(
      defaultLocale: 'en',
      locales: [
        LocaleInfo(code: 'en'),
        LocaleInfo(code: 'pt', fallbackCode: 'en'),
        LocaleInfo(code: 'es', fallbackCode: 'en'),
      ],
    );
  }

  @override
  Future<TranslationBundle> fetchBundle(String locale) async {
    const shared = {
      'common.cancel': BundleEntry(value: 'Cancel', plural: 'none'),
      'common.retry': BundleEntry(value: 'Retry', plural: 'none'),
      'common.loading': BundleEntry(value: 'Loading…', plural: 'none'),
      'common.learn_before_you_believe': BundleEntry(
        value: 'Learn before you believe.',
        plural: 'none',
      ),
      'analysis.title': BundleEntry(value: 'Analyze', plural: 'none'),
      'analysis.submit': BundleEntry(value: 'Analyze text', plural: 'none'),
      'analysis.pending': BundleEntry(
        value: 'Analysis in progress…',
        plural: 'none',
      ),
      'analysis.processing': BundleEntry(value: 'Analyzing…', plural: 'none'),
      'analysis.failed': BundleEntry(value: 'Analysis failed', plural: 'none'),
      'analysis.summary': BundleEntry(value: 'Summary', plural: 'none'),
      'analysis.verifiability': BundleEntry(
        value: 'Verifiability',
        plural: 'none',
      ),
      'analysis.credibility_score': BundleEntry(
        value: 'Credibility score',
        plural: 'none',
      ),
      'analysis.input_hint': BundleEntry(
        value: 'Paste text to verify…',
        plural: 'none',
      ),
      'auth.sign_in': BundleEntry(value: 'Sign in', plural: 'none'),
      'auth.sign_out': BundleEntry(value: 'Sign out', plural: 'none'),
      'auth.continue_guest': BundleEntry(
        value: 'Continue as guest',
        plural: 'none',
      ),
      'auth.continue_google': BundleEntry(
        value: 'Continue with Google',
        plural: 'none',
      ),
      'auth.guest_label': BundleEntry(value: 'Guest', plural: 'none'),
      'settings.title': BundleEntry(value: 'Settings', plural: 'none'),
      'settings.language': BundleEntry(value: 'Language', plural: 'none'),
      'settings.theme': BundleEntry(value: 'Theme', plural: 'none'),
      'settings.theme_system': BundleEntry(value: 'System', plural: 'none'),
      'settings.theme_light': BundleEntry(value: 'Light', plural: 'none'),
      'settings.theme_dark': BundleEntry(value: 'Dark', plural: 'none'),
      'settings.account': BundleEntry(value: 'Account', plural: 'none'),
    };
    if (locale == 'en') {
      return TranslationBundle(
        locale: 'en',
        version: 1,
        entries: Map.of(shared),
      );
    }
    // Mirror the backend contract: the bundle is already resolved over the
    // fallback chain — the locale's own entries win, missing keys are
    // filled from en (ADR-0007).
    final own = locale == 'pt'
        ? const <String, BundleEntry>{
            'common.cancel': BundleEntry(value: 'Cancelar', plural: 'none'),
            'analysis.submit': BundleEntry(value: 'Analisar', plural: 'none'),
            'analysis.summary': BundleEntry(value: 'Resumo', plural: 'none'),
          }
        : const <String, BundleEntry>{
            'common.cancel': BundleEntry(value: 'Cancelar', plural: 'none'),
            'analysis.submit': BundleEntry(value: 'Analizar', plural: 'none'),
          };
    final merged = <String, BundleEntry>{...shared, ...own};
    return TranslationBundle(
      locale: locale,
      fallbackLocale: 'en',
      version: 1,
      entries: Map.unmodifiable(merged),
    );
  }
}

/// Runtime configuration for the ANNEX mobile app.
///
/// Values are read from `--dart-define` at build time (e.g.
/// `flutter run --dart-define=ANNEX_API_URL=https://api.example.com`).
/// No secrets are compiled into the binary (SECURITY.md).
library;

import 'package:flutter/foundation.dart';

/// The backend API base URL.
///
/// Defaults to the local development server; override with
/// `--dart-define=ANNEX_API_URL=...`.
const String apiBaseUrl = String.fromEnvironment(
  'ANNEX_API_URL',
  defaultValue: 'http://localhost:8000/api/v1',
);

/// Whether to run with the in-memory mock API instead of the real backend.
///
/// Defaults to true in debug builds so the app works without a server, and
/// false in release builds so production can never silently serve mock
/// data. Override explicitly with `--dart-define=ANNEX_USE_MOCK=...`.
const bool useMockApi = bool.fromEnvironment(
  'ANNEX_USE_MOCK',
  defaultValue: kDebugMode,
);

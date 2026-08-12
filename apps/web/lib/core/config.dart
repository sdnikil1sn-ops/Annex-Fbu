/// Runtime configuration for the ANNEX web app.
///
/// Values are read from `--dart-define` at build time (e.g.
/// `flutter build web --dart-define=ANNEX_API_URL=https://api.example.com`).
/// The production Firebase Hosting build points `ANNEX_API_URL` at the
/// Cloud Run API and sets `ANNEX_USE_MOCK=false` (docs/guides/deployment.md
/// §11). No secrets are compiled into the bundle (SECURITY.md).
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

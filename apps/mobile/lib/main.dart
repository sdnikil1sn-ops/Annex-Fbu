/// ANNEX mobile app entry point.
///
/// Wires the composition root: Firebase Auth (when available), the API
/// client (HTTP or the explicit mock in debug), and the runtime i18n
/// loader, then builds the app scope. All feature code comes from
/// `shared_features`; this entry point stays platform-specific (Phase 12).
library;

import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_features/shared_features.dart';

import 'app/annex_app.dart';
import 'core/config.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Firebase is the only auth backend in production. In release builds a
  // failed initialization must surface so the accepting-everything mock
  // can never serve real users; the mock is debug-only for local runs.
  AuthGateway auth;
  try {
    await Firebase.initializeApp();
    auth = FirebaseAuthGateway();
  } catch (error) {
    if (kReleaseMode) rethrow;
    auth = MockAuthGateway();
  }

  final AnalysisApi api = useMockApi
      ? MockAnalysisApi()
      : HttpAnalysisApi(
          baseUrl: apiBaseUrl,
          tokenProvider: () => auth.idToken(),
        );

  final i18n = I18nController(api: api);
  final authController = AuthController(auth);
  final settings = SettingsController(i18n: i18n);

  final services = AppServices(
    api: api,
    authController: authController,
    i18n: i18n,
    settings: settings,
  );

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: authController),
        ChangeNotifierProvider.value(value: i18n),
        ChangeNotifierProvider.value(value: settings),
      ],
      child: AppScope(services: services, child: const AnnexApp()),
    ),
  );

  // Warm the locale registry; the shell renders with English meanwhile.
  unawaited(i18n.load());
}

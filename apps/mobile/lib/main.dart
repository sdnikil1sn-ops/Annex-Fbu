/// ANNEX mobile app entry point.
///
/// Wires the composition root: Firebase Auth (when available), the API
/// client (HTTP or the explicit mock in debug), and the runtime i18n
/// loader, then builds the app scope. All feature code comes from
/// `shared_features`; this entry point stays platform-specific (Phase 12).
library;

import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_features/shared_features.dart';

import 'app/annex_app.dart';
import 'core/config.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Firebase is optional in local/dev builds: without a project config the
  // app still runs through the guest flow.
  AuthGateway auth = MockAuthGateway();
  try {
    await Firebase.initializeApp();
    auth = FirebaseAuthGateway();
  } catch (_) {
    // No Firebase configuration — fall back to the explicit mock.
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

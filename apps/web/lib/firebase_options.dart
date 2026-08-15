/// Firebase options for the ANNEX web app.
///
/// Mirrors the Firebase project (annex-adv-38561). Keeping options in Dart
/// lets `Firebase.initializeApp(options: ...)` create the default app
/// through the modular JS SDK that FlutterFire auto-injects — the compat
/// SDK previously loaded in index.html was incompatible with the web
/// plugin and caused initialization to fail (and auth to silently fall
/// back to the mock gateway).
library;

import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;

const FirebaseOptions firebaseOptions = FirebaseOptions(
  apiKey: 'AIzaSyDi-w4PxwL7IMekiztf2f641QB-79Zz_6E',
  appId: '1:294477889054:web:749909fc91c43056f0b80f',
  messagingSenderId: '294477889054',
  projectId: 'annex-adv-38561',
  authDomain: 'annex-adv-38561.firebaseapp.com',
  storageBucket: 'annex-adv-38561.firebasestorage.app',
  measurementId: 'G-N088NRPMYD',
);

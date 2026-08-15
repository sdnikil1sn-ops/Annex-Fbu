/// Fullscreen toggle fallback for non-web targets (e.g. VM widget tests).
///
/// The real implementation lives in fullscreen_web.dart and is selected
/// via conditional import when dart:js_interop is available.
library;

/// No-op on non-web platforms.
void toggleFullscreen() {}

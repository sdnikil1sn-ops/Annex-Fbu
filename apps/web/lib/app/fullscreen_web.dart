/// Browser fullscreen toggle (web implementation).
library;

import 'package:web/web.dart' as web;

/// Request or exit the browser fullscreen.
void toggleFullscreen() {
  final document = web.document;
  if (document.fullscreenElement != null) {
    document.exitFullscreen();
  } else {
    document.documentElement!.requestFullscreen();
  }
}

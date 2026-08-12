/// Locale fallback-chain resolution (ADR-0007).
///
/// Clients resolve a requested locale against the server-declared chain
/// `requested -> parent -> ... -> default` (e.g. `pt-BR -> pt -> en`) and
/// load bundles asynchronously, falling back to the next entry in the
/// chain while a bundle is still loading or a key is missing.
library;

/// A locale known to the server, with its optional parent locale.
class LocaleNode {
  const LocaleNode(this.code, {this.fallbackCode});

  /// BCP-47-style code, lower-cased (e.g. `en`, `pt-BR`).
  final String code;

  /// The parent locale code, or null for the default locale.
  final String? fallbackCode;
}

/// Returns the ordered fallback chain for [locale].
///
/// The chain starts at [locale] and follows `fallbackCode` parents until
/// reaching [defaultLocale], which is always appended last — mirroring
/// the backend resolution in `app/domain/i18n.py`. Cycles in declared
/// fallbacks are broken by visiting each code at most once.
///
/// Example: `pt-BR` with parents `pt -> en` yields
/// `[pt-BR, pt, en]`.
List<String> resolveFallbackChain(
  String locale,
  Map<String, LocaleNode> locales, {
  required String defaultLocale,
}) {
  final chain = <String>[];
  final seen = <String>{};
  var current = locale;
  while (!seen.contains(current)) {
    seen.add(current);
    chain.add(current);
    final node = locales[current];
    if (node == null || node.fallbackCode == null) break;
    current = node.fallbackCode!;
  }
  if (chain.last != defaultLocale) {
    chain.add(defaultLocale);
  }
  return chain;
}

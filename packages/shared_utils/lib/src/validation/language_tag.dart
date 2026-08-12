/// BCP-47-style language tag validation.
///
/// The project's locale codes are 2–3 letter language tags with optional
/// script/region subtags (`en`, `pt-BR`, `zh-Hans`). Validation mirrors
/// the backend contract so a tag accepted here is accepted by the API.
library;

final RegExp _tagPattern = RegExp(r'^[a-z]{2,3}(-[a-z0-9]{2,8})*$');

/// Whether [tag] is a well-formed, API-valid locale code.
bool isValidLanguageTag(String tag) {
  return _tagPattern.hasMatch(tag.trim().toLowerCase());
}

/// Normalizes [tag] to the canonical lowercase form used in bundles.
String canonicalLanguageTag(String tag) => tag.trim().toLowerCase();

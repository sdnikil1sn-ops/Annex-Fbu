/// Community translation contribution models (Phase 18/21).
///
/// Shapes mirror the backend suggestion endpoints: `GET
/// /i18n/suggestions/missing` returns keys the default locale defines that
/// a target locale lacks (public), `POST /i18n/suggestions` submits a
/// proposal, and `GET /i18n/suggestions` lists the caller's submissions
/// with their review status.
library;

/// A key the default locale defines that a target locale has not
/// translated yet.
class MissingKey {
  const MissingKey({
    required this.namespace,
    required this.key,
    required this.englishValue,
  });

  final String namespace;
  final String key;

  /// The default-locale source text contributors translate from.
  final String englishValue;

  /// The dotted `namespace.key` identifier.
  String get fullKey => '$namespace.$key';

  factory MissingKey.fromJson(Map<String, dynamic> json) {
    final namespace = json['namespace'];
    final key = json['key'];
    final english = json['english'];
    if (namespace is! String || namespace.isEmpty) {
      throw const FormatException('MissingKey requires a namespace');
    }
    if (key is! String || key.isEmpty) {
      throw const FormatException('MissingKey requires a key');
    }
    if (english is! String) {
      throw const FormatException('MissingKey requires an english value');
    }
    return MissingKey(
      namespace: namespace,
      key: key,
      englishValue: english,
    );
  }

  Map<String, dynamic> toJson() =>
      {'namespace': namespace, 'key': key, 'english': englishValue};
}

/// A community-proposed translation awaiting (or after) review.
class TranslationSuggestion {
  const TranslationSuggestion({
    required this.id,
    required this.locale,
    required this.namespace,
    required this.key,
    required this.value,
    this.pluralRule = 'none',
    this.suggestedBy,
    this.status = 'pending',
    this.createdAt,
  });

  final String id;

  /// The target locale the value translates into.
  final String locale;

  final String namespace;
  final String key;

  /// The proposed translation.
  final String value;

  /// ICU plural category of the proposed form.
  final String pluralRule;

  /// The contributor's user id, when the payload carries it.
  final String? suggestedBy;

  /// `pending` | `approved` | `rejected`.
  final String status;

  final DateTime? createdAt;

  /// The dotted `namespace.key` identifier.
  String get fullKey => '$namespace.$key';

  /// Whether this suggestion is still awaiting moderator review.
  bool get isPending => status == 'pending';

  factory TranslationSuggestion.fromJson(Map<String, dynamic> json) {
    final id = json['id'];
    final locale = json['locale'];
    final namespace = json['namespace'];
    final key = json['key'];
    final value = json['value'];
    if (id is! String || id.isEmpty) {
      throw const FormatException('TranslationSuggestion requires an id');
    }
    if (locale is! String || locale.isEmpty) {
      throw const FormatException('TranslationSuggestion requires a locale');
    }
    if (namespace is! String || namespace.isEmpty) {
      throw const FormatException('TranslationSuggestion requires a namespace');
    }
    if (key is! String || key.isEmpty) {
      throw const FormatException('TranslationSuggestion requires a key');
    }
    if (value is! String || value.isEmpty) {
      throw const FormatException('TranslationSuggestion requires a value');
    }
    final createdAt = json['created_at'];
    return TranslationSuggestion(
      id: id,
      locale: locale,
      namespace: namespace,
      key: key,
      value: value,
      pluralRule: json['plural_rule'] as String? ?? 'none',
      suggestedBy: json['suggested_by'] as String?,
      status: json['status'] as String? ?? 'pending',
      createdAt: createdAt == null ? null : DateTime.parse(createdAt as String),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'locale': locale,
        'namespace': namespace,
        'key': key,
        'value': value,
        'plural_rule': pluralRule,
        'suggested_by': suggestedBy,
        'status': status,
        'created_at': createdAt?.toIso8601String(),
      };
}

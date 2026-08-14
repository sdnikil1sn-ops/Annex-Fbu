/// Source credibility domain models (Phase 14/19/22).
///
/// Shapes mirror the backend sources contract: `GET /sources/search` and
/// `GET /sources/{domain}` return a profile with the model credibility
/// score and trust signals, plus (since Phase 19) the aggregated
/// community signal — count, average, and the caller's own rating when
/// authenticated. `POST /sources/{domain}/rate` returns the updated
/// profile.
library;

/// The aggregated community credibility signal for a source.
class SourceCommunity {
  const SourceCommunity({
    this.count = 0,
    this.average,
    this.myRating,
  });

  /// Number of distinct users who rated the source.
  final int count;

  /// Mean rating (1–5), or null when nobody has rated yet.
  final double? average;

  /// The caller's own rating, when authenticated and rated.
  final int? myRating;

  /// Whether the caller has rated this source.
  bool get hasRated => myRating != null;

  factory SourceCommunity.fromJson(Map<String, dynamic> json) {
    return SourceCommunity(
      count: (json['count'] as num?)?.toInt() ?? 0,
      average: (json['average'] as num?)?.toDouble(),
      myRating: (json['my_rating'] as num?)?.toInt(),
    );
  }

  Map<String, dynamic> toJson() => {
        'count': count,
        'average': average,
        'my_rating': myRating,
      };
}

/// A publisher/domain with its latest credibility score.
class Source {
  const Source({
    required this.id,
    required this.domain,
    this.name,
    this.country,
    this.language,
    this.category,
    this.score,
    this.signals = const {},
    this.model,
    this.computedAt,
    this.community = const SourceCommunity(),
  });

  final String id;

  /// The publisher's domain (unique).
  final String domain;

  /// Display name, when known.
  final String? name;

  final String? country;
  final String? language;

  /// Publisher category (news, fact_check, blog, ...).
  final String? category;

  /// Latest model credibility score (0..1), when computed.
  final double? score;

  /// Named trust signals backing the score.
  final Map<String, dynamic> signals;

  /// Which model/version produced the latest score.
  final String? model;

  final DateTime? computedAt;

  /// Aggregated community credibility feedback (Phase 19).
  final SourceCommunity community;

  factory Source.fromJson(Map<String, dynamic> json) {
    final id = json['id'];
    final domain = json['domain'];
    if (id is! String || id.isEmpty) {
      throw const FormatException('Source requires an id');
    }
    if (domain is! String || domain.isEmpty) {
      throw const FormatException('Source requires a domain');
    }
    final score = json['score'];
    final signals = json['signals'];
    final computedAt = json['computed_at'];
    final community = json['community'];
    return Source(
      id: id,
      domain: domain,
      name: json['name'] as String?,
      country: json['country'] as String?,
      language: json['language'] as String?,
      category: json['category'] as String?,
      score: score == null ? null : (score as num).toDouble(),
      signals: signals is Map
          ? Map<String, dynamic>.from(signals)
          : const <String, dynamic>{},
      model: json['model'] as String?,
      computedAt:
          computedAt == null ? null : DateTime.parse(computedAt as String),
      community: community is Map
          ? SourceCommunity.fromJson(Map<String, dynamic>.from(community))
          : const SourceCommunity(),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'domain': domain,
        'name': name,
        'country': country,
        'language': language,
        'category': category,
        'score': score,
        'signals': signals,
        'model': model,
        'computed_at': computedAt?.toIso8601String(),
        'community': community.toJson(),
      };
}

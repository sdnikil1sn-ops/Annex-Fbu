/// Analysis domain models (ADR-0002 / ADR-0008).
///
/// Shapes mirror the backend contract: `POST /analysis` returns an
/// analysis with `id`, `input_type`, `status`, `locale`, `report` and
/// timestamps; reports carry a `summary` and a list of claims with
/// `text` + numeric `verifiability`.
library;

/// The kind of content submitted for analysis.
enum AnalysisInputType {
  text('text'),
  url('url'),
  image('image');

  const AnalysisInputType(this.wire);

  /// The wire value used by the API.
  final String wire;

  static AnalysisInputType fromWire(String value) {
    return AnalysisInputType.values.firstWhere(
      (type) => type.wire == value,
      orElse: () => throw FormatException('Unknown input_type: $value'),
    );
  }
}

/// Lifecycle states of an analysis (ADR-0008).
enum AnalysisStatus {
  pending('pending'),
  processing('processing'),
  completed('completed'),
  failed('failed');

  const AnalysisStatus(this.wire);

  /// The wire value used by the API.
  final String wire;

  static AnalysisStatus fromWire(String value) {
    return AnalysisStatus.values.firstWhere(
      (status) => status.wire == value,
      orElse: () => throw FormatException('Unknown status: $value'),
    );
  }

  /// Whether the state machine has reached a terminal state.
  bool get isTerminal => this == completed || this == failed;
}

/// One extracted claim with its verifiability score.
class ClaimItem {
  const ClaimItem({required this.text, required this.verifiability});

  /// The claim as written in the analyzed content.
  final String text;

  /// Verifiability in `[0, 1]` (1 = fully verifiable).
  final double verifiability;

  /// Whether the score is in the documented `[0, 1]` range.
  bool get isInRange => verifiability >= 0 && verifiability <= 1;

  factory ClaimItem.fromJson(Map<String, dynamic> json) {
    final text = json['text'];
    final score = json['verifiability'];
    if (text is! String || text.isEmpty) {
      throw const FormatException('Claim requires a non-empty text');
    }
    if (score is! num) {
      throw const FormatException('Claim requires a numeric verifiability');
    }
    return ClaimItem(text: text, verifiability: score.toDouble());
  }

  Map<String, dynamic> toJson() =>
      {'text': text, 'verifiability': verifiability};
}

/// The structured output of a completed analysis.
class AnalysisReport {
  const AnalysisReport({required this.summary, required this.claims});

  /// Short, neutral summary of the analyzed content.
  final String summary;

  /// The extracted claims, in order.
  final List<ClaimItem> claims;

  /// Overall credibility score as the mean claim verifiability
  /// (`0..1`), or `0` when no claims were extracted.
  double get credibilityScore {
    if (claims.isEmpty) return 0;
    final total =
        claims.fold<double>(0, (sum, claim) => sum + claim.verifiability);
    return total / claims.length;
  }

  factory AnalysisReport.fromJson(Map<String, dynamic> json) {
    final summary = json['summary'];
    final claims = json['claims'];
    if (summary is! String) {
      throw const FormatException('Report requires a summary string');
    }
    if (claims is! List) {
      throw const FormatException('Report requires a claims list');
    }
    return AnalysisReport(
      summary: summary,
      claims: claims
          .map((item) =>
              ClaimItem.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() => {
        'summary': summary,
        'claims': claims.map((claim) => claim.toJson()).toList(),
      };
}

/// One analysis request as returned by the API.
class Analysis {
  const Analysis({
    required this.id,
    required this.inputType,
    required this.status,
    required this.locale,
    this.failureReason,
    this.report,
    required this.createdAt,
    this.completedAt,
  });

  final String id;
  final AnalysisInputType inputType;
  final AnalysisStatus status;
  final String locale;

  /// Structured error code when `status == failed`.
  final String? failureReason;

  /// The report, present once the analysis completed.
  final AnalysisReport? report;

  final DateTime createdAt;
  final DateTime? completedAt;

  /// Whether the client can stop polling (completed or failed).
  bool get isTerminal => status.isTerminal;

  /// Whether the analysis failed with a known failure reason.
  bool get hasFailed => status == AnalysisStatus.failed;

  factory Analysis.fromJson(Map<String, dynamic> json) {
    final id = json['id'];
    final createdAt = json['created_at'];
    if (id is! String || id.isEmpty) {
      throw const FormatException('Analysis requires an id');
    }
    if (createdAt is! String) {
      throw const FormatException('Analysis requires created_at');
    }
    final reportJson = json['report'];
    final completedAt = json['completed_at'];
    return Analysis(
      id: id,
      inputType: AnalysisInputType.fromWire(json['input_type'] as String),
      status: AnalysisStatus.fromWire(json['status'] as String),
      locale: json['locale'] as String,
      failureReason: json['failure_reason'] as String?,
      report: reportJson == null
          ? null
          : AnalysisReport.fromJson(
              Map<String, dynamic>.from(reportJson as Map)),
      createdAt: DateTime.parse(createdAt),
      completedAt:
          completedAt == null ? null : DateTime.parse(completedAt as String),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'input_type': inputType.wire,
        'status': status.wire,
        'locale': locale,
        'failure_reason': failureReason,
        'report': report?.toJson(),
        'created_at': createdAt.toIso8601String(),
        'completed_at': completedAt?.toIso8601String(),
      };
}

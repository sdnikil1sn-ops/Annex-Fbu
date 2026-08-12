import 'package:shared_models/shared_models.dart';
import 'package:test/test.dart';

void main() {
  group('Analysis', () {
    test('round-trips the completed report shape from the API', () {
      const wire = {
        'id': '0f0a2e22-9f1b-4f0d-b6e2-5b0b7c9d3f11',
        'input_type': 'text',
        'status': 'completed',
        'locale': 'en',
        'failure_reason': null,
        'report': {
          'summary': 'Two claims were checked.',
          'claims': [
            {'text': 'The sky is blue', 'verifiability': 0.9},
            {'text': 'Gravity exists', 'verifiability': 0.8},
          ],
        },
        'created_at': '2026-08-12T10:00:00Z',
        'completed_at': '2026-08-12T10:00:02Z',
      };

      final analysis = Analysis.fromJson(wire);
      expect(analysis.status, AnalysisStatus.completed);
      expect(analysis.isTerminal, isTrue);
      expect(analysis.inputType, AnalysisInputType.text);
      expect(analysis.report!.claims, hasLength(2));
      expect(analysis.report!.claims.first.text, 'The sky is blue');
      expect(analysis.report!.claims.first.verifiability, closeTo(0.9, 0.001));
      expect(analysis.report!.credibilityScore, closeTo(0.85, 0.001));

      final decoded = Analysis.fromJson(analysis.toJson());
      expect(decoded.id, analysis.id);
      expect(decoded.status, analysis.status);
      expect(decoded.report!.toJson(), analysis.report!.toJson());
    });

    test('pending analyses have no report and are not terminal', () {
      final analysis = Analysis(
        id: 'a',
        inputType: AnalysisInputType.text,
        status: AnalysisStatus.pending,
        locale: 'en',
        createdAt: DateTime.utc(2026, 8, 12),
      );
      expect(analysis.isTerminal, isFalse);
      expect(analysis.report, isNull);
    });

    test('failed analyses carry a structured failure reason', () {
      final analysis = Analysis.fromJson(const {
        'id': 'b',
        'input_type': 'url',
        'status': 'failed',
        'locale': 'pt',
        'failure_reason': 'analysis.processing_failed',
        'report': null,
        'created_at': '2026-08-12T10:00:00Z',
        'completed_at': '2026-08-12T10:00:05Z',
      });
      expect(analysis.hasFailed, isTrue);
      expect(analysis.failureReason, 'analysis.processing_failed');
    });

    test('rejects malformed input', () {
      expect(() => Analysis.fromJson(const {'status': 'completed'}),
          throwsFormatException);
      expect(
        () => Analysis.fromJson(const {
          'id': 'a',
          'input_type': 'text',
          'status': 'unknown_status',
          'locale': 'en',
          'created_at': '2026-08-12T10:00:00Z',
        }),
        throwsFormatException,
      );
    });
  });

  group('AnalysisReport', () {
    test('credibility score averages claim verifiability', () {
      const report = AnalysisReport(
        summary: 's',
        claims: [
          ClaimItem(text: 'a', verifiability: 1),
          ClaimItem(text: 'b', verifiability: 0.5),
          ClaimItem(text: 'c', verifiability: 0),
        ],
      );
      expect(report.credibilityScore, closeTo(0.5, 0.001));
    });

    test('empty claims score zero', () {
      const report = AnalysisReport(summary: 's', claims: []);
      expect(report.credibilityScore, 0);
    });

    test('rejects non-numeric verifiability', () {
      expect(
        () => ClaimItem.fromJson(const {'text': 'a', 'verifiability': 'high'}),
        throwsFormatException,
      );
    });
  });
}

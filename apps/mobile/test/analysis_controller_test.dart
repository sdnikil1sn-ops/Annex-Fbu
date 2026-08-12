import 'package:annex_mobile/core/api/analysis_api.dart';
import 'package:annex_mobile/core/api/mock_analysis_api.dart';
import 'package:annex_mobile/features/analysis/analysis_controller.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_models/shared_models.dart';

void main() {
  test('submit → poll → completed with report', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = AnalysisController(
      api: api,
      pollInterval: const Duration(milliseconds: 20),
    );
    addTearDown(controller.dispose);

    expect(controller.state, AnalysisFlowState.idle);

    final submitted = controller.submit('The Earth orbits the Sun');
    await Future<void>.delayed(const Duration(milliseconds: 10));
    expect(controller.state, AnalysisFlowState.polling);

    await submitted;
    await Future<void>.delayed(const Duration(milliseconds: 60));

    expect(controller.state, AnalysisFlowState.completed);
    expect(controller.report, isNotNull);
    expect(controller.report!.claims, isNotEmpty);
    expect(api.lastSubmittedText, 'The Earth orbits the Sun');
  });

  test('trigger text produces a failed analysis', () async {
    final api = MockAnalysisApi(delay: Duration.zero, failTrigger: '!!!');
    final controller = AnalysisController(
      api: api,
      pollInterval: const Duration(milliseconds: 20),
    );
    addTearDown(controller.dispose);

    final submitted = controller.submit('This is broken !!!');
    await submitted;
    await Future<void>.delayed(const Duration(milliseconds: 60));

    expect(controller.state, AnalysisFlowState.failed);
    expect(controller.failureReason, 'analysis.processing_failed');
  });

  test('blank input is ignored', () async {
    final api = MockAnalysisApi();
    final controller = AnalysisController(api: api);
    addTearDown(controller.dispose);

    await controller.submit('   ');

    expect(controller.state, AnalysisFlowState.idle);
    expect(api.lastSubmittedText, isNull);
  });

  test('notifies listeners on state changes', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = AnalysisController(
      api: api,
      pollInterval: const Duration(milliseconds: 20),
    );
    addTearDown(controller.dispose);

    var notifications = 0;
    controller.addListener(() => notifications++);
    controller.submit('text');
    await Future<void>.delayed(const Duration(milliseconds: 80));

    expect(notifications, greaterThanOrEqualTo(3));
    expect(controller.analysis, isNotNull);
  });

  test('failed fetch surfaces an error state', () async {
    final api = _ThrowingApi();
    final controller = AnalysisController(api: api);
    addTearDown(controller.dispose);

    await controller.submit('hello');

    expect(controller.state, AnalysisFlowState.failed);
    expect(controller.error, contains('boom'));
  });
}

/// An API that always fails — exercises the error path.
class _ThrowingApi extends MockAnalysisApi {
  @override
  Future<Analysis> submitText(String text, {String locale = 'en'}) async {
    throw ApiException('network.error', 'boom: no connection');
  }
}

/// Analysis screen — submit text, watch the pipeline, render the report.
library;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_models/shared_models.dart';
import 'package:shared_ui/shared_ui.dart';
import 'package:shared_utils/shared_utils.dart';

import '../../app/app_scope.dart';
import '../../l10n/i18n_controller.dart';
import 'analysis_controller.dart';

/// The claim-analysis flow UI.
class AnalysisScreen extends StatefulWidget {
  const AnalysisScreen({super.key});

  @override
  State<AnalysisScreen> createState() => _AnalysisScreenState();
}

class _AnalysisScreenState extends State<AnalysisScreen> {
  final TextEditingController _text = TextEditingController();

  @override
  void dispose() {
    _text.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final i18n = AppScope.of(context).i18n;
    final controller = context.watch<AnalysisController>();

    return Scaffold(
      appBar: AppBar(title: Text(i18n.t(StringKeys.analysisTitle))),
      body: ListView(
        padding: const EdgeInsets.all(AppSpacing.lg),
        children: [
          _buildInput(context, i18n, controller),
          const SizedBox(height: AppSpacing.lg),
          ..._buildFlow(context, i18n, controller),
        ],
      ),
    );
  }

  Widget _buildInput(
    BuildContext context,
    I18nController i18n,
    AnalysisController controller,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        TextField(
          controller: _text,
          minLines: 3,
          maxLines: 8,
          maxLength: 20000,
          enabled: !controller.busy,
          decoration: InputDecoration(
            hintText: i18n.t(StringKeys.analysisInputHint),
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        AppButton(
          label: i18n.t(StringKeys.analysisSubmit),
          icon: Icons.analytics_outlined,
          busy: controller.state == AnalysisFlowState.submitting,
          expanded: true,
          onPressed: () => controller.submit(
            _text.text,
            locale: AppScope.of(context).i18n.locale,
          ),
        ),
      ],
    );
  }

  List<Widget> _buildFlow(
    BuildContext context,
    I18nController i18n,
    AnalysisController controller,
  ) {
    switch (controller.state) {
      case AnalysisFlowState.idle:
        return [];
      case AnalysisFlowState.submitting:
        return [
          Center(
            child: StatusPill(
              label: i18n.t(StringKeys.analysisPending),
              state: PillState.processing,
            ),
          ),
        ];
      case AnalysisFlowState.polling:
        return [
          Center(
            child: StatusPill(
              label: i18n.t(StringKeys.analysisProcessing),
              state: PillState.processing,
            ),
          ),
        ];
      case AnalysisFlowState.completed:
        final report = controller.report;
        if (report == null) return const [];
        return [_ReportView(report: report, i18n: i18n)];
      case AnalysisFlowState.failed:
        return [
          Center(
            child: StatusPill(
              label: i18n.t(StringKeys.analysisFailed),
              state: PillState.failure,
            ),
          ),
          if (controller.error != null) ...[
            const SizedBox(height: AppSpacing.sm),
            Text(
              controller.error!,
              style: AppTypography.bodyMedium,
              textAlign: TextAlign.center,
            ),
          ],
        ];
    }
  }
}

/// Renders a completed analysis report.
class _ReportView extends StatelessWidget {
  const _ReportView({required this.report, required this.i18n});

  final AnalysisReport report;
  final I18nController i18n;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Center(
          child: ScoreMeter(
            score: report.credibilityScore,
            label: i18n.t(StringKeys.analysisCredibilityScore),
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
        Text(
          i18n.t(StringKeys.analysisSummary),
          style: AppTypography.titleLarge,
        ),
        const SizedBox(height: AppSpacing.xs),
        Text(report.summary, style: AppTypography.bodyLarge),
        const SizedBox(height: AppSpacing.lg),
        for (final claim in report.claims) ...[
          ClaimCard(
            text: claim.text,
            verifiability: claim.verifiability,
            label: i18n.t(StringKeys.analysisVerifiability),
          ),
          const SizedBox(height: AppSpacing.sm),
        ],
      ],
    );
  }
}

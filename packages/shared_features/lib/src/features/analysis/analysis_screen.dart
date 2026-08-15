/// Analysis screen — submit text or an image, watch the pipeline, render
/// the report (with OCR + forensics context for images).
library;

import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import 'package:shared_models/shared_models.dart';
import 'package:shared_ui/shared_ui.dart';
import 'package:shared_utils/shared_utils.dart';

import '../../app/app_scope.dart';
import '../../i18n/i18n_controller.dart';
import 'analysis_controller.dart';

/// The claim-analysis flow UI (text and image inputs).
class AnalysisScreen extends StatefulWidget {
  const AnalysisScreen({super.key});

  @override
  State<AnalysisScreen> createState() => _AnalysisScreenState();
}

/// The active input mode.
enum _InputMode { text, image }

class _AnalysisScreenState extends State<AnalysisScreen> {
  final TextEditingController _text = TextEditingController();
  final ImagePicker _picker = ImagePicker();
  _InputMode _mode = _InputMode.text;
  XFile? _image;
  Uint8List? _imageBytes;
  String? _pickError;

  @override
  void initState() {
    super.initState();
    // Rebuild so the Analyze button tracks whether input is present.
    _text.addListener(() => setState(() {}));
  }

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
      body: ListView(
        padding: const EdgeInsets.all(AppSpacing.lg),
        children: [
          PageHeader(
            icon: Icons.analytics_outlined,
            title: i18n.t(StringKeys.analysisTitle),
            subtitle: i18n.t(StringKeys.analysisSubtitle),
          ),
          const SizedBox(height: AppSpacing.lg),
          SegmentedButton<_InputMode>(
            segments: [
              ButtonSegment(
                value: _InputMode.text,
                icon: const Icon(Icons.notes_rounded, size: 18),
                label: Text(i18n.t(StringKeys.analysisModeText)),
              ),
              ButtonSegment(
                value: _InputMode.image,
                icon: const Icon(Icons.image_outlined, size: 18),
                label: Text(i18n.t(StringKeys.analysisModeImage)),
              ),
            ],
            selected: {_mode},
            onSelectionChanged: (selection) {
              setState(() {
                _mode = selection.first;
                _pickError = null;
                controller.reset();
              });
            },
          ),
          const SizedBox(height: AppSpacing.md),
          if (_mode == _InputMode.text)
            _buildTextInput(context, i18n, controller)
          else
            _buildImageInput(context, i18n, controller),
          const SizedBox(height: AppSpacing.lg),
          ..._buildFlow(context, i18n, controller),
        ],
      ),
    );
  }

  Widget _buildTextInput(
    BuildContext context,
    I18nController i18n,
    AnalysisController controller,
  ) {
    final colorScheme = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _ExampleChips(
              onSelect: controller.busy
                  ? null
                  : (example) => setState(() => _text.text = example),
            ),
            const SizedBox(height: AppSpacing.md),
            TextField(
              controller: _text,
              minLines: 6,
              maxLines: 12,
              maxLength: 20000,
              enabled: !controller.busy,
              decoration: InputDecoration(
                hintText: i18n.t(StringKeys.analysisInputHint),
                hintMaxLines: 2,
                filled: true,
                fillColor: colorScheme.surfaceContainerHighest
                    .withValues(alpha: 0.4),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            AppButton(
              label: i18n.t(StringKeys.analysisSubmit),
              icon: Icons.analytics_outlined,
              busy: controller.state == AnalysisFlowState.submitting,
              expanded: true,
              onPressed: _text.text.trim().isEmpty
                  ? null
                  : () => controller.submit(
                        _text.text,
                        locale: AppScope.of(context).i18n.locale,
                      ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildImageInput(
    BuildContext context,
    I18nController i18n,
    AnalysisController controller,
  ) {
    final colorScheme = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (_image == null)
              InkWell(
                onTap: controller.busy ? null : () => _pickImage(),
                borderRadius: BorderRadius.circular(AppSpacing.radiusLg),
                child: Container(
                  height: 180,
                  decoration: BoxDecoration(
                    color: colorScheme.surfaceContainerHighest
                        .withValues(alpha: 0.5),
                    borderRadius: BorderRadius.circular(AppSpacing.radiusLg),
                    border: Border.all(
                      color: colorScheme.outline.withValues(alpha: 0.5),
                    ),
                  ),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.add_photo_alternate_outlined,
                        size: 42,
                        color: colorScheme.onSurfaceVariant,
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      Text(
                        i18n.t(StringKeys.analysisImageChoose),
                        style: AppTypography.titleSmall,
                      ),
                      const SizedBox(height: AppSpacing.xxs),
                      Padding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.lg,
                        ),
                        child: Text(
                          i18n.t(StringKeys.analysisImageHint),
                          style: AppTypography.bodySmall.copyWith(
                            color: colorScheme.onSurfaceVariant,
                          ),
                          textAlign: TextAlign.center,
                        ),
                      ),
                    ],
                  ),
                ),
              )
            else ...[
              ClipRRect(
                borderRadius: BorderRadius.circular(AppSpacing.radiusLg),
                child: Image.memory(
                  _imageBytes!,
                  height: 220,
                  fit: BoxFit.cover,
                  width: double.infinity,
                ),
              ),
              const SizedBox(height: AppSpacing.sm),
              Row(
                children: [
                  Expanded(
                    child: AppButton(
                      label: i18n.t(StringKeys.analysisImageChange),
                      icon: Icons.swap_horiz_rounded,
                      variant: AppButtonVariant.outlined,
                      expanded: true,
                      onPressed: controller.busy ? null : () => _pickImage(),
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    flex: 2,
                    child: AppButton(
                      label: i18n.t(StringKeys.analysisImageSubmit),
                      icon: Icons.analytics_outlined,
                      busy: controller.state == AnalysisFlowState.submitting,
                      expanded: true,
                      onPressed: () => controller.submitImage(
                        _imageDataUrl()!,
                        locale: AppScope.of(context).i18n.locale,
                      ),
                    ),
                  ),
                ],
              ),
            ],
            if (_pickError != null) ...[
              const SizedBox(height: AppSpacing.sm),
              Text(
                _pickError!,
                style: AppTypography.bodySmall.copyWith(
                  color: colorScheme.error,
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _pickImage() async {
    try {
      final picked = await _picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 2400,
        imageQuality: 90,
      );
      if (picked == null) return;
      final bytes = await picked.readAsBytes();
      if (!mounted) return;
      setState(() {
        _image = picked;
        _imageBytes = bytes;
        _pickError = null;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _pickError = 'Could not read that image.');
    }
  }

  String? _imageDataUrl() {
    final bytes = _imageBytes;
    if (bytes == null) return null;
    return 'data:image/jpeg;base64,${base64Encode(bytes)}';
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
          AppErrorState(
            title: i18n.t(StringKeys.analysisFailed),
            message: controller.error,
            action: StateAction(
              label: i18n.t(StringKeys.commonRetry),
              onPressed: () {
                if (_mode == _InputMode.image && _image != null) {
                  controller.submitImage(
                    _imageDataUrl()!,
                    locale: AppScope.of(context).i18n.locale,
                  );
                } else {
                  controller.submit(
                    _text.text,
                    locale: AppScope.of(context).i18n.locale,
                  );
                }
              },
            ),
          ),
        ];
    }
  }
}

/// Renders a completed analysis report (score, summary, claims, and for
/// image inputs the OCR + forensics context).
class _ReportView extends StatelessWidget {
  const _ReportView({required this.report, required this.i18n});

  final AnalysisReport report;
  final I18nController i18n;

  @override
  Widget build(BuildContext context) {
    final media = report.media;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Column(
              children: [
                ScoreMeter(
                  score: report.credibilityScore,
                  size: 112,
                  label: i18n.t(StringKeys.analysisCredibilityScore),
                ),
              ],
            ),
          ),
        ),
        if (media != null) ...[
          const SizedBox(height: AppSpacing.lg),
          _MediaContextCard(media: media, i18n: i18n),
        ],
        const SizedBox(height: AppSpacing.lg),
        Text(
          i18n.t(StringKeys.analysisSummary),
          style: AppTypography.titleLarge,
        ),
        const SizedBox(height: AppSpacing.xs),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: Text(report.summary, style: AppTypography.bodyLarge),
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
        if (report.claims.isEmpty)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(AppSpacing.lg),
              child: Row(
                children: [
                  Icon(
                    Icons.verified_outlined,
                    color: AppColors.success,
                    size: 22,
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: Text(
                      i18n.t(StringKeys.analysisNoClaims),
                      style: AppTypography.bodyMedium,
                    ),
                  ),
                ],
              ),
            ),
          ),
        for (final claim in report.claims) ...[
          ClaimCard(
            text: claim.text,
            verifiability: claim.verifiability,
            label: i18n.t(StringKeys.analysisVerifiability),
            verdict: claim.verdict,
            rationale: claim.rationale,
            evidence: [
              for (final item in claim.evidence)
                ClaimEvidenceView(
                  url: item.url,
                  quote: item.quote,
                  snippet: item.snippet,
                ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
        ],
      ],
    );
  }
}

/// Quick-start example prompts for the text input.
class _ExampleChips extends StatelessWidget {
  const _ExampleChips({required this.onSelect});

  /// Called with the example text when a chip is tapped.
  final void Function(String example)? onSelect;

  static const List<String> examples = [
    '"The Earth is flat and vaccines cause autism."',
    '"Eating chocolate daily cures headaches — miracle study proves it."',
    '"A leaked report shows the moon landing was filmed in a desert studio."',
  ];

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Try an example',
          style: AppTypography.labelMedium.copyWith(
            color: colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: AppSpacing.xs),
        Wrap(
          spacing: AppSpacing.xs,
          runSpacing: AppSpacing.xxs,
          children: [
            for (final example in examples)
              ActionChip(
                avatar: const Icon(Icons.bolt_rounded, size: 16),
                label: Text(
                  example.length > 34
                      ? '${example.substring(0, 34)}…'
                      : example,
                ),
                visualDensity: VisualDensity.compact,
                onPressed: onSelect == null
                    ? null
                    : () => onSelect!(example),
              ),
          ],
        ),
      ],
    );
  }
}

/// OCR text + forensics signals for image analyses.
class _MediaContextCard extends StatelessWidget {
  const _MediaContextCard({required this.media, required this.i18n});

  final MediaContext media;
  final I18nController i18n;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final risk = media.riskScore;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.image_search_rounded,
                  size: 20,
                  color: colorScheme.primary,
                ),
                const SizedBox(width: AppSpacing.xs),
                Text(
                  i18n.t(StringKeys.analysisImageForensics),
                  style: AppTypography.titleMedium,
                ),
              ],
            ),
            if (media.ocrText != null && media.ocrText!.isNotEmpty) ...[
              const SizedBox(height: AppSpacing.md),
              Text(
                i18n.t(StringKeys.analysisImageOcr),
                style: AppTypography.labelMedium.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: AppSpacing.xxs),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(AppSpacing.md),
                decoration: BoxDecoration(
                  color: colorScheme.surfaceContainerHighest
                      .withValues(alpha: 0.6),
                  borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
                ),
                child: Text(
                  media.ocrText!,
                  style: AppTypography.bodyMedium,
                ),
              ),
            ] else ...[
              const SizedBox(height: AppSpacing.md),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(AppSpacing.md),
                decoration: BoxDecoration(
                  color: colorScheme.surfaceContainerHighest
                      .withValues(alpha: 0.4),
                  borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
                  border: Border.all(
                    color: colorScheme.outline.withValues(alpha: 0.4),
                  ),
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.text_fields_rounded,
                      size: 18,
                      color: colorScheme.onSurfaceVariant,
                    ),
                    const SizedBox(width: AppSpacing.sm),
                    Expanded(
                      child: Text(
                        i18n.t(StringKeys.analysisImageNoText),
                        style: AppTypography.bodyMedium.copyWith(
                          color: colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            if (risk != null) ...[
              const SizedBox(height: AppSpacing.md),
              Row(
                children: [
                  Text(
                    i18n.t(StringKeys.analysisImageRisk),
                    style: AppTypography.labelMedium.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                  const Spacer(),
                  StatusPill(
                    label: '${(risk * 100).round()}%',
                    state: risk < 0.3
                        ? PillState.success
                        : risk < 0.6
                        ? PillState.processing
                        : PillState.failure,
                  ),
                ],
              ),
            ],
            const SizedBox(height: AppSpacing.md),
            Wrap(
              spacing: AppSpacing.xs,
              runSpacing: AppSpacing.xxs,
              children: [
                if (media.mime != null)
                  StatusPill(label: media.mime!, state: PillState.neutral),
                if (media.signals != null &&
                    media.signals!['width'] is num &&
                    media.signals!['height'] is num)
                  StatusPill(
                    label:
                        '${media.signals!['width']} × ${media.signals!['height']}',
                    state: PillState.neutral,
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

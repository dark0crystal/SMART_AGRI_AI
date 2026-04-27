import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../services/auth_api.dart';
import '../services/diagnosis_api.dart';

class DiagnosisDetailScreen extends StatefulWidget {
  const DiagnosisDetailScreen({super.key, required this.id});

  final int id;

  @override
  State<DiagnosisDetailScreen> createState() => _DiagnosisDetailScreenState();
}

class _DiagnosisDetailScreenState extends State<DiagnosisDetailScreen> {
  Map<String, dynamic>? _data;
  String? _error;
  bool _loading = true;

  static final DateFormat _dateFormat = DateFormat.yMMMd().add_jm();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await AuthApi.syncUser();
      final res = await DiagnosisApi.getDiagnosis(widget.id);
      if (mounted) {
        setState(() {
          _data = res;
          _loading = false;
        });
      }
    } on AuthApiException catch (e) {
      if (mounted) {
        setState(() {
          _error = e.message;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Diagnosis details'),
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    children: [
                      Padding(
                        padding: const EdgeInsets.all(24),
                        child: Text(_error!),
                      ),
                    ],
                  )
                : _data == null
                    ? const SizedBox.shrink()
                    : _buildBody(context, _data!),
      ),
    );
  }

  Widget _buildBody(BuildContext context, Map<String, dynamic> data) {
    final disease = data['disease'];
    Map<String, dynamic>? d;
    if (disease is Map<String, dynamic>) {
      d = disease;
    }

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
      physics: const AlwaysScrollableScrollPhysics(),
      children: [
        if (d != null) ...[
          _headerCard(context, d, data),
          const SizedBox(height: 12),
          _infoSummaryCard(context, data),
          const SizedBox(height: 16),
          _section(
            context,
            icon: Icons.description_outlined,
            title: 'Description',
            en: d['description_en'],
            ar: d['description_ar'],
          ),
          _section(
            context,
            icon: Icons.help_outline,
            title: 'Causes',
            en: d['causes_en'],
            ar: d['causes_ar'],
          ),
          _section(
            context,
            icon: Icons.medical_services_outlined,
            title: 'Treatment',
            en: d['treatment_en'],
            ar: d['treatment_ar'],
          ),
        ] else
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Text(
                'No disease catalog data for this record.',
                style: Theme.of(context).textTheme.bodyLarge,
              ),
            ),
          ),
        if (data['text_input'] != null &&
            data['text_input'].toString().trim().isNotEmpty) ...[
          const SizedBox(height: 8),
          _userNotesCard(context, data['text_input'].toString()),
        ],
      ],
    );
  }

  Widget _headerCard(
    BuildContext context,
    Map<String, dynamic> disease,
    Map<String, dynamic> data,
  ) {
    final cs = Theme.of(context).colorScheme;
    final nameEn = _str(disease['name_en']);
    final nameAr = _str(disease['name_ar']);
    final created = _formatDate(data['created_at']?.toString());

    return Card(
      elevation: 0,
      color: cs.primaryContainer.withValues(alpha: 0.6),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.spa_outlined, color: cs.primary, size: 28),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    nameEn.isNotEmpty ? nameEn : 'Diagnosis',
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: cs.onPrimaryContainer,
                        ),
                  ),
                ),
              ],
            ),
            if (nameAr.isNotEmpty && nameAr != nameEn) ...[
              const SizedBox(height: 12),
              Text(
                nameAr,
                textAlign: TextAlign.right,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: cs.onPrimaryContainer,
                    ),
              ),
            ],
            if (created.isNotEmpty) ...[
              const SizedBox(height: 12),
              Row(
                children: [
                  Icon(Icons.schedule, size: 18, color: cs.onSurfaceVariant),
                  const SizedBox(width: 8),
                  Text(
                    created,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: cs.onSurfaceVariant,
                        ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _infoSummaryCard(BuildContext context, Map<String, dynamic> data) {
    final cs = Theme.of(context).colorScheme;
    final confidence = data['confidence_score'];
    final confText = confidence is num
        ? '${(confidence * 100).clamp(0, 100).toStringAsFixed(1)}%'
        : '—';
    final inputType = data['input_type']?.toString() ?? '—';
    final imageUrl = data['image_url']?.toString();
    final hasImage = imageUrl != null && imageUrl.isNotEmpty;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Record',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
            const SizedBox(height: 12),
            _infoRow(
              context,
              Icons.analytics_outlined,
              'Model confidence',
              confText,
            ),
            const Divider(height: 20),
            _infoRow(
              context,
              Icons.input,
              'Input type',
              inputType == 'image' ? 'Photo' : 'Text',
            ),
            if (hasImage) ...[
              const Divider(height: 20),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.image_outlined, size: 20, color: cs.primary),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Photo',
                          style:
                              Theme.of(context).textTheme.labelMedium?.copyWith(
                                    color: cs.onSurfaceVariant,
                                  ),
                        ),
                        const SizedBox(height: 8),
                        _diagnosisPhotoPreview(context, imageUrl),
                      ],
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _diagnosisPhotoPreview(BuildContext context, String imageUrl) {
    final cs = Theme.of(context).colorScheme;

    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: AspectRatio(
        aspectRatio: 4 / 3,
        child: Image.network(
          imageUrl,
          fit: BoxFit.cover,
          alignment: Alignment.center,
          loadingBuilder: (context, child, loadingProgress) {
            if (loadingProgress == null) return child;
            return ColoredBox(
              color: cs.surfaceContainerHighest,
              child: Center(
                child: SizedBox(
                  width: 28,
                  height: 28,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    value: loadingProgress.expectedTotalBytes != null
                        ? loadingProgress.cumulativeBytesLoaded /
                            loadingProgress.expectedTotalBytes!
                        : null,
                  ),
                ),
              ),
            );
          },
          errorBuilder: (context, error, stackTrace) {
            return ColoredBox(
              color: cs.errorContainer,
              child: Center(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.broken_image_outlined,
                        color: cs.onErrorContainer,
                        size: 36,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Could not load image',
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: cs.onErrorContainer,
                            ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _infoRow(
    BuildContext context,
    IconData icon,
    String label,
    String value,
  ) {
    final cs = Theme.of(context).colorScheme;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 20, color: cs.primary),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: cs.onSurfaceVariant,
                    ),
              ),
              const SizedBox(height: 2),
              Text(
                value,
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      fontWeight: FontWeight.w500,
                    ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _section(
    BuildContext context, {
    required IconData icon,
    required String title,
    required dynamic en,
    required dynamic ar,
  }) {
    final enS = _str(en);
    final arS = _str(ar);
    final hasEn = enS.isNotEmpty;
    final hasAr = arS.isNotEmpty;
    if (!hasEn && !hasAr) {
      return const SizedBox.shrink();
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(icon, size: 22, color: Theme.of(context).colorScheme.primary),
                  const SizedBox(width: 8),
                  Text(
                    title,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              if (hasEn) ...[
                Text(
                  'English',
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                        letterSpacing: 0.5,
                      ),
                ),
                const SizedBox(height: 4),
                Text(
                  enS,
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
              ],
              if (hasEn && hasAr) const SizedBox(height: 14),
              if (hasAr) ...[
                Text(
                  'العربية',
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                        letterSpacing: 0.5,
                      ),
                ),
                const SizedBox(height: 4),
                Text(
                  arS,
                  textAlign: TextAlign.right,
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _userNotesCard(BuildContext context, String text) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.notes_rounded,
                    color: Theme.of(context).colorScheme.primary),
                const SizedBox(width: 8),
                Text(
                  'Your symptom notes',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              text.trim(),
              style: Theme.of(context).textTheme.bodyLarge,
            ),
          ],
        ),
      ),
    );
  }

  String _str(dynamic v) => v?.toString().trim() ?? '';

  String _formatDate(String? iso) {
    if (iso == null || iso.isEmpty) return '';
    try {
      return _dateFormat.format(DateTime.parse(iso).toLocal());
    } catch (_) {
      return iso;
    }
  }
}

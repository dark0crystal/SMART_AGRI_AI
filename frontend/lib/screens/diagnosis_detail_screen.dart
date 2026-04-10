import 'package:flutter/material.dart';

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
      appBar: AppBar(title: const Text('Diagnosis result')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? ListView(
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
      padding: const EdgeInsets.all(24),
      children: [
        if (d != null) ...[
          Text(
            d['name_en']?.toString() ?? '—',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          Text(
            d['name_ar']?.toString() ?? '',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 16),
          _section(context, 'Description', d['description_en'], d['description_ar']),
          _section(context, 'Causes', d['causes_en'], d['causes_ar']),
          _section(context, 'Treatment', d['treatment_en'], d['treatment_ar']),
        ] else
          const Text('No disease data.'),
        const Divider(height: 32),
        Text('Confidence: ${data['confidence_score'] ?? '—'}'),
        Text('Input: ${data['input_type'] ?? '—'}'),
        if (data['text_input'] != null &&
            data['text_input'].toString().isNotEmpty)
          Text('Your text: ${data['text_input']}'),
      ],
    );
  }

  Widget _section(
    BuildContext context,
    String title,
    dynamic en,
    dynamic ar,
  ) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 4),
          Text(en?.toString() ?? '—'),
          if (ar != null && ar.toString().isNotEmpty)
            Text(ar.toString(), textAlign: TextAlign.right),
        ],
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../services/auth_api.dart';
import '../services/diagnosis_api.dart';

class DiagnosisHistoryScreen extends StatefulWidget {
  const DiagnosisHistoryScreen({super.key});

  @override
  State<DiagnosisHistoryScreen> createState() => _DiagnosisHistoryScreenState();
}

class _DiagnosisHistoryScreenState extends State<DiagnosisHistoryScreen> {
  List<dynamic> _items = [];
  String? _error;
  bool _loading = true;

  static final DateFormat _dateFormat =
      DateFormat.yMMMd().add_jm(); // localized date + time

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
      final res = await DiagnosisApi.listDiagnoses();
      final results = res['results'];
      if (results is List) {
        _items = results;
      } else {
        _items = [];
      }
    } on AuthApiException catch (e) {
      _error = e.message;
    } catch (e) {
      _error = e.toString();
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  String _formatCreatedAt(String? iso) {
    if (iso == null || iso.isEmpty) return '—';
    try {
      return _dateFormat.format(DateTime.parse(iso).toLocal());
    } catch (_) {
      return iso;
    }
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Diagnosis history'),
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
                : _items.isEmpty
                    ? ListView(
                        physics: const AlwaysScrollableScrollPhysics(),
                        children: const [
                          Padding(
                            padding: EdgeInsets.all(32),
                            child: Center(
                              child: Text(
                                'No diagnoses yet.\n'
                                'Start from the home screen to add one.',
                                textAlign: TextAlign.center,
                              ),
                            ),
                          ),
                        ],
                      )
                    : ListView.separated(
                        padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
                        physics: const AlwaysScrollableScrollPhysics(),
                        itemCount: _items.length,
                        separatorBuilder: (context, index) =>
                            const SizedBox(height: 12),
                        itemBuilder: (context, i) {
                          final row = _items[i] as Map<String, dynamic>;
                          final idRaw = row['id'];
                          final id = idRaw is int
                              ? idRaw
                              : (idRaw is num ? idRaw.toInt() : null);
                          final disease = row['disease'];
                          String title = 'Diagnosis';
                          if (disease is Map && disease['name_en'] != null) {
                            title = disease['name_en'].toString();
                          }
                          final createdRaw = row['created_at']?.toString();
                          final inputType =
                              row['input_type']?.toString() ?? '';

                          return Card(
                            elevation: 1,
                            clipBehavior: Clip.antiAlias,
                            child: InkWell(
                              onTap: id == null
                                  ? null
                                  : () => context.push('/diagnosis/detail/$id'),
                              child: Padding(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 16,
                                  vertical: 14,
                                ),
                                child: Row(
                                  children: [
                                    CircleAvatar(
                                      backgroundColor:
                                          colorScheme.primaryContainer,
                                      foregroundColor:
                                          colorScheme.onPrimaryContainer,
                                      child: Icon(
                                        inputType == 'image'
                                            ? Icons.photo_outlined
                                            : Icons.text_fields_rounded,
                                        size: 22,
                                      ),
                                    ),
                                    const SizedBox(width: 14),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            title,
                                            style: Theme.of(context)
                                                .textTheme
                                                .titleMedium
                                                ?.copyWith(
                                                  fontWeight: FontWeight.w600,
                                                ),
                                            maxLines: 2,
                                            overflow: TextOverflow.ellipsis,
                                          ),
                                          const SizedBox(height: 6),
                                          Text(
                                            _formatCreatedAt(createdRaw),
                                            style: Theme.of(context)
                                                .textTheme
                                                .bodySmall
                                                ?.copyWith(
                                                  color: colorScheme
                                                      .onSurfaceVariant,
                                                ),
                                          ),
                                        ],
                                      ),
                                    ),
                                    Icon(
                                      Icons.chevron_right_rounded,
                                      color: colorScheme.onSurfaceVariant,
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
}

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Diagnosis history')),
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
                : _items.isEmpty
                    ? ListView(
                        children: const [
                          Padding(
                            padding: EdgeInsets.all(24),
                            child: Text('No diagnoses yet.'),
                          ),
                        ],
                      )
                    : ListView.builder(
                        itemCount: _items.length,
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
                          final created = row['created_at']?.toString() ?? '';
                          return ListTile(
                            title: Text(title),
                            subtitle: Text(created),
                            onTap: () {
                              if (id != null) {
                                context.push('/diagnosis/detail/$id');
                              }
                            },
                          );
                        },
                      ),
      ),
    );
  }
}

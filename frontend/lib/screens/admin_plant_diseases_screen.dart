import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../services/admin_catalog_api.dart';
import '../services/auth_api.dart' show AuthApiException;

class AdminPlantDiseasesScreen extends StatefulWidget {
  const AdminPlantDiseasesScreen({super.key, required this.plantId});

  final int plantId;

  @override
  State<AdminPlantDiseasesScreen> createState() => _AdminPlantDiseasesScreenState();
}

class _AdminPlantDiseasesScreenState extends State<AdminPlantDiseasesScreen> {
  bool _loading = true;
  String? _error;
  String _plantTitle = '';
  List<dynamic> _diseases = [];

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
      final res = await AdminCatalogApi.listDiseasesForPlant(widget.plantId);
      if (!mounted) return;
      final plant = res['plant'];
      if (plant is Map) {
        _plantTitle = plant['name_en']?.toString() ?? 'Plant';
      } else {
        _plantTitle = 'Plant ${widget.plantId}';
      }
      final results = res['results'];
      setState(() {
        _diseases = results is List ? results : [];
        _loading = false;
      });
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
        title: Text(_plantTitle.isEmpty ? 'Diseases' : _plantTitle),
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
                        child: Text(_error!, textAlign: TextAlign.center),
                      ),
                    ],
                  )
                : ListView.separated(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
                    itemCount: _diseases.length,
                    separatorBuilder: (context, index) =>
                        const SizedBox(height: 10),
                    itemBuilder: (context, i) {
                      final row = _diseases[i] as Map<String, dynamic>;
                      final idRaw = row['id'];
                      final id = idRaw is int
                          ? idRaw
                          : int.tryParse('$idRaw');
                      final name =
                          row['name_en']?.toString() ?? 'Disease';
                      if (id == null) {
                        return const SizedBox.shrink();
                      }
                      return Card(
                        clipBehavior: Clip.antiAlias,
                        child: ListTile(
                          leading: CircleAvatar(
                            backgroundColor: Theme.of(context)
                                .colorScheme
                                .secondaryContainer,
                            foregroundColor: Theme.of(context)
                                .colorScheme
                                .onSecondaryContainer,
                            child: const Icon(Icons.coronavirus_outlined),
                          ),
                          title: Text(name),
                          subtitle: row['name_ar'] != null &&
                                  row['name_ar'].toString().isNotEmpty
                              ? Text(
                                  row['name_ar'].toString(),
                                  textAlign: TextAlign.right,
                                )
                              : null,
                          trailing:
                              const Icon(Icons.edit_outlined),
                          onTap: () =>
                              context.push('/admin/disease/$id'),
                        ),
                      );
                    },
                  ),
      ),
    );
  }
}

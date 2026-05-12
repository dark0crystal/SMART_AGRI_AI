import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../services/admin_catalog_api.dart';
import '../services/auth_api.dart';
import '../services/session_sync.dart';

/// Admin entry: manage disease catalog (plants → diseases → bilingual text).
class AdminCatalogScreen extends StatefulWidget {
  const AdminCatalogScreen({super.key});

  @override
  State<AdminCatalogScreen> createState() => _AdminCatalogScreenState();
}

class _AdminCatalogScreenState extends State<AdminCatalogScreen> {
  bool _gateLoading = true;
  bool _allowed = false;
  String? _gateError;

  bool _listLoading = false;
  List<dynamic> _plants = [];
  String? _listError;

  @override
  void initState() {
    super.initState();
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    setState(() {
      _gateLoading = true;
      _gateError = null;
    });
    try {
      await SessionSync.ensure();
      final me = await AuthApi.me();
      final role = me['role']?.toString().toLowerCase();
      if (!mounted) return;
      if (role != 'admin') {
        setState(() {
          _allowed = false;
          _gateLoading = false;
        });
        return;
      }
      setState(() {
        _allowed = true;
        _gateLoading = false;
      });
      await _loadPlants();
    } on AuthApiException catch (e) {
      if (mounted) {
        setState(() {
          _gateError = e.message;
          _gateLoading = false;
          _allowed = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _gateError = e.toString();
          _gateLoading = false;
          _allowed = false;
        });
      }
    }
  }

  Future<void> _loadPlants() async {
    setState(() {
      _listLoading = true;
      _listError = null;
    });
    try {
      final res = await AdminCatalogApi.listPlants();
      final results = res['results'];
      if (!mounted) return;
      setState(() {
        _plants = results is List ? results : [];
        _listLoading = false;
      });
    } on AuthApiException catch (e) {
      if (mounted) {
        setState(() {
          _listError = e.message;
          _listLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _listError = e.toString();
          _listLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Disease catalog'),
      ),
      body: RefreshIndicator(
        onRefresh: _bootstrap,
        child: _gateLoading
            ? const Center(child: CircularProgressIndicator())
            : _gateError != null
                ? ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    children: [
                      Padding(
                        padding: const EdgeInsets.all(24),
                        child: Text(_gateError!, textAlign: TextAlign.center),
                      ),
                    ],
                  )
                : !_allowed
                    ? ListView(
                        physics: const AlwaysScrollableScrollPhysics(),
                        children: [
                          Padding(
                            padding: const EdgeInsets.all(24),
                            child: Text(
                              'This area is only available to accounts with '
                              'the administrator role.',
                              textAlign: TextAlign.center,
                              style: Theme.of(context).textTheme.bodyLarge,
                            ),
                          ),
                        ],
                      )
                    : _listLoading && _plants.isEmpty
                        ? const Center(child: CircularProgressIndicator())
                        : _listError != null && _plants.isEmpty
                            ? ListView(
                                physics: const AlwaysScrollableScrollPhysics(),
                                children: [
                                  Padding(
                                    padding: const EdgeInsets.all(24),
                                    child: Text(
                                      _listError!,
                                      textAlign: TextAlign.center,
                                    ),
                                  ),
                                ],
                              )
                            : ListView(
                                physics: const AlwaysScrollableScrollPhysics(),
                                padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                                children: [
                                  Text(
                                    'Choose a plant to edit disease names, '
                                    'descriptions, and treatments shown '
                                    'in the app after diagnosis.',
                                    style: Theme.of(context)
                                        .textTheme
                                        .bodyMedium
                                        ?.copyWith(
                                          color: Theme.of(context)
                                              .colorScheme
                                              .onSurfaceVariant,
                                        ),
                                  ),
                                  const SizedBox(height: 16),
                                  ...(_plants.map((raw) {
                                    final row = raw as Map<String, dynamic>;
                                    final idRaw = row['id'];
                                    final id = idRaw is int
                                        ? idRaw
                                        : int.tryParse('$idRaw');
                                    final name =
                                        row['name_en']?.toString() ?? 'Plant';
                                    if (id == null) {
                                      return const SizedBox.shrink();
                                    }
                                    return Padding(
                                      padding:
                                          const EdgeInsets.only(bottom: 10),
                                      child: Card(
                                        clipBehavior: Clip.antiAlias,
                                        child: ListTile(
                                          leading: CircleAvatar(
                                            backgroundColor: Theme.of(context)
                                                .colorScheme
                                                .primaryContainer,
                                            foregroundColor: Theme.of(context)
                                                .colorScheme
                                                .onPrimaryContainer,
                                            child: const Icon(
                                                Icons.local_florist_outlined),
                                          ),
                                          title: Text(name),
                                          subtitle:
                                              row['name_ar'] != null &&
                                                      row['name_ar']
                                                          .toString()
                                                          .isNotEmpty
                                                  ? Text(
                                                      row['name_ar'].toString(),
                                                      textAlign: TextAlign.right,
                                                    )
                                                  : null,
                                          trailing: const Icon(
                                              Icons.chevron_right_rounded),
                                          onTap: () => context
                                              .push('/admin/plant/$id'),
                                        ),
                                      ),
                                    );
                                  }).toList()),
                                ],
                              ),
      ),
    );
  }
}

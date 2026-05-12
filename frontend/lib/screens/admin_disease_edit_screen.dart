import 'package:flutter/material.dart';

import '../services/admin_catalog_api.dart';
import '../services/auth_api.dart' show AuthApiException;

class AdminDiseaseEditScreen extends StatefulWidget {
  const AdminDiseaseEditScreen({super.key, required this.diseaseId});

  final int diseaseId;

  @override
  State<AdminDiseaseEditScreen> createState() => _AdminDiseaseEditScreenState();
}

class _AdminDiseaseEditScreenState extends State<AdminDiseaseEditScreen> {
  final _formKey = GlobalKey<FormState>();

  bool _loading = true;
  bool _saving = false;
  String? _error;

  late final TextEditingController _nameEn;
  late final TextEditingController _nameAr;
  late final TextEditingController _descEn;
  late final TextEditingController _descAr;
  late final TextEditingController _treatEn;
  late final TextEditingController _treatAr;

  String _title = 'Edit disease';

  @override
  void initState() {
    super.initState();
    _nameEn = TextEditingController();
    _nameAr = TextEditingController();
    _descEn = TextEditingController();
    _descAr = TextEditingController();
    _treatEn = TextEditingController();
    _treatAr = TextEditingController();
    _load();
  }

  @override
  void dispose() {
    _nameEn.dispose();
    _nameAr.dispose();
    _descEn.dispose();
    _descAr.dispose();
    _treatEn.dispose();
    _treatAr.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final d = await AdminCatalogApi.getDisease(widget.diseaseId);
      if (!mounted) return;
      _nameEn.text = d['name_en']?.toString() ?? '';
      _nameAr.text = d['name_ar']?.toString() ?? '';
      _descEn.text = d['description_en']?.toString() ?? '';
      _descAr.text = d['description_ar']?.toString() ?? '';
      _treatEn.text = d['treatment_en']?.toString() ?? '';
      _treatAr.text = d['treatment_ar']?.toString() ?? '';
      final en = _nameEn.text.trim();
      setState(() {
        _title = en.isNotEmpty ? en : 'Edit disease';
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

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);
    try {
      final body = <String, dynamic>{
        'name_en': _nameEn.text.trim(),
        'name_ar': _nameAr.text.trim(),
        'description_en': _descEn.text.trim(),
        'description_ar': _descAr.text.trim(),
        'treatment_en': _treatEn.text.trim(),
        'treatment_ar': _treatAr.text.trim(),
      };
      await AdminCatalogApi.updateDisease(widget.diseaseId, body);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Saved')),
      );
      Navigator.of(context).pop();
    } on AuthApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.message)),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString())),
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Widget _sectionLabel(BuildContext context, String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8, top: 12),
      child: Text(
        text,
        style: Theme.of(context).textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.w600,
              color: Theme.of(context).colorScheme.primary,
            ),
      ),
    );
  }

  Widget _field(String label, TextEditingController c, {int maxLines = 3}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: TextFormField(
        controller: c,
        maxLines: maxLines,
        decoration: InputDecoration(
          labelText: label,
          alignLabelWithHint: maxLines > 1,
          border: const OutlineInputBorder(),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_title),
        actions: [
          if (!_loading && _error == null)
            TextButton(
              onPressed: _saving ? null : _save,
              child: _saving
                  ? const SizedBox(
                      width: 22,
                      height: 22,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Save'),
            ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Text(_error!, textAlign: TextAlign.center),
                  ),
                )
              : Form(
                  key: _formKey,
                  child: ListView(
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
                    children: [
                      Text(
                        'These texts appear on the diagnosis details screen '
                        'for users.',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: Theme.of(context)
                                  .colorScheme
                                  .onSurfaceVariant,
                            ),
                      ),
                      _sectionLabel(context, 'Names'),
                      _field('Name (English)', _nameEn, maxLines: 1),
                      _field('Name (Arabic)', _nameAr, maxLines: 1),
                      _sectionLabel(context, 'Description'),
                      _field('Description (English)', _descEn),
                      _field('Description (Arabic)', _descAr),
                      _sectionLabel(context, 'Treatment'),
                      _field('Treatment (English)', _treatEn),
                      _field('Treatment (Arabic)', _treatAr),
                      const SizedBox(height: 16),
                      FilledButton.icon(
                        onPressed: _saving ? null : _save,
                        icon: const Icon(Icons.save_outlined),
                        label: const Text('Save changes'),
                      ),
                    ],
                  ),
                ),
    );
  }
}

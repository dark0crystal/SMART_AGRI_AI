import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../services/auth_api.dart';
import '../services/diagnosis_api.dart';

class DiagnosisTextScreen extends StatefulWidget {
  const DiagnosisTextScreen({super.key});

  @override
  State<DiagnosisTextScreen> createState() => _DiagnosisTextScreenState();
}

class _DiagnosisTextScreenState extends State<DiagnosisTextScreen> {
  final _controller = TextEditingController();
  bool _loading = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final text = _controller.text.trim();
    if (text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter a description of symptoms.')),
      );
      return;
    }
    setState(() => _loading = true);
    try {
      await AuthApi.syncUser();
      final res = await DiagnosisApi.createDiagnosis(
        inputType: 'text',
        textInput: text,
      );
      if (!mounted) return;
      final raw = res['id'];
      final id = raw is int ? raw : (raw is num ? raw.toInt() : null);
      if (id != null) {
        context.pushReplacement('/diagnosis/detail/$id');
      } else {
        context.pop();
      }
    } on AuthApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.message)),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Text symptoms')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: _controller,
              decoration: const InputDecoration(
                labelText: 'Symptoms on the lemon tree',
                border: OutlineInputBorder(),
                alignLabelWithHint: true,
              ),
              minLines: 4,
              maxLines: 10,
              textCapitalization: TextCapitalization.sentences,
            ),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: _loading ? null : _submit,
              child: _loading
                  ? const SizedBox(
                      height: 22,
                      width: 22,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Submit for diagnosis'),
            ),
          ],
        ),
      ),
    );
  }
}

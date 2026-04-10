import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class DiagnosisHubScreen extends StatelessWidget {
  const DiagnosisHubScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Lemon disease diagnosis'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          Text(
            'Choose how to describe symptoms',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: () => context.push('/diagnosis/text'),
            icon: const Icon(Icons.text_fields),
            label: const Text('Describe with text'),
          ),
          const SizedBox(height: 12),
          FilledButton.tonalIcon(
            onPressed: () => context.push('/diagnosis/camera'),
            icon: const Icon(Icons.photo_camera_outlined),
            label: const Text('Take a photo'),
          ),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: () => context.push('/diagnosis/history'),
            icon: const Icon(Icons.history),
            label: const Text('Diagnosis history'),
          ),
        ],
      ),
    );
  }
}

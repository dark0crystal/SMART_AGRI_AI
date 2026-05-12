import 'dart:io';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../services/auth_api.dart';
import '../services/diagnosis_api.dart';
import '../services/session_sync.dart';

class DiagnosisCameraScreen extends StatefulWidget {
  const DiagnosisCameraScreen({super.key});

  @override
  State<DiagnosisCameraScreen> createState() => _DiagnosisCameraScreenState();
}

class _DiagnosisCameraScreenState extends State<DiagnosisCameraScreen> {
  bool _busy = false;

  /// Vision model resizes to 224x224, so anything larger than ~1280px just
  /// inflates upload time and Storage egress. Quality 80 is visually
  /// indistinguishable for leaf photos but cuts JPEG size ~2x.
  static const int _maxImageEdge = 1280;
  static const int _imageQuality = 80;

  /// Hard ceiling after compression. Anything larger almost certainly means
  /// `image_picker` couldn't downscale the image (e.g. raw HEIC); we surface
  /// a clear error rather than silently uploading multi-megabyte payloads.
  static const int _maxUploadBytes = 4 * 1024 * 1024;

  Future<void> _pickAndUpload(ImageSource source) async {
    final picker = ImagePicker();
    final xfile = await picker.pickImage(
      source: source,
      maxWidth: _maxImageEdge.toDouble(),
      maxHeight: _maxImageEdge.toDouble(),
      imageQuality: _imageQuality,
    );
    if (xfile == null) return;

    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Not signed in.')),
        );
      }
      return;
    }

    setState(() => _busy = true);
    try {
      // No-op when the session was already synced after sign-in/registration;
      // covers the edge case where a persisted session opens straight into
      // this screen without the home screen running first.
      await SessionSync.ensure();
      final file = File(xfile.path);
      final fileSize = await file.length();
      if (fileSize > _maxUploadBytes) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                'Photo is too large to upload (${(fileSize / (1024 * 1024)).toStringAsFixed(1)} MB). '
                'Try a different photo.',
              ),
            ),
          );
        }
        return;
      }
      final name =
          '${DateTime.now().millisecondsSinceEpoch}_${xfile.name.replaceAll(RegExp(r'[^\w.-]'), '_')}';
      final ref = FirebaseStorage.instance
          .ref()
          .child('users/${user.uid}/diagnoses/$name');
      await ref.putFile(file);
      final url = await ref.getDownloadURL();

      final res = await DiagnosisApi.createDiagnosis(
        inputType: 'image',
        imageUrl: url,
      );
      if (!mounted) return;
      final raw = res['id'];
      final id = raw is int ? raw : (raw is num ? raw.toInt() : null);
      if (id != null) {
        context.pushReplacement('/diagnosis/detail/$id');
      }
    } on AuthApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.message)),
      );
    } on FirebaseException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.message ?? e.code)),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Photo of symptoms')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: _busy
            ? const Center(child: CircularProgressIndicator())
            : Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text(
                    'Take a new photo or pick one from the gallery. '
                    'The image is uploaded to Firebase Storage, then sent to the API.',
                  ),
                  const SizedBox(height: 24),
                  FilledButton.icon(
                    onPressed: () => _pickAndUpload(ImageSource.camera),
                    icon: const Icon(Icons.camera_alt),
                    label: const Text('Use camera'),
                  ),
                  const SizedBox(height: 12),
                  FilledButton.tonalIcon(
                    onPressed: () => _pickAndUpload(ImageSource.gallery),
                    icon: const Icon(Icons.photo_library_outlined),
                    label: const Text('Choose from gallery'),
                  ),
                ],
              ),
      ),
    );
  }
}

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../services/auth_api.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  Map<String, dynamic>? _profile;
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
      final me = await AuthApi.me();
      if (mounted) {
        setState(() {
          _profile = me;
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

  Future<void> _signOut() async {
    await FirebaseAuth.instance.signOut();
    if (mounted) context.go('/login');
  }

  @override
  Widget build(BuildContext context) {
    final user = FirebaseAuth.instance.currentUser;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Smart Agri AI'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: _signOut,
            tooltip: 'Sign out',
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            if (_loading)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(32),
                  child: CircularProgressIndicator(),
                ),
              )
            else if (_error != null)
              Card(
                color: Theme.of(context).colorScheme.errorContainer,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Text(_error!),
                ),
              )
            else if (_profile != null) ...[
              Text(
                'Synced profile',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              Text('ID: ${_profile!['id']}'),
              Text('Email: ${_profile!['email']}'),
              if (_profile!['username'] != null)
                Text('Username: ${_profile!['username']}'),
              Text('Role: ${_profile!['role']}'),
            ],
            const SizedBox(height: 24),
            Text(
              'Firebase',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text('UID: ${user?.uid ?? '—'}'),
            Text('Email: ${user?.email ?? '—'}'),
            const SizedBox(height: 32),
            FilledButton.icon(
              onPressed: () => context.push('/diagnosis'),
              icon: const Icon(Icons.biotech_outlined),
              label: const Text('Lemon disease diagnosis'),
            ),
          ],
        ),
      ),
    );
  }
}

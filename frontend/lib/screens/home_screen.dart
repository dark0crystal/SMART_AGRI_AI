import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../services/auth_api.dart';
import '../services/session_sync.dart';

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
      await SessionSync.ensure();
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
    SessionSync.reset();
    if (mounted) context.go('/login');
  }

  /// Friendly name: backend username → Firebase displayName → email local part.
  String _displayName(Map<String, dynamic>? profile, User? firebaseUser) {
    final u = profile?['username']?.toString().trim();
    if (u != null && u.isNotEmpty) return u;
    final dn = firebaseUser?.displayName?.trim();
    if (dn != null && dn.isNotEmpty) return dn;
    final email = profile?['email']?.toString() ??
        firebaseUser?.email ??
        '';
    final at = email.indexOf('@');
    final local = at > 0 ? email.substring(0, at) : email;
    return local.isNotEmpty ? local : 'User';
  }

  /// First letter for avatar (prefer a letter A–Z / a–z).
  String _avatarLetter(String name) {
    for (final rune in name.runes) {
      final c = String.fromCharCode(rune);
      if (RegExp(r'[A-Za-z]').hasMatch(c)) {
        return c.toUpperCase();
      }
    }
    if (name.isNotEmpty) return name[0].toUpperCase();
    return '?';
  }

  String _roleLabel(String? raw) {
    switch (raw?.toLowerCase()) {
      case 'admin':
        return 'Administrator';
      default:
        return 'User';
    }
  }

  IconData _roleIcon(String? raw) {
    switch (raw?.toLowerCase()) {
      case 'admin':
        return Icons.admin_panel_settings_outlined;
      default:
        return Icons.person_outline;
    }
  }

  bool _isAdmin(Map<String, dynamic> profile) =>
      profile['role']?.toString().toLowerCase() == 'admin';

  Widget _roleBadge(BuildContext context, String? roleRaw) {
    final cs = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final label = _roleLabel(roleRaw);
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Row(
        children: [
          Icon(
            _roleIcon(roleRaw),
            size: 18,
            color: cs.primary,
          ),
          const SizedBox(width: 6),
          Text(
            label,
            style: textTheme.labelLarge?.copyWith(
              color: cs.onSurfaceVariant,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.2,
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final firebaseUser = FirebaseAuth.instance.currentUser;
    final cs = Theme.of(context).colorScheme;

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
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
              sliver: SliverToBoxAdapter(
                child: _loading
                    ? const Padding(
                        padding: EdgeInsets.symmetric(vertical: 48),
                        child: Center(child: CircularProgressIndicator()),
                      )
                    : _error != null
                        ? Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              Card(
                                color: cs.errorContainer,
                                child: Padding(
                                  padding: const EdgeInsets.all(16),
                                  child: Text(_error!),
                                ),
                              ),
                              if (firebaseUser != null) ...[
                                const SizedBox(height: 24),
                                _profileFallbackCard(context, firebaseUser),
                                const SizedBox(height: 28),
                                _toolsSection(context),
                              ],
                            ],
                          )
                        : _profile == null
                            ? const SizedBox.shrink()
                            : _buildContent(
                                context,
                                profile: _profile!,
                                firebaseUser: firebaseUser,
                              ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContent(
    BuildContext context, {
    required Map<String, dynamic> profile,
    required User? firebaseUser,
  }) {
    final cs = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final name = _displayName(profile, firebaseUser);
    final letter = _avatarLetter(name);
    final email = profile['email']?.toString() ??
        firebaseUser?.email ??
        '';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Card(
          elevation: 0,
          color: cs.surfaceContainerHighest.withValues(alpha: 0.75),
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                CircleAvatar(
                  radius: 36,
                  backgroundColor: cs.primaryContainer,
                  foregroundColor: cs.onPrimaryContainer,
                  child: Text(
                    letter,
                    style: textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        name,
                        style: textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                      if (email.isNotEmpty) ...[
                        const SizedBox(height: 6),
                        Text(
                          email,
                          style: textTheme.bodyMedium?.copyWith(
                            color: cs.onSurfaceVariant,
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                      _roleBadge(context, profile['role']?.toString()),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 28),
        _toolsSection(context),
        if (_isAdmin(profile)) ...[
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: () => context.push('/admin'),
            icon: const Icon(Icons.dashboard_customize_outlined),
            label: const Text('Admin tools'),
            style: OutlinedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14),
              ),
            ),
          ),
        ],
      ],
    );
  }

  Widget _profileFallbackCard(BuildContext context, User firebaseUser) {
    final name = _displayName(null, firebaseUser);
    final letter = _avatarLetter(name);
    final email = firebaseUser.email ?? '';
    final cs = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;

    return Card(
      elevation: 0,
      color: cs.surfaceContainerHighest.withValues(alpha: 0.75),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            CircleAvatar(
              radius: 36,
              backgroundColor: cs.primaryContainer,
              foregroundColor: cs.onPrimaryContainer,
              child: Text(
                letter,
                style: textTheme.headlineMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    name,
                    style: textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  if (email.isNotEmpty) ...[
                    const SizedBox(height: 6),
                    Text(
                      email,
                      style: textTheme.bodyMedium?.copyWith(
                        color: cs.onSurfaceVariant,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _toolsSection(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final cs = Theme.of(context).colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'Tools',
          style: textTheme.titleSmall?.copyWith(
            color: cs.onSurfaceVariant,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: 12),
        FilledButton.icon(
          style: FilledButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 16),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14),
            ),
          ),
          onPressed: () => context.push('/diagnosis'),
          icon: const Icon(Icons.biotech_outlined),
          label: const Text('Lemon disease diagnosis'),
        ),
      ],
    );
  }
}

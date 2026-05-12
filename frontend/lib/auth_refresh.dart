import 'dart:async';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';

import 'services/session_sync.dart';

/// Notifies [GoRouter] when Firebase auth session changes.
///
/// Also clears the cached `users/sync/` state on sign-out so the next signed-in
/// user is re-synced exactly once via [SessionSync.ensure].
class AuthStateRefresh extends ChangeNotifier {
  AuthStateRefresh() {
    _sub = FirebaseAuth.instance.authStateChanges().listen((user) {
      if (user == null) {
        SessionSync.reset();
      }
      notifyListeners();
    });
  }

  StreamSubscription<User?>? _sub;

  @override
  void dispose() {
    _sub?.cancel();
    _sub = null;
    super.dispose();
  }
}

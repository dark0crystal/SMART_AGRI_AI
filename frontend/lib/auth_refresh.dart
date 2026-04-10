import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';

/// Notifies [GoRouter] when Firebase auth session changes.
class AuthStateRefresh extends ChangeNotifier {
  AuthStateRefresh() {
    FirebaseAuth.instance.authStateChanges().listen((_) => notifyListeners());
  }
}

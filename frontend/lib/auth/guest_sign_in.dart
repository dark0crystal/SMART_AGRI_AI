import 'package:firebase_auth/firebase_auth.dart';

import '../services/auth_api.dart';

/// Firebase anonymous auth + Django user sync. Requires Anonymous enabled in Firebase Console.
Future<void> signInAsGuestAndSync() async {
  await FirebaseAuth.instance.signInAnonymously();
  await AuthApi.syncUser();
}

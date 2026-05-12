import 'package:firebase_auth/firebase_auth.dart';

/// User-facing text for FirebaseAuth failures during email/password sign-in
/// and registration.
String firebaseAuthMessage(FirebaseAuthException e) {
  final code = e.code;
  final msg = e.message ?? '';

  switch (code) {
    case 'operation-not-allowed':
      return 'This sign-in method is disabled. In Firebase Console open '
          'Authentication → Sign-in method and enable Email/Password.';
    case 'admin-restricted-operation':
      return 'This sign-in method is disabled for this project.';
    case 'network-request-failed':
      return 'Network error. Check your connection and try again.';
    case 'invalid-credential':
    case 'wrong-password':
    case 'user-not-found':
      return 'Incorrect email or password.';
    case 'invalid-email':
      return 'That email address is not valid.';
    case 'email-already-in-use':
      return 'An account already exists with this email.';
    case 'weak-password':
      return 'Choose a stronger password (at least 6 characters).';
    case 'too-many-requests':
      return 'Too many attempts. Wait a moment and try again.';
    case 'user-disabled':
      return 'This account has been disabled.';
    default:
      break;
  }

  if (msg.contains('internal error') ||
      msg.contains('Print and inspect') ||
      msg.toLowerCase().contains('internal')) {
    return 'Firebase Auth failed ($code). '
        'Confirm GoogleService-Info.plist / google-services.json match this app, '
        'then run a full rebuild (not hot restart).'
        '${msg.isNotEmpty ? '\nDetails: $msg' : ''}';
  }

  return msg.isNotEmpty ? '$code: $msg' : 'Firebase error: $code';
}

import 'package:firebase_auth/firebase_auth.dart';

/// User-facing text for FirebaseAuth failures (guest + sign-in).
String firebaseAuthMessage(FirebaseAuthException e) {
  final code = e.code;
  final msg = e.message ?? '';

  switch (code) {
    case 'operation-not-allowed':
      return 'Guest sign-in is turned off. In Firebase Console open '
          'Authentication → Sign-in method → enable Anonymous.';
    case 'admin-restricted-operation':
      return 'This sign-in method is disabled for this project.';
    case 'network-request-failed':
      return 'Network error. Check your connection and try again.';
    default:
      break;
  }

  if (msg.contains('internal error') ||
      msg.contains('Print and inspect') ||
      msg.toLowerCase().contains('internal')) {
    return 'Firebase Auth failed ($code). '
        'Enable Anonymous under Authentication → Sign-in method, '
        'confirm GoogleService-Info.plist / google-services.json match this app, '
        'then run a full rebuild (not hot restart).'
        '${msg.isNotEmpty ? '\nDetails: $msg' : ''}';
  }

  return msg.isNotEmpty ? '$code: $msg' : 'Firebase error: $code';
}

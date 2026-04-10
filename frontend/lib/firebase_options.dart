// Generated-style options: replace with output of `flutterfire configure --project=<id>`
// or paste values from Firebase Console → Project settings → Your apps.

import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart'
    show defaultTargetPlatform, kIsWeb, TargetPlatform;

class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform {
    if (kIsWeb) {
      return web;
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return android;
      case TargetPlatform.iOS:
        return ios;
      default:
        throw UnsupportedError(
          'DefaultFirebaseOptions are not configured for this platform.',
        );
    }
  }

  static const FirebaseOptions web = FirebaseOptions(
    apiKey: 'REPLACE_WITH_WEB_API_KEY',
    appId: '1:000000000000:web:0000000000000000000000',
    messagingSenderId: '000000000000',
    projectId: 'configure-in-firebase-console',
    authDomain: 'configure-in-firebase-console.firebaseapp.com',
    storageBucket: 'configure-in-firebase-console.appspot.com',
  );

  static const FirebaseOptions android = FirebaseOptions(
    apiKey: 'AIzaSyDELYQKRZImJAJm2Mg_3kGhx-41JxOLhEo',
    appId: '1:651436429024:android:98ff6debc99477b38a0a85',
    messagingSenderId: '651436429024',
    projectId: 'smart-agri-28723',
    storageBucket: 'smart-agri-28723.firebasestorage.app',
  );

  static const FirebaseOptions ios = FirebaseOptions(
    apiKey: 'AIzaSyDQgYcWQrZ-No9a-Bu0LsoKQsV3ZJZ0efg',
    appId: '1:651436429024:ios:9f03d96e4a11190f8a0a85',
    messagingSenderId: '651436429024',
    projectId: 'smart-agri-28723',
    storageBucket: 'smart-agri-28723.firebasestorage.app',
    iosBundleId: 'com.example.smartAgriAi',
  );

}
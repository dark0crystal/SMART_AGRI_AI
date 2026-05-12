import 'package:firebase_auth/firebase_auth.dart';

import 'api_client.dart';
import 'auth_api.dart';

/// De-duplicates `POST /api/users/sync/` so each signed-in Firebase user only
/// triggers the backend upsert once per app session.
///
/// Previously every screen called `AuthApi.syncUser()` before its real fetch,
/// adding an extra round-trip on every navigation. Screens now call
/// [SessionSync.ensure] which:
///   * returns immediately if the backend has already been synced for the
///     currently signed-in uid in this process,
///   * shares a single in-flight Future when called concurrently,
///   * forwards [username] (e.g. on first registration) when [force] is true.
class SessionSync {
  SessionSync._();

  static String? _syncedUid;
  static Future<void>? _inflight;

  /// Forget any cached sync state. Call after sign-out so the next user is
  /// synced afresh, and so we don't carry the previous user's ID token over.
  static void reset() {
    _syncedUid = null;
    _inflight = null;
    ApiClient.invalidateToken();
  }

  /// Ensure the backend `users/<uid>` row exists for the current user.
  /// Returns a completed Future when no user is signed in.
  static Future<void> ensure({String? username, bool force = false}) {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      reset();
      return Future.value();
    }

    final uid = user.uid;
    if (!force) {
      if (_syncedUid == uid && _inflight == null) {
        return Future.value();
      }
      if (_inflight != null && _syncedUid == uid) {
        return _inflight!;
      }
    }

    final future = AuthApi.syncUser(username: username).then((_) {
      _syncedUid = uid;
      _inflight = null;
    }).catchError((Object error, StackTrace stack) {
      // Surface the failure to the caller AND clear cache so the next call
      // can retry. Keep the sentinel uid in-place is intentionally avoided
      // here so a transient backend error doesn't permanently mark synced.
      _syncedUid = null;
      _inflight = null;
      throw error;
    });
    _syncedUid = uid;
    _inflight = future;
    return future;
  }
}

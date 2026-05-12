import 'dart:async';
import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:http/http.dart' as http;

import '../config/api_config.dart';
import 'auth_api.dart';

/// Default timeouts; long-running endpoints (image diagnosis) override per call.
const Duration _kDefaultTimeout = Duration(seconds: 20);
const Duration _kDiagnosisTimeout = Duration(seconds: 60);

/// Process-wide HTTP client and shared error/auth wiring.
///
/// Owning a single [http.Client] lets dart:io reuse the underlying TCP/TLS
/// connection across requests instead of paying a fresh TLS handshake every
/// time. We also cache the Firebase ID token briefly so back-to-back requests
/// (e.g. diagnose → navigate to detail) don't each await `getIdToken()`.
class ApiClient {
  ApiClient._();

  static final http.Client _httpClient = http.Client();

  /// Firebase ID tokens are valid for 1 hour. Cache for a much shorter window
  /// to bound staleness; firebase_auth refreshes the token transparently when
  /// we ask after expiry.
  static const Duration _tokenCacheTtl = Duration(minutes: 5);
  static String? _cachedToken;
  static String? _cachedTokenUid;
  static DateTime _cachedTokenAt = DateTime.fromMillisecondsSinceEpoch(0);

  static Uri uri(String path, [Map<String, String>? query]) {
    final base = Uri.parse('$kApiBaseUrl$path');
    if (query == null || query.isEmpty) return base;
    return base.replace(queryParameters: query);
  }

  /// Returns a Firebase ID token, optionally forcing a refresh.
  static Future<String> token({bool forceRefresh = false}) async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      throw AuthApiException('Not signed in.');
    }
    final now = DateTime.now();
    final fresh = !forceRefresh &&
        _cachedToken != null &&
        _cachedTokenUid == user.uid &&
        now.difference(_cachedTokenAt) < _tokenCacheTtl;
    if (fresh) {
      return _cachedToken!;
    }
    final t = await user.getIdToken(forceRefresh);
    if (t == null || t.isEmpty) {
      throw AuthApiException('No ID token.');
    }
    _cachedToken = t;
    _cachedTokenUid = user.uid;
    _cachedTokenAt = now;
    return t;
  }

  /// Forget the cached token (e.g., after sign-out).
  static void invalidateToken() {
    _cachedToken = null;
    _cachedTokenUid = null;
    _cachedTokenAt = DateTime.fromMillisecondsSinceEpoch(0);
  }

  static Map<String, String> _headers(String token, {bool json = false}) {
    final h = <String, String>{'Authorization': 'Bearer $token'};
    if (json) h['Content-Type'] = 'application/json';
    return h;
  }

  static Future<http.Response> _send(
    Future<http.Response> Function() send,
    Duration timeout,
  ) async {
    try {
      return await send().timeout(timeout);
    } on TimeoutException {
      throw AuthApiException(
        'The server took too long to respond. Please try again.',
      );
    }
  }

  static Future<Map<String, dynamic>> get(
    String path, {
    Map<String, String>? query,
    Duration? timeout,
  }) async {
    final t = await token();
    final res = await _send(
      () => _httpClient.get(uri(path, query), headers: _headers(t)),
      timeout ?? _kDefaultTimeout,
    );
    return _decode(res);
  }

  static Future<Map<String, dynamic>> post(
    String path, {
    Map<String, dynamic>? body,
    Duration? timeout,
  }) async {
    final t = await token();
    final res = await _send(
      () => _httpClient.post(
        uri(path),
        headers: _headers(t, json: true),
        body: jsonEncode(body ?? <String, dynamic>{}),
      ),
      timeout ?? _kDefaultTimeout,
    );
    return _decode(res);
  }

  /// Same as [post], but with the longer diagnosis-friendly timeout.
  static Future<Map<String, dynamic>> postDiagnosis(
    String path, {
    Map<String, dynamic>? body,
  }) =>
      post(path, body: body, timeout: _kDiagnosisTimeout);

  static Future<Map<String, dynamic>> patch(
    String path, {
    Map<String, dynamic>? body,
    Duration? timeout,
  }) async {
    final t = await token();
    final res = await _send(
      () => _httpClient.patch(
        uri(path),
        headers: _headers(t, json: true),
        body: jsonEncode(body ?? <String, dynamic>{}),
      ),
      timeout ?? _kDefaultTimeout,
    );
    return _decode(res);
  }

  static Map<String, dynamic> _decode(http.Response res) {
    Map<String, dynamic>? body;
    try {
      if (res.body.isNotEmpty) {
        body = jsonDecode(res.body) as Map<String, dynamic>?;
      }
    } catch (_) {}
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return body ?? <String, dynamic>{};
    }
    final detail = body?['detail'];
    final message = detail is String
        ? detail
        : detail is List
            ? detail.map((e) => e.toString()).join(' ')
            : 'Request failed (${res.statusCode})';
    throw AuthApiException(message, statusCode: res.statusCode);
  }
}

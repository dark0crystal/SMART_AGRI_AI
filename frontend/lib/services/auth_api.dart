import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:http/http.dart' as http;

import '../config/api_config.dart';

class AuthApiException implements Exception {
  AuthApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

class AuthApi {
  static Uri _uri(String path) => Uri.parse('$kApiBaseUrl$path');

  static Future<Map<String, dynamic>> syncUser({String? username}) async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      throw AuthApiException('Not signed in.');
    }
    final token = await user.getIdToken();
    final payload = <String, dynamic>{};
    if (username != null && username.trim().isNotEmpty) {
      payload['username'] = username.trim();
    }
    final res = await http.post(
      _uri('/api/users/sync/'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode(payload),
    );
    return _decodeJsonMap(res);
  }

  static Future<Map<String, dynamic>> me() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      throw AuthApiException('Not signed in.');
    }
    final token = await user.getIdToken();
    final res = await http.get(
      _uri('/api/me/'),
      headers: {'Authorization': 'Bearer $token'},
    );
    return _decodeJsonMap(res);
  }

  static Map<String, dynamic> _decodeJsonMap(http.Response res) {
    Map<String, dynamic>? body;
    try {
      if (res.body.isNotEmpty) {
        body = jsonDecode(res.body) as Map<String, dynamic>?;
      }
    } catch (_) {
      // ignore
    }
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return body ?? {};
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

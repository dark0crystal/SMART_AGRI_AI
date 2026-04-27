import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:http/http.dart' as http;

import '../config/api_config.dart';
import 'auth_api.dart';

class AdminCatalogApi {
  static Uri _uri(String path) => Uri.parse('$kApiBaseUrl$path');

  static Future<String> _token() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) throw AuthApiException('Not signed in.');
    final t = await user.getIdToken();
    if (t == null || t.isEmpty) throw AuthApiException('No ID token.');
    return t;
  }

  static Map<String, dynamic> _decode(http.Response res) {
    Map<String, dynamic>? body;
    try {
      if (res.body.isNotEmpty) {
        body = jsonDecode(res.body) as Map<String, dynamic>?;
      }
    } catch (_) {}
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

  static Future<Map<String, dynamic>> listPlants() async {
    final token = await _token();
    final res = await http.get(
      _uri('/api/admin/catalog/plants/'),
      headers: {'Authorization': 'Bearer $token'},
    );
    return _decode(res);
  }

  static Future<Map<String, dynamic>> getPlant(int plantId) async {
    final token = await _token();
    final res = await http.get(
      _uri('/api/admin/catalog/plants/$plantId/'),
      headers: {'Authorization': 'Bearer $token'},
    );
    return _decode(res);
  }

  static Future<Map<String, dynamic>> listDiseasesForPlant(int plantId) async {
    final token = await _token();
    final res = await http.get(
      _uri('/api/admin/catalog/plants/$plantId/diseases/'),
      headers: {'Authorization': 'Bearer $token'},
    );
    return _decode(res);
  }

  static Future<Map<String, dynamic>> getDisease(int diseaseId) async {
    final token = await _token();
    final res = await http.get(
      _uri('/api/admin/catalog/diseases/$diseaseId/'),
      headers: {'Authorization': 'Bearer $token'},
    );
    return _decode(res);
  }

  static Future<Map<String, dynamic>> updateDisease(
    int diseaseId,
    Map<String, dynamic> body,
  ) async {
    final token = await _token();
    final res = await http.patch(
      _uri('/api/admin/catalog/diseases/$diseaseId/'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode(body),
    );
    return _decode(res);
  }
}

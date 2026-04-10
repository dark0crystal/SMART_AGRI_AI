import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:http/http.dart' as http;

import '../config/api_config.dart';
import 'auth_api.dart';

class DiagnosisApi {
  static Uri _uri(String path, [Map<String, String>? query]) {
    final base = Uri.parse('$kApiBaseUrl$path');
    if (query == null || query.isEmpty) return base;
    return base.replace(queryParameters: query);
  }

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

  /// Paginated list: keys `count`, `next`, `previous`, `results`.
  static Future<Map<String, dynamic>> listDiagnoses({int page = 1}) async {
    final token = await _token();
    final res = await http.get(
      _uri('/api/diagnoses/', {'page': '$page'}),
      headers: {'Authorization': 'Bearer $token'},
    );
    return _decode(res);
  }

  static Future<Map<String, dynamic>> getDiagnosis(int id) async {
    final token = await _token();
    final res = await http.get(
      _uri('/api/diagnoses/$id/'),
      headers: {'Authorization': 'Bearer $token'},
    );
    return _decode(res);
  }

  static Future<Map<String, dynamic>> createDiagnosis({
    required String inputType,
    String? textInput,
    String? imageUrl,
  }) async {
    final token = await _token();
    final payload = <String, dynamic>{
      'input_type': inputType,
    };
    if (textInput != null && textInput.isNotEmpty) {
      payload['text_input'] = textInput;
    }
    if (imageUrl != null && imageUrl.isNotEmpty) {
      payload['image_url'] = imageUrl;
    }
    final res = await http.post(
      _uri('/api/diagnoses/'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode(payload),
    );
    return _decode(res);
  }
}
